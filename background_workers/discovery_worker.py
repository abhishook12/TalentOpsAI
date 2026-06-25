#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import random
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests
from requests import Session
from ddgs import DDGS
from requests.exceptions import RequestException, Timeout
from sqlalchemy import MetaData, Table, and_, bindparam, create_engine, func, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text


DEFAULT_DATABASE_ENV_KEYS = ("DATABASE_URL", "TALENTOPS_DATABASE_URL")
DEFAULT_WEBHOOK_URL = "http://localhost:8000/recruiters/extension"
DEFAULT_SCAN_INTERVAL_HOURS = 0.0001
DEFAULT_COMPANY_DELAY_MIN = 0.0
DEFAULT_COMPANY_DELAY_MAX = 0.0
DEFAULT_POST_DELAY_MIN = 0.0
DEFAULT_POST_DELAY_MAX = 0.0
DEFAULT_REQUEST_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_SEARCH_RESULTS = 10

NAME_SPLIT_RE = re.compile(r"\s*[·•|,\-–—]+\s*")
LINKEDIN_PROFILE_RE = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[^/?#\"'>\s]+", re.I)
LIKELY_NAME_RE = re.compile(r"^[A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,3}$")


@dataclass
class Stats:
    loops: int = 0
    companies_scanned: int = 0
    names_found: int = 0
    existing_matches: int = 0
    posted_new: int = 0
    post_failures: int = 0
    search_failures: int = 0
    db_failures: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standalone live roster discovery worker for tracked companies."
    )
    parser.add_argument("--database-url", help="PostgreSQL connection string. Overrides environment variables.")
    parser.add_argument("--webhook-url", default=DEFAULT_WEBHOOK_URL, help="Local webhook URL for new recruiters.")
    parser.add_argument("--scan-interval-hours", type=float, default=DEFAULT_SCAN_INTERVAL_HOURS)
    parser.add_argument("--company-delay-min", type=float, default=DEFAULT_COMPANY_DELAY_MIN)
    parser.add_argument("--company-delay-max", type=float, default=DEFAULT_COMPANY_DELAY_MAX)
    parser.add_argument("--post-delay-min", type=float, default=DEFAULT_POST_DELAY_MIN)
    parser.add_argument("--post-delay-max", type=float, default=DEFAULT_POST_DELAY_MAX)
    parser.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    parser.add_argument("--connect-timeout", type=float, default=DEFAULT_CONNECT_TIMEOUT)
    parser.add_argument("--search-results", type=int, default=DEFAULT_SEARCH_RESULTS)
    parser.add_argument("--max-companies", type=int, default=None, help="Optional cap for one scan cycle.")
    parser.add_argument("--run-once", action="store_true", help="Run one scan cycle and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Discover and print candidates without posting.")
    parser.add_argument("--concurrency", type=int, default=8, help="Number of concurrent company processing threads.")
    return parser.parse_args()


_print_lock = threading.Lock()

def log(message: str, level: str = "INFO") -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{stamp}] [{level}] {message}"
    with _print_lock:
        try:
            print(msg, flush=True)
        except UnicodeEncodeError:
            enc = sys.stdout.encoding or 'utf-8'
            try:
                print(msg.encode(enc, errors='replace').decode(enc), flush=True)
            except Exception:
                # Last resort fallback if decoding also fails
                print(f"[{stamp}] [{level}] [Log Error] Message contains un-printable characters", flush=True)


def load_database_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url

    for key in DEFAULT_DATABASE_ENV_KEYS:
        value = os.getenv(key)
        if value:
            return value

    env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in DEFAULT_DATABASE_ENV_KEYS and value.strip():
                return value.strip().strip('"').strip("'")

    raise RuntimeError("Database URL not found. Pass --database-url or set DATABASE_URL / TALENTOPS_DATABASE_URL.")


