#!/usr/bin/env python
from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from requests import Response, Session
from requests.exceptions import RequestException, Timeout


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 45
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_SLEEP_MIN = 4.0
DEFAULT_SLEEP_MAX = 7.0
DEFAULT_EMPTY_WAIT = 15.0


@dataclass
class Stats:
    fetched: int = 0
    attempted: int = 0
    enhanced: int = 0
    failed: int = 0
    empty_batches: int = 0
    loop_count: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standalone background enhancer for recruiters missing phone numbers."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Local backend base URL.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Recruiters to fetch per GET batch.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Read timeout in seconds for API calls.")
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=DEFAULT_CONNECT_TIMEOUT,
        help="Connect timeout in seconds for API calls.",
    )
    parser.add_argument("--sleep-min", type=float, default=DEFAULT_SLEEP_MIN, help="Minimum sleep between POST requests.")
    parser.add_argument("--sleep-max", type=float, default=DEFAULT_SLEEP_MAX, help="Maximum sleep between POST requests.")
    parser.add_argument(
        "--empty-wait",
        type=float,
        default=DEFAULT_EMPTY_WAIT,
        help="Wait time before final shutdown when no recruiters are returned.",
    )
    parser.add_argument(
        "--max-recruiters",
        type=int,
        default=None,
        help="Optional cap for this run. Useful for safe testing.",
    )
    parser.add_argument(
        "--stop-time",
        type=str,
        default=None,
        help="Optional stop time (HH:MM) to safely exit.",
    )
    return parser.parse_args()


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str, level: str = "INFO") -> None:
    msg = f"[{now_stamp()}] [{level}] {message}"
    print(msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding), flush=True)


def build_session() -> Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "TalentOpsBulkEnhancer/1.0",
        }
    )
    adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5, max_retries=0)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def timeout_tuple(args: argparse.Namespace) -> tuple[float, float]:
    return (args.connect_timeout, args.timeout)


