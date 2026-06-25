#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, bindparam, create_engine, func, inspect, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


STANDARD_CATEGORIES = [
    "Technology",
    "Healthcare",
    "Executive",
    "Finance",
    "Campus",
    "Legal",
    "General",
]

CATEGORY_TAG_PREFIX = "category:"


RULES: dict[str, list[tuple[re.Pattern[str], int]]] = {
    "Technology": [
        (re.compile(r"\bit\b"), 3),
        (re.compile(r"\btech(?:nical|nology)?\b"), 4),
        (re.compile(r"\bsoftware\b"), 4),
        (re.compile(r"\bdeveloper\b"), 4),
        (re.compile(r"\bengineer(?:ing)?\b"), 4),
        (re.compile(r"\bdevops\b"), 4),
        (re.compile(r"\bdata\b"), 3),
        (re.compile(r"\bcyber(?:security)?\b"), 4),
        (re.compile(r"\binfrastructure\b"), 3),
        (re.compile(r"\bcloud\b"), 3),
        (re.compile(r"\bfull[\s-]?stack\b"), 4),
        (re.compile(r"\bfrontend\b|\bfront[\s-]?end\b"), 3),
        (re.compile(r"\bbackend\b|\bback[\s-]?end\b"), 3),
        (re.compile(r"\bqa\b|\bquality assurance\b"), 2),
        (re.compile(r"\bsre\b"), 4),
        (re.compile(r"\bproduct\b"), 2),
        (re.compile(r"\bsourcer\b"), 1),
    ],
    "Healthcare": [
        (re.compile(r"\bhealth(?:care)?\b"), 4),
        (re.compile(r"\bclinical\b"), 4),
        (re.compile(r"\bmedical\b"), 4),
        (re.compile(r"\bnurs(?:e|ing)\b"), 4),
        (re.compile(r"\bphysician\b"), 4),
        (re.compile(r"\bdoctor\b"), 4),
        (re.compile(r"\bpharma\b|\bpharmaceutical\b"), 4),
        (re.compile(r"\bbiotech\b"), 4),
        (re.compile(r"\blife sciences?\b"), 4),
        (re.compile(r"\btherapy\b|\btherapist\b"), 3),
        (re.compile(r"\bdental\b"), 3),
        (re.compile(r"\bcaregiver\b"), 3),
    ],
    "Executive": [
        (re.compile(r"\bexecutive\b"), 4),
        (re.compile(r"\bexec search\b|\bexecutive search\b"), 5),
        (re.compile(r"\bc[-\s]?suite\b"), 5),
        (re.compile(r"\bceo\b|\bcfo\b|\bcoo\b|\bcio\b|\bcto\b"), 5),
        (re.compile(r"\bboard\b"), 3),
        (re.compile(r"\bleadership\b"), 4),
        (re.compile(r"\bvp\b|\bvice president\b"), 3),
        (re.compile(r"\bretained search\b"), 5),
    ],
    "Finance": [
        (re.compile(r"\bfinance\b|\bfinancial\b"), 4),
        (re.compile(r"\baccount(?:ing|ant)?\b"), 4),
        (re.compile(r"\bfp&a\b"), 4),
        (re.compile(r"\bpayroll\b"), 3),
        (re.compile(r"\btax\b"), 4),
        (re.compile(r"\bauditor?\b|\baudit\b"), 4),
        (re.compile(r"\btreasury\b"), 4),
        (re.compile(r"\bbank(?:ing)?\b"), 4),
        (re.compile(r"\binvestment\b"), 4),
        (re.compile(r"\bprivate equity\b"), 4),
        (re.compile(r"\bhedge fund\b"), 4),
        (re.compile(r"\bcredit\b"), 3),
        (re.compile(r"\bcontroller\b"), 3),
    ],
    "Campus": [
        (re.compile(r"\bcampus\b"), 5),
        (re.compile(r"\buniversity\b|\bcollege\b"), 4),
        (re.compile(r"\bgraduate\b"), 4),
        (re.compile(r"\bearly career\b"), 5),
        (re.compile(r"\bintern(?:ship)?s?\b"), 4),
        (re.compile(r"\bentry[\s-]?level\b"), 3),
        (re.compile(r"\bstudent\b"), 3),
        (re.compile(r"\bnew grad\b"), 5),
    ],
    "Legal": [
        (re.compile(r"\blegal\b"), 5),
        (re.compile(r"\battorney\b|\blawyer\b|\bcounsel\b"), 5),
        (re.compile(r"\bparalegal\b"), 5),
        (re.compile(r"\blitigation\b"), 4),
        (re.compile(r"\bcontract law\b|\bcorporate law\b"), 4),
        (re.compile(r"\bcompliance\b"), 3),
        (re.compile(r"\bjd\b|\bjuris doctor\b"), 4),
    ],
}