def build_engine(database_url: str) -> Engine:
    connect_args: dict[str, Any] = {}
    if database_url.startswith("postgresql+psycopg://"):
        connect_args["prepare_threshold"] = None

    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def reflect_tables(engine: Engine) -> tuple[Table, Table]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    for required in ("companies", "recruiters"):
        if required not in table_names:
            raise RuntimeError(f"Required table '{required}' was not found.")

    metadata = MetaData()
    companies = Table("companies", metadata, autoload_with=engine)
    recruiters = Table("recruiters", metadata, autoload_with=engine)

    for column in ("company_name", "is_tracked", "is_active"):
        if column not in companies.c:
            raise RuntimeError(f"Missing companies.{column} column.")
    if "recruiter_name" not in recruiters.c:
        raise RuntimeError("Missing recruiters.recruiter_name column.")

    return companies, recruiters


def build_session() -> Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def timeout_tuple(args: argparse.Namespace) -> tuple[float, float]:
    return (args.connect_timeout, args.request_timeout)


def sleep_jitter(lower: float, upper: float) -> float:
    seconds = random.uniform(min(lower, upper), max(lower, upper))
    time.sleep(seconds)
    return seconds


def normalize_name(value: str) -> str:
    value = unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_company(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def extract_candidate_name(text: str, company_name: str) -> str | None:
    if not text:
        return None

    cleaned = unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    parts = NAME_SPLIT_RE.split(cleaned)
    blocked_fragments = {
        "linkedin",
        "profiles",
        "profile",
        "recruiter",
        "recruiting",
        "talent acquisition",
        "duckduckgo",
        "people",
        "search",
        "sr.",
        "senior",
        "vp",
        "vice president",
        "director",
        "head",
        "manager",
        "phd",
        "mba",
        "consultant",
        "lead",
        "sourcer",
        "human resources",
        "hr",
    }
    company_normalized = normalize_company(company_name)

    for part in parts:
        candidate = normalize_name(part)
        if not candidate or len(candidate) < 5 or len(candidate) > 60:
            continue
        lower = candidate.lower()
        if any(fragment in lower for fragment in blocked_fragments):
            continue
        if normalize_company(candidate) == company_normalized:
            continue
        words = candidate.split()
        if len(words) < 2 or len(words) > 4:
            continue
        if not LIKELY_NAME_RE.match(candidate):
            continue
        return candidate

    return None


def load_tavily_keys() -> list[str]:
    keys = os.getenv("TAVILY_API_KEYS", "")
    if not keys:
        env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("TAVILY_API_KEYS="):
                    keys = line.split("=", 1)[1]
                    break
    
    parsed_keys = [k.strip() for k in keys.split(",") if k.strip()]
    if not parsed_keys:
        parsed_keys = ["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"]
    return parsed_keys

_TAVILY_KEYS: list[str] = []
_CURRENT_TAVILY_INDEX = 0

_tavily_lock = threading.Lock()

def get_next_tavily_client() -> Any:
    global _TAVILY_KEYS, _CURRENT_TAVILY_INDEX
    from tavily import TavilyClient
    with _tavily_lock:
        if not _TAVILY_KEYS:
            _TAVILY_KEYS = load_tavily_keys()
        
        if _CURRENT_TAVILY_INDEX >= len(_TAVILY_KEYS):
            return None
        
        key = _TAVILY_KEYS[_CURRENT_TAVILY_INDEX]
        return TavilyClient(key)

def rotate_tavily_key():
    global _CURRENT_TAVILY_INDEX, _TAVILY_KEYS
    with _tavily_lock:
        _CURRENT_TAVILY_INDEX += 1
        if _CURRENT_TAVILY_INDEX < len(_TAVILY_KEYS):
            log(f"Rotated Tavily API key. Now using key index {_CURRENT_TAVILY_INDEX + 1}/{len(_TAVILY_KEYS)}", level="WARN")
        else:
            log("All Tavily API keys have been exhausted! Will need to wait until limits reset.", level="ERROR")

def discover_names_for_company(
    session: Session,
    company_name: str,
    linkedin_url: str | None,
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    names: list[dict[str, str]] = []
    seen: set[str] = set()
    
    queries = []
    if linkedin_url:
        clean_url = linkedin_url.replace('https://', '').replace('http://', '').replace('www.', '').rstrip('/')
        queries.append(f'site:{clean_url} recruiter')
        queries.append(f'site:linkedin.com/in "{company_name}" recruiter')
    else:
        queries = [
            f'site:linkedin.com/in "{company_name}" recruiter',
            f'site:linkedin.com/in "{company_name}" talent acquisition',
        ]

    for q in queries:
        while True:
            client = get_next_tavily_client()
            if not client:
                log("No active Tavily keys available. Skipping search.", level="ERROR")
                break
                
            try:
                response = client.search(query=q, search_depth="basic", max_results=10)
                results = response.get("results", [])
                
                for r in results:
                    title = r.get("title", "")
                    href = r.get("url", "")
                    content = r.get("content", "")
                    
                    if 'linkedin.com/in/' in href:
                        slug = href.rstrip("/").split("/")[-1]
                        slug = re.sub(r'-[a-f0-9]{6,}$', '', slug)
                        slug = re.sub(r"[-_]+", " ", slug)
                        slug = " ".join(word.capitalize() for word in slug.split() if word)
                        candidate = extract_candidate_name(slug, company_name)
                        if candidate and candidate.lower() not in seen:
                            seen.add(candidate.lower())
                            names.append({"name": candidate, "linkedin_url": href, "title": title, "location": content})
                            
                    parts = NAME_SPLIT_RE.split(re.sub(r'<[^>]+>', '', title))
                    for part in parts:
                        part = part.strip()
                        candidate = extract_candidate_name(part, company_name)
                        if candidate and candidate.lower() not in seen:
                            seen.add(candidate.lower())
                            names.append({"name": candidate, "linkedin_url": href if 'linkedin.com/in/' in href else None, "title": title, "location": content})
                            
                if len(names) >= args.search_results:
                    break
                break # Search succeeded, stop retry loop
                
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "unauthorized" in err_msg or "400" in err_msg:
                    log(f"Tavily quota exceeded/invalid key: {e}", level="WARN")
                    rotate_tavily_key()
                else:
                    log(f"Tavily scraper error for query '{q}': {e}", level="WARN")
                    break

    return names[: args.search_results]


def fetch_tracked_companies(
    engine: Engine,
    companies: Table,
    recruiters: Table,
    limit: int | None,
) -> list[dict[str, Any]]:
    stmt = (
        select(
            companies.c.company_id,
            companies.c.company_name,
            companies.c.linkedin_url,
            func.count(recruiters.c.recruiter_id).label("people_count")
        )
        .select_from(companies)
        .outerjoin(
            recruiters,
            and_(
                companies.c.company_id == recruiters.c.company_id,
                recruiters.c.is_active.is_(True)
            )
        )
        .where(
            companies.c.is_active.is_(True)
        )
        .where(
            companies.c.is_tracked.is_(True)
        )
        .group_by(
            companies.c.company_id,
            companies.c.company_name,
            companies.c.linkedin_url,
            companies.c.trust_score,
            companies.c.updated_at
        )
        .order_by(
            companies.c.updated_at.asc().nullsfirst(),
            companies.c.trust_score.desc().nullslast(),
            text("people_count DESC"),
            companies.c.company_name.asc()
        )
    )
    if limit:
        stmt = stmt.limit(limit)

    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(stmt).mappings().all()]


def recruiter_exists(engine: Engine, recruiters: Table, recruiter_name: str, company_name: str) -> bool:
    recruiter_expr = func.lower(func.trim(recruiters.c.recruiter_name)) == bindparam("recruiter_name")
    stmt = select(func.count()).select_from(recruiters).where(recruiter_expr)

    params: dict[str, Any] = {"recruiter_name": recruiter_name.strip().lower()}
    if "company_name" in recruiters.c:
        stmt = stmt.where(func.lower(func.trim(recruiters.c.company_name)) == bindparam("company_name"))
        params["company_name"] = company_name.strip().lower()

    with engine.connect() as connection:
        count = int(connection.execute(stmt, params).scalar_one())
    return count > 0


def post_new_recruiter(
    session: Session,
    webhook_url: str,
    recruiter_name: str,
    company_name: str,
    linkedin_url: str | None,
    args: argparse.Namespace,
    title: str | None = None,
    location: str | None = None,
) -> dict[str, Any] | str | None:
    payload = {
        "recruiter_name": recruiter_name,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "title": title,
        "location": location,
        "source": "discovery_worker",
        "tags": ["AI Discovered", "Fresh"],
    }
    response = session.post(webhook_url, json=payload, timeout=timeout_tuple(args))
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return response.text

_stats_lock = threading.Lock()

def process_single_company(
    engine: Engine,
    companies: Table,
    recruiters: Table,
    company: dict[str, Any],
    index: int,
    total_companies: int,
    args: argparse.Namespace,
    stats: Stats,
) -> None:
    company_name = str(company.get("company_name") or "").strip()
    if not company_name:
        return
        
    people_count = company.get("people_count", 0)
    company_id = company.get("company_id", "N/A")
    company_linkedin_url = company.get("linkedin_url")
    
    log(f"[Discovery] Company {index}/{total_companies}: {company_name}")
    log(f"[Discovery] Company ID: {company_id}")
    log(f"[Discovery] Existing people count: {people_count}")
    log(f"[Discovery] Priority rank: {index}")

    with _stats_lock:
        stats.companies_scanned += 1
    
    start_time = time.time()
    
    duplicates_skipped = 0
    success_count = 0
    post_fails = 0
    search_fails = 0
    db_fails = 0
    
    query_str = f"site:linkedin.com/in \"{company_name}\" recruiter"
    if company_linkedin_url:
        query_str = f"Targeted: {company_linkedin_url}"
        
    log(f"[Discovery] Search query: {query_str}")

    thread_session = build_session()
    try:
        try:
            names_data = discover_names_for_company(thread_session, company_name, company_linkedin_url, args)
        except Timeout as exc:
            search_fails += 1
            with _stats_lock:
                stats.search_failures += 1
            log(f"DuckDuckGo timeout for {company_name}: {exc}", level="WARN")
            if args.company_delay_min > 0 or args.company_delay_max > 0:
                sleep_jitter(args.company_delay_min, args.company_delay_max)
            names_data = []
        except RequestException as exc:
            search_fails += 1
            with _stats_lock:
                stats.search_failures += 1
            log(f"DuckDuckGo request failed for {company_name}: {exc}", level="WARN")
            if args.company_delay_min > 0 or args.company_delay_max > 0:
                sleep_jitter(args.company_delay_min, args.company_delay_max)
            names_data = []
        except Exception as exc:
            search_fails += 1
            with _stats_lock:
                stats.search_failures += 1
            log(f"Unexpected discovery error for {company_name}: {exc}", level="ERROR")
            if args.company_delay_min > 0 or args.company_delay_max > 0:
                sleep_jitter(args.company_delay_min, args.company_delay_max)
            names_data = []

        log(f"[Discovery] Number of search results received: {len(names_data) if names_data else 0}")
        
        if names_data:
            valid_extracted = 0
            for item in names_data:
                name = item["name"]
                recruiter_linkedin_url = item.get("linkedin_url")
                extracted_title = item.get("title")
                extracted_location = item.get("location")
                valid_extracted += 1
                with _stats_lock:
                    stats.names_found += 1
                try:
                    exists = recruiter_exists(engine, recruiters, name, company_name)
                except SQLAlchemyError as exc:
                    db_fails += 1
                    with _stats_lock:
                        stats.db_failures += 1
                    log(f"DB lookup failed for {name} / {company_name}: {exc}", level="ERROR")
                    continue

                if exists:
                    duplicates_skipped += 1
                    with _stats_lock:
                        stats.existing_matches += 1
                    continue

                if args.dry_run:
                    success_count += 1
                    with _stats_lock:
                        stats.posted_new += 1
                else:
                    try:
                        post_new_recruiter(thread_session, args.webhook_url, name, company_name, recruiter_linkedin_url, args, extracted_title, extracted_location)
                        success_count += 1
                        with _stats_lock:
                            stats.posted_new += 1
                    except Timeout as exc:
                        post_fails += 1
                        with _stats_lock:
                            stats.post_failures += 1
                    except RequestException as exc:
                        post_fails += 1
                        with _stats_lock:
                            stats.post_failures += 1
                    except Exception as exc:
                        post_fails += 1
                        with _stats_lock:
                            stats.post_failures += 1

                if args.post_delay_min > 0 or args.post_delay_max > 0:
                    sleep_jitter(args.post_delay_min, args.post_delay_max)

            log(f"[Discovery] Number of valid names extracted: {valid_extracted}")
        else:
            log(f"[Discovery] Number of valid names extracted: 0")
        
        duration = time.time() - start_time
        
        if not args.dry_run:
            try:
                with engine.begin() as conn:
                    stmt = companies.update().where(companies.c.company_id == company_id).values(updated_at=func.now())
                    conn.execute(stmt)
            except Exception as e:
                log(f"Failed to update updated_at for {company_name}: {e}", level="ERROR")
        
        log(f"[Discovery] Number of duplicates skipped: {duplicates_skipped}")
        log(f"[Discovery] Number of new people successfully saved: {success_count}")
        log(f"[Discovery] Number of failed webhook requests: {post_fails}")
        log(f"[Discovery] Processing duration per company: {duration:.2f}s")
        
        if args.company_delay_min > 0 or args.company_delay_max > 0:
            slept = sleep_jitter(args.company_delay_min, args.company_delay_max)
            log(f"Cooling down {slept:.2f}s before next company.", level="DEBUG")
    finally:
        thread_session.close()

def run_scan_cycle(
    engine: Engine,
    companies: Table,
    recruiters: Table,
    session: Session,
    args: argparse.Namespace,
    stats: Stats,
) -> None:
    tracked_companies = fetch_tracked_companies(engine, companies, recruiters, args.max_companies)
    if not tracked_companies:
        log("No tracked active companies found for discovery scan.", level="WARN")
        return

    total_companies = len(tracked_companies)
    log(f"Starting discovery cycle for {total_companies} tracked companies.")

    concurrency = getattr(args, "concurrency", 8)
    log(f"Running cycle with concurrency = {concurrency} threads.")

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                process_single_company,
                engine,
                companies,
                recruiters,
                company,
                index,
                total_companies,
                args,
                stats
            )
            for index, company in enumerate(tracked_companies, start=1)
        ]
        # Wait for all futures to complete
        for future in futures:
            try:
                future.result()
            except Exception as exc:
                log(f"Unhandled company processing error: {exc}", level="ERROR")