def safe_json(response: Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def extract_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return [item for item in results if isinstance(item, dict)]
        if isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def recruiter_name(recruiter: dict[str, Any]) -> str:
    return (
        str(
            recruiter.get("recruiter_name")
            or recruiter.get("name")
            or recruiter.get("full_name")
            or f"Recruiter {recruiter.get('recruiter_id', 'Unknown')}"
        ).strip()
        or "Unknown Recruiter"
    )


def phone_value(payload: Any, recruiter: dict[str, Any]) -> str:
    if isinstance(payload, dict):
        for key in ("phone", "phone1", "best_phone", "primary_phone"):
            value = payload.get(key)
            if value:
                return str(value).strip()

        nested = payload.get("recruiter")
        if isinstance(nested, dict):
            for key in ("phone", "phone1", "best_phone", "primary_phone"):
                value = nested.get(key)
                if value:
                    return str(value).strip()

    for key in ("phone", "phone1", "phone2", "phone3", "phone4"):
        value = recruiter.get(key)
        if value:
            return str(value).strip()

    return "Not found"


def email_value(payload: Any, recruiter: dict[str, Any]) -> str:
    if isinstance(payload, dict):
        for key in ("email", "best_email", "primary_email"):
            value = payload.get(key)
            if value:
                return str(value).strip()

        nested = payload.get("recruiter")
        if isinstance(nested, dict):
            for key in ("email", "best_email", "primary_email"):
                value = nested.get(key)
                if value:
                    return str(value).strip()

    for key in ("email", "email2", "email3", "email4"):
        value = recruiter.get(key)
        if value:
            return str(value).strip()

    return "Not found"


def fetch_missing_phone_batch(
    session: Session,
    args: argparse.Namespace,
    company_name: str | None = None,
) -> list[dict[str, Any]]:
    url = f"{args.base_url.rstrip('/')}/recruiters/"
    params = {
        "limit": args.batch_size,
        "has_phone": "false",
        "sort_by": "last_scan_at",
        "sort_desc": "false",
    }
    if company_name:
        params["company"] = company_name
    response = session.get(url, params=params, timeout=timeout_tuple(args))
    response.raise_for_status()
    return extract_results(safe_json(response))


def enhance_recruiter(
    session: Session,
    recruiter_id: Any,
    args: argparse.Namespace,
) -> Any:
    url = f"{args.base_url.rstrip('/')}/recruiters/{recruiter_id}/enhance"
    response = session.post(url, timeout=timeout_tuple(args))
    response.raise_for_status()
    return safe_json(response)


def sleep_with_jitter(args: argparse.Namespace) -> float:
    lower = min(args.sleep_min, args.sleep_max)
    upper = max(args.sleep_min, args.sleep_max)
    seconds = random.uniform(lower, upper)
    time.sleep(seconds)
    return seconds


def summarize_success(
    sequence_number: int,
    recruiter: dict[str, Any],
    payload: Any,
) -> str:
    name = recruiter_name(recruiter)
    phone = phone_value(payload, recruiter)
    email = email_value(payload, recruiter)
    recruiter_id = recruiter.get("recruiter_id", "Unknown")
    return f"[{sequence_number}] Enhanced {name} (ID {recruiter_id}) - Found Phone: {phone} - Found Email: {email}"


def summarize_failure(
    sequence_number: int,
    recruiter: dict[str, Any],
    error: Exception,
) -> str:
    name = recruiter_name(recruiter)
    recruiter_id = recruiter.get("recruiter_id", "Unknown")
    return f"[{sequence_number}] Failed {name} (ID {recruiter_id}) - {error}"


def main() -> int:
    import json
    import os
    args = parse_args()
    stats = Stats()
    session = build_session()

    log(
        f"Starting bulk enhancer | base_url={args.base_url} | batch_size={args.batch_size} "
        f"| sleep_range={min(args.sleep_min, args.sleep_max):.1f}-{max(args.sleep_min, args.sleep_max):.1f}s"
    )

    try:
        target_companies = []
        if os.path.exists("target_companies.json"):
            with open("target_companies.json", "r") as f:
                target_companies = json.load(f)
            log(f"Loaded {len(target_companies)} target companies from target_companies.json")
        else:
            log("No target_companies.json found. Running in normal mode.", level="WARN")
            target_companies = [None]
            
        stop_dt = None
        if args.stop_time:
            from datetime import timedelta
            now = datetime.now()
            stop_t = datetime.strptime(args.stop_time, "%H:%M").time()
            stop_dt = datetime.combine(now.date(), stop_t)
            if stop_dt <= now:
                stop_dt += timedelta(days=1)
            log(f"Will stop running at: {stop_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        for company_idx, company_name in enumerate(target_companies):
            if company_name:
                log(f"--- Processing company {company_idx+1}/{len(target_companies)}: {company_name} ---")
            
            while True:
                if stop_dt and datetime.now() >= stop_dt:
                    log(f"Reached stop time ({args.stop_time}). Exiting gracefully.")
                    break

                if args.max_recruiters is not None and stats.attempted >= args.max_recruiters:
                    log(f"Reached max recruiter cap for this run: {args.max_recruiters}")
                    break

                stats.loop_count += 1

                try:
                    batch = fetch_missing_phone_batch(session, args, company_name)
                except Timeout as exc:
                    log(f"GET batch timed out: {exc}", level="WARN")
                    time.sleep(args.empty_wait)
                    continue
                except RequestException as exc:
                    log(f"GET batch failed: {exc}", level="WARN")
                    time.sleep(args.empty_wait)
                    continue
                except Exception as exc:
                    log(f"Unexpected GET batch error: {exc}", level="ERROR")
                    time.sleep(args.empty_wait)
                    continue

                if not batch:
                    if company_name:
                        log(f"No more recruiters for {company_name}. Moving to next company.")
                    else:
                        log(f"GET returned 0 recruiters missing phone numbers. Sleeping for {args.empty_wait}s.")
                        time.sleep(args.empty_wait)
                    break # Break inner loop, go to next company

                stats.fetched += len(batch)
                log(
                    f"Fetched batch #{stats.loop_count} with {len(batch)} recruiters "
                    f"| total_fetched={stats.fetched}"
                )

                for recruiter in batch:
                    if args.max_recruiters is not None and stats.attempted >= args.max_recruiters:
                        break

                    recruiter_id = recruiter.get("recruiter_id")
                    if recruiter_id in (None, ""):
                        stats.failed += 1
                        continue

                    stats.attempted += 1

                    try:
                        payload = enhance_recruiter(session, recruiter_id, args)
                        stats.enhanced += 1
                        log(summarize_success(stats.attempted, recruiter, payload), level="SUCCESS")
                    except Exception as exc:
                        stats.failed += 1
                        log(summarize_failure(stats.attempted, recruiter, exc), level="WARN")

                    slept = sleep_with_jitter(args)

                if args.max_recruiters is not None and stats.attempted >= args.max_recruiters:
                    break
                    
            if stop_dt and datetime.now() >= stop_dt:
                break
            if args.max_recruiters is not None and stats.attempted >= args.max_recruiters:
                break

        log(
            f"Worker finished | fetched={stats.fetched} attempted={stats.attempted} "
            f"enhanced={stats.enhanced} failed={stats.failed}"
        )
        return 0

    except KeyboardInterrupt:
        log(
            f"Interrupted by user | fetched={stats.fetched} attempted={stats.attempted} "
            f"enhanced={stats.enhanced} failed={stats.failed}",
            level="WARN",
        )
        return 130
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