@dataclass
class WorkerStats:
    scanned: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: int = 0
    batches: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standalone taxonomy worker for normalizing recruiter titles into category tags."
    )
    parser.add_argument("--database-url", help="PostgreSQL connection string. Overrides environment variables.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Rows to process per batch.")
    parser.add_argument("--start-id", type=int, default=0, help="Resume processing from recruiter_id greater than this.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows to scan for testing.")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without committing them.")
    parser.add_argument(
        "--replace-existing-category",
        action="store_true",
        default=True,
        help="Replace existing category tags before appending the new one. Default: enabled.",
    )
    parser.add_argument("--no-replace-existing-category", dest="replace_existing_category", action="store_false")
    parser.add_argument("--progress-every", type=int, default=5000, help="Fallback progress print cadence without tqdm.")
    parser.add_argument("--echo-sql", action="store_true", help="Enable SQLAlchemy SQL logging.")
    return parser.parse_args()


def load_database_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url

    for key in ("DATABASE_URL", "TALENTOPS_DATABASE_URL"):
        value = os.getenv(key)
        if value:
            return value

    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in {"DATABASE_URL", "TALENTOPS_DATABASE_URL"} and value.strip():
                return value.strip().strip('"').strip("'")

    raise RuntimeError(
        "Database URL not found. Pass --database-url or set DATABASE_URL / TALENTOPS_DATABASE_URL."
    )


def build_engine(database_url: str, echo_sql: bool = False) -> Engine:
    connect_args: dict[str, Any] = {}
    if database_url.startswith("postgresql+psycopg://"):
        connect_args["prepare_threshold"] = None

    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        echo=echo_sql,
        connect_args=connect_args,
    )


def reflect_recruiters_table(engine: Engine) -> tuple[Table, str]:
    inspector = inspect(engine)
    if "recruiters" not in inspector.get_table_names():
        raise RuntimeError("Table 'recruiters' was not found in the connected database.")

    metadata = MetaData()
    recruiters = Table("recruiters", metadata, autoload_with=engine)

    if "recruiter_id" in recruiters.c:
        pk_name = "recruiter_id"
    else:
        pk_columns = [column.name for column in recruiters.primary_key.columns]
        if not pk_columns:
            raise RuntimeError("Could not determine a primary key for the recruiters table.")
        pk_name = pk_columns[0]

    required_columns = {"tags"}
    missing = [name for name in required_columns if name not in recruiters.c]
    if missing:
        raise RuntimeError(f"Missing required recruiter columns: {', '.join(missing)}")

    if "title" not in recruiters.c and "specialization" not in recruiters.c:
        raise RuntimeError("Expected at least one of the columns: title, specialization")

    return recruiters, pk_name


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def classify_category(title: Any, specialization: Any) -> str:
    source = " | ".join(part for part in [normalize_text(title), normalize_text(specialization)] if part)
    if not source:
        return "General"

    scores = {category: 0 for category in STANDARD_CATEGORIES}
    for category, patterns in RULES.items():
        for pattern, weight in patterns:
            if pattern.search(source):
                scores[category] += weight

    if re.search(r"\brecruit(?:er|ing|ment)?\b|\btalent acquisition\b|\bsourcing\b", source):
        if scores["Technology"] > 0:
            scores["Technology"] += 1
        if scores["Healthcare"] > 0:
            scores["Healthcare"] += 1
        if scores["Executive"] > 0:
            scores["Executive"] += 1
        if scores["Finance"] > 0:
            scores["Finance"] += 1
        if scores["Campus"] > 0:
            scores["Campus"] += 1
        if scores["Legal"] > 0:
            scores["Legal"] += 1

    best_category = "General"
    best_score = 0
    for category in STANDARD_CATEGORIES:
        score = scores.get(category, 0)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category if best_score > 0 else "General"


