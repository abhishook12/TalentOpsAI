from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter
from app.utils.phone_normalizer import format_us_phone, phone_compare_key


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
MATCHED_EXISTING_PATH = OUTPUT_DIR / "location_workbook_matched_existing.csv"
REVIEW_QUEUE_PATH = OUTPUT_DIR / "workbook_review_queue.csv"
REPORT_PATH = OUTPUT_DIR / "phone_repair_report.json"
CHANGES_PATH = OUTPUT_DIR / "phone_repair_changes.csv"


PHONE_HINT_KEYS = ("phone", "mobile", "cell", "tel", "telephone", "contact")
INVALID_REPEAT_PHONES = {
    "0000000000",
    "1111111111",
    "2222222222",
    "3333333333",
    "4444444444",
    "5555555555",
    "6666666666",
    "7777777777",
    "8888888888",
    "9999999999",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json_blob(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def normalize_candidate(value: Any) -> str | None:
    if not value:
        return None
    normalized = format_us_phone(value)
    if not normalized:
        return None
    text = str(normalized).strip()
    return text or None


def looks_plausible_us_phone(value: Any) -> bool:
    digits = re.sub(r"\D+", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return False
    if digits in INVALID_REPEAT_PHONES:
        return False
    if digits[0] in {"0", "1"}:
        return False
    if digits[3] in {"0", "1"}:
        return False
    return True


def slot_values(recruiter: Recruiter) -> list[tuple[str, str | None]]:
    return [
        ("phone", recruiter.phone),
        ("phone2", recruiter.phone2),
        ("phone3", recruiter.phone3),
        ("phone4", recruiter.phone4),
    ]


def iter_source_phone_values(recruiter: Recruiter, matched_row: dict[str, str] | None) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []

    if matched_row and matched_row.get("phone"):
        values.append(("workbook_matched_existing.phone", matched_row["phone"]))

    raw_data = load_json_blob(recruiter.raw_data)
    metadata = load_json_blob(recruiter.metadata_json)

    for source_name, blob in (("raw_data", raw_data), ("metadata_json", metadata)):
        for key, value in blob.items():
            key_lower = str(key).lower()
            if any(hint in key_lower for hint in PHONE_HINT_KEYS) or key_lower in {"workbook_phone", "alternate_phones", "all_phones", "extra_phones"}:
                if isinstance(value, (list, tuple, set)):
                    for item in value:
                        if item and isinstance(item, (str, int, float)):
                            values.append((f"{source_name}.{key}", str(item)))
                elif isinstance(value, (str, int, float)) and value:
                    values.append((f"{source_name}.{key}", str(value)))

    for field_name in ("phone", "phone2", "phone3", "phone4"):
        field_value = getattr(recruiter, field_name, None)
        if field_value:
            values.append((f"current.{field_name}", str(field_value)))

    alt_phones = metadata.get("all_phones") or []
    if isinstance(alt_phones, list):
        for idx, value in enumerate(alt_phones):
            if value:
                values.append((f"metadata_json.all_phones[{idx}]", str(value)))

    extra_phones = metadata.get("extra_phones") or []
    if isinstance(extra_phones, list):
        for idx, value in enumerate(extra_phones):
            if value:
                values.append((f"metadata_json.extra_phones[{idx}]", str(value)))

    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for source, value in values:
        key = (source, value.strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append((source, value.strip()))
    return deduped


def choose_best_candidate(values: list[tuple[str, str]]) -> tuple[str | None, dict[str, Any]]:
    best_value: str | None = None
    best_meta: dict[str, Any] = {}
    best_score: tuple[int, int, int] = (-1, -1, -1)

    for source, raw_value in values:
        normalized = normalize_candidate(raw_value)
        if not normalized:
            continue
        compare_key = phone_compare_key(normalized)
        if not compare_key:
            continue

        digits = re.sub(r"\D+", "", str(normalized))
        if len(digits) < 10 or len(digits) > 15:
            continue
        if len(digits) == 10 and not looks_plausible_us_phone(digits):
            continue
        is_us = len(digits) == 10
        source_priority = 4 if source.startswith("workbook_matched_existing") else 3 if source.startswith("raw_data") else 2 if source.startswith("metadata_json") else 1
        completeness = 3 if is_us else 2 if len(digits) > 10 else 1
        stability = 2 if source.startswith("workbook_matched_existing") else 1
        score = (source_priority, completeness, stability)

        if score > best_score:
            best_score = score
            best_value = normalized
            best_meta = {
                "source": source,
                "raw_value": raw_value,
                "normalized": normalized,
                "compare_key": compare_key,
            }

    return best_value, best_meta


def normalize_current_slots(recruiter: Recruiter) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    # ONLY normalize phone3 and phone4 per user request
    for field_name, current_value in [("phone3", recruiter.phone3), ("phone4", recruiter.phone4)]:
        if not current_value:
            continue
        normalized = normalize_candidate(current_value)
        if normalized and normalized != current_value.strip():
            changes.append({
                "field": field_name,
                "before": current_value,
                "after": normalized,
            })
    return changes


def repair_recruiter(recruiter: Recruiter, matched_row: dict[str, str] | None, apply: bool) -> dict[str, Any]:
    before_slots = {field: getattr(recruiter, field, None) for field, _ in slot_values(recruiter)}
    current_primary = recruiter.phone or ""
    current_primary_key = phone_compare_key(current_primary)

    candidates = iter_source_phone_values(recruiter, matched_row)
    workbook_candidates = [
        item for item in candidates
        if item[0].startswith("workbook_matched_existing") or item[0].endswith("workbook_phone")
    ]
    fallback_candidates = [
        item for item in candidates
        if item[0].startswith("raw_data.phone")
        or item[0].startswith("metadata_json.all_phones")
        or item[0].startswith("metadata_json.extra_phones")
    ]
    best_phone, best_meta = choose_best_candidate(workbook_candidates)
    fallback_phone, fallback_meta = choose_best_candidate(fallback_candidates)
    slot_norm_changes = normalize_current_slots(recruiter)

    applied = False
    primary_changed = False
    evidence: dict[str, Any] = {
        "current_primary": current_primary,
        "current_primary_key": current_primary_key,
        "candidate_sources": candidates[:20],
        "slot_normalizations": slot_norm_changes,
    }

    if best_phone:
        best_key = phone_compare_key(best_phone)
        if best_key and best_key != current_primary_key:
            old_primary = recruiter.phone
            old_slots = [getattr(recruiter, field) for field, _ in slot_values(recruiter)]
            existing_keys = [phone_compare_key(value) for value in old_slots if value]
            if best_key not in existing_keys:
                if apply:
                    for field in ("phone3", "phone4"):
                        if not getattr(recruiter, field):
                            setattr(recruiter, field, best_phone)
                            break
                applied = True
                primary_changed = True
                evidence["previous_primary"] = old_primary
                evidence["applied_primary"] = best_phone
                evidence["source"] = best_meta.get("source")
                evidence["source_value"] = best_meta.get("raw_value")
            elif best_key == current_primary_key and best_phone != current_primary:
                pass # do not touch primary phone as per user instruction
                applied = True
                primary_changed = True
                evidence["previous_primary"] = current_primary
                evidence["applied_primary"] = best_phone
                evidence["source"] = best_meta.get("source")
                evidence["source_value"] = best_meta.get("raw_value")
    elif not current_primary and fallback_phone:
        fallback_key = phone_compare_key(fallback_phone)
        if fallback_key:
            if apply:
                for field in ("phone3", "phone4"):
                    if not getattr(recruiter, field):
                        setattr(recruiter, field, fallback_phone)
                        break
            applied = True
            primary_changed = True
            evidence["previous_primary"] = current_primary
            evidence["applied_primary"] = fallback_phone
            evidence["source"] = fallback_meta.get("source")
            evidence["source_value"] = fallback_meta.get("raw_value")

    if apply and slot_norm_changes:
        for change in slot_norm_changes:
            setattr(recruiter, change["field"], change["after"])

    if apply and (primary_changed or slot_norm_changes):
        metadata = load_json_blob(recruiter.metadata_json)
        history = metadata.setdefault("phone_repair_history", [])
        history.append({
            "repaired_at": datetime.now(timezone.utc).isoformat(),
            "source": best_meta.get("source") or "normalization_only",
            "applied_primary": recruiter.phone,
            "evidence": evidence,
        })
        metadata["phone_repair_evidence"] = evidence
        recruiter.metadata_json = json.dumps(metadata, default=str)

    return {
        "recruiter_id": recruiter.recruiter_id,
        "recruiter_name": recruiter.recruiter_name,
        "email": recruiter.email,
        "changed": bool(primary_changed or slot_norm_changes),
        "primary_changed": primary_changed,
        "slot_normalizations": slot_norm_changes,
        "before_phone": before_slots["phone"],
        "after_phone": recruiter.phone if apply else (best_phone or recruiter.phone),
        "source": best_meta.get("source"),
        "source_value": best_meta.get("raw_value"),
    }


def write_changes(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "recruiter_id",
                "recruiter_name",
                "email",
                "changed",
                "primary_changed",
                "before_phone",
                "after_phone",
                "source",
                "source_value",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair recruiter phone numbers using workbook-backed evidence.")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of recruiters processed.")
    args = parser.parse_args()

    matched_rows = load_csv(MATCHED_EXISTING_PATH)
    matched_by_id = {
        int(row["matched_recruiter_id"]): row
        for row in matched_rows
        if row.get("matched_recruiter_id") and row["phone"]
    }

    db = SessionLocal()
    try:
        recruiters = db.query(Recruiter).order_by(Recruiter.recruiter_id.asc()).all()
        if args.limit:
            recruiters = recruiters[: args.limit]

        summary = Counter()
        samples: list[dict[str, Any]] = []
        changed_rows: list[dict[str, Any]] = []

        for recruiter in recruiters:
            matched_row = matched_by_id.get(recruiter.recruiter_id)
            result = repair_recruiter(recruiter, matched_row, apply=args.apply)
            summary["scanned"] += 1
            if result["changed"]:
                summary["changed"] += 1
                if result["primary_changed"]:
                    summary["primary_changed"] += 1
                if result["slot_normalizations"]:
                    summary["slot_normalizations"] += len(result["slot_normalizations"])
                if result["source"]:
                    summary[f"source::{result['source']}"] += 1
                changed_rows.append(result)
                if len(samples) < 25:
                    samples.append(result)

        if args.apply:
            db.commit()
        else:
            db.rollback()

        write_changes(CHANGES_PATH, changed_rows)
        report = {
            "mode": "apply" if args.apply else "dry_run",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scanned": summary["scanned"],
            "changed": summary["changed"],
            "primary_changed": summary["primary_changed"],
            "slot_normalizations": summary["slot_normalizations"],
            "source_counts": {k.split("::", 1)[1]: v for k, v in summary.items() if k.startswith("source::")},
            "samples": samples[:20],
            "report_path": str(REPORT_PATH),
            "changes_path": str(CHANGES_PATH),
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