def main() -> int:
    args = parse_args()
    stats = Stats()

    try:
        database_url = load_database_url(args.database_url)
        engine = build_engine(database_url)
        companies, recruiters = reflect_tables(engine)
        session = build_session()
    except Exception as exc:
        print(f"Startup error: {exc}", file=sys.stderr)
        return 1

    log(
        f"Discovery worker started | webhook={args.webhook_url} | "
        f"scan_interval_hours={args.scan_interval_hours} | dry_run={args.dry_run}"
    )

    try:
        while True:
            stats.loops += 1
            log(f"Beginning scan loop #{stats.loops}")

            try:
                run_scan_cycle(engine, companies, recruiters, session, args, stats)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                log(f"Top-level scan cycle error: {exc}", level="ERROR")

            log(
                f"Cycle summary | loops={stats.loops} companies_scanned={stats.companies_scanned} "
                f"names_found={stats.names_found} existing_matches={stats.existing_matches} "
                f"posted_new={stats.posted_new} post_failures={stats.post_failures} "
                f"search_failures={stats.search_failures} db_failures={stats.db_failures}"
            )

            if args.run_once:
                break

            sleep_seconds = max(args.scan_interval_hours, 0.01) * 3600
            log(f"Sleeping for {sleep_seconds / 3600:.2f} hours before next scan cycle.")
            time.sleep(sleep_seconds)

        return 0

    except KeyboardInterrupt:
        log("Discovery worker interrupted by user.", level="WARN")
        return 130
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