def category_tag(category: str) -> str:
    return f"{CATEGORY_TAG_PREFIX} {category}"


def remove_existing_category_tags(items: list[str]) -> list[str]:
    return [item for item in items if not normalize_text(item).startswith(CATEGORY_TAG_PREFIX)]


def normalize_string_tags(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def merge_into_existing_tags(
    raw_tags: Any,
    category: str,
    replace_existing_category: bool = True,
) -> tuple[Any, bool]:
    new_tag = category_tag(category)

    if raw_tags is None or raw_tags == "":
        return new_tag, True

    if isinstance(raw_tags, list):
        tags = [str(item).strip() for item in raw_tags if str(item).strip()]
        normalized = remove_existing_category_tags(tags) if replace_existing_category else tags[:]
        if new_tag not in normalized:
            normalized.append(new_tag)
        changed = normalized != tags
        return normalized, changed

    if isinstance(raw_tags, dict):
        payload = dict(raw_tags)
        current = payload.get("tags", [])
        if isinstance(current, str):
            current_tags = normalize_string_tags(current)
        elif isinstance(current, list):
            current_tags = [str(item).strip() for item in current if str(item).strip()]
        else:
            current_tags = []
        normalized = remove_existing_category_tags(current_tags) if replace_existing_category else current_tags[:]
        if new_tag not in normalized:
            normalized.append(new_tag)
        payload["tags"] = normalized
        changed = payload != raw_tags
        return payload, changed

    if isinstance(raw_tags, str):
        stripped = raw_tags.strip()
        if not stripped:
            return new_tag, True

        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                return merge_into_existing_tags(parsed, category, replace_existing_category)
            except json.JSONDecodeError:
                pass

        current_tags = normalize_string_tags(stripped)
        normalized = remove_existing_category_tags(current_tags) if replace_existing_category else current_tags[:]
        if new_tag not in normalized:
            normalized.append(new_tag)
        updated = ", ".join(normalized)
        changed = updated != stripped
        return updated, changed

    fallback = str(raw_tags).strip()
    current_tags = normalize_string_tags(fallback)
    normalized = remove_existing_category_tags(current_tags) if replace_existing_category else current_tags[:]
    if new_tag not in normalized:
        normalized.append(new_tag)
    updated = ", ".join(normalized)
    changed = updated != fallback
    return updated, changed


def progress_bar(total: int | None):
    if tqdm:
        return tqdm(total=total, unit="recruiter", dynamic_ncols=True)
    return None


def fetch_batch(
    connection,
    recruiters: Table,
    pk_name: str,
    last_seen_id: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    pk_column = recruiters.c[pk_name]
    columns = [pk_column, recruiters.c.tags]
    if "title" in recruiters.c:
        columns.append(recruiters.c.title)
    if "specialization" in recruiters.c:
        columns.append(recruiters.c.specialization)

    stmt = (
        select(*columns)
        .where(pk_column > last_seen_id)
        .order_by(pk_column.asc())
        .limit(batch_size)
    )
    return [dict(row) for row in connection.execute(stmt).mappings().all()]


def process_batch(
    connection,
    recruiters: Table,
    pk_name: str,
    rows: list[dict[str, Any]],
    dry_run: bool,
    replace_existing_category: bool,
) -> tuple[int, int]:
    updates: list[dict[str, Any]] = []
    unchanged = 0

    for row in rows:
        category = classify_category(row.get("title"), row.get("specialization"))
        merged_tags, changed = merge_into_existing_tags(
            row.get("tags"),
            category,
            replace_existing_category=replace_existing_category,
        )

        if not changed:
            unchanged += 1
            continue

        updates.append(
            {
                "pk_value": row[pk_name],
                "new_tags": merged_tags,
            }
        )

    if updates and not dry_run:
        stmt = (
            update(recruiters)
            .where(recruiters.c[pk_name] == bindparam("pk_value"))
            .values({"tags": bindparam("new_tags")})
        )
        connection.execute(stmt, updates)

    return len(updates), unchanged


def process_rows_with_fallback(
    engine: Engine,
    recruiters: Table,
    pk_name: str,
    rows: list[dict[str, Any]],
    dry_run: bool,
    replace_existing_category: bool,
) -> tuple[int, int, int]:
    try:
        with engine.begin() as connection:
            updated, unchanged = process_batch(
                connection=connection,
                recruiters=recruiters,
                pk_name=pk_name,
                rows=rows,
                dry_run=dry_run,
                replace_existing_category=replace_existing_category,
            )
        return updated, unchanged, 0
    except Exception as batch_exc:
        print(
            f"Batch failed near recruiter_id={rows[0].get(pk_name)}; "
            f"retrying row-by-row. Error: {batch_exc}",
            file=sys.stderr,
        )

    updated_total = 0
    unchanged_total = 0
    error_total = 0

    for row in rows:
        try:
            with engine.begin() as connection:
                updated, unchanged = process_batch(
                    connection=connection,
                    recruiters=recruiters,
                    pk_name=pk_name,
                    rows=[row],
                    dry_run=dry_run,
                    replace_existing_category=replace_existing_category,
                )
            updated_total += updated
            unchanged_total += unchanged
        except Exception as row_exc:
            error_total += 1
            print(
                f"Row failed for recruiter_id={row.get(pk_name)} | error={row_exc}",
                file=sys.stderr,
            )

    return updated_total, unchanged_total, error_total


def main() -> int:
    args = parse_args()
    started_at = time.time()

    try:
        database_url = load_database_url(args.database_url)
        engine = build_engine(database_url, echo_sql=args.echo_sql)
        recruiters, pk_name = reflect_recruiters_table(engine)

        with engine.connect() as connection:
            total_stmt = select(func.count()).select_from(recruiters)
            total_rows = int(connection.execute(total_stmt).scalar_one())

        target_total = min(total_rows, args.limit) if args.limit else total_rows
        print(
            f"Starting taxonomy worker | total_rows={total_rows} | target_rows={target_total} | "
            f"batch_size={args.batch_size} | dry_run={args.dry_run}"
        )

        stats = WorkerStats()
        processed_limit = 0
        last_seen_id = args.start_id
        bar = progress_bar(target_total)

        while True:
            if args.limit is not None and processed_limit >= args.limit:
                break

            batch_fetch_size = args.batch_size
            if args.limit is not None:
                remaining = args.limit - processed_limit
                if remaining <= 0:
                    break
                batch_fetch_size = min(batch_fetch_size, remaining)

            with engine.connect() as connection:
                rows = fetch_batch(connection, recruiters, pk_name, last_seen_id, batch_fetch_size)
            if not rows:
                break

            updated, unchanged, errors = process_rows_with_fallback(
                engine=engine,
                recruiters=recruiters,
                pk_name=pk_name,
                rows=rows,
                dry_run=args.dry_run,
                replace_existing_category=args.replace_existing_category,
            )

            stats.batches += 1
            stats.scanned += len(rows)
            stats.updated += updated
            stats.unchanged += unchanged
            stats.errors += errors
            processed_limit += len(rows)
            last_seen_id = int(rows[-1][pk_name])

            if bar:
                bar.update(len(rows))
                bar.set_postfix(updated=stats.updated, unchanged=stats.unchanged, errors=stats.errors)
            elif stats.scanned % args.progress_every < len(rows):
                print(
                    f"Progress | scanned={stats.scanned} updated={stats.updated} "
                    f"unchanged={stats.unchanged} last_{pk_name}={last_seen_id}"
                )

        if bar:
            bar.close()

        elapsed = time.time() - started_at
        print(
            "Finished taxonomy worker | "
            f"scanned={stats.scanned} updated={stats.updated} unchanged={stats.unchanged} "
            f"errors={stats.errors} batches={stats.batches} elapsed_seconds={elapsed:.2f}"
        )
        return 0

    except SQLAlchemyError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
