from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter
from app.utils.phone_normalizer import format_us_phone, phone_compare_key


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
REPORT_PATH = OUTPUT_DIR / "phone_salvage_report.json"
CHANGES_PATH = OUTPUT_DIR / "phone_salvage_changes.csv"

INVALID_REPEAT_PHONES = {f"{d}" * 10 for d in range(10)}


def digits(value: Any) -> str:
    if not value:
        return ""
    result = re.sub(r"\D+", "", str(value))
    if len(result) == 11 and result.startswith("1"):
        result = result[1:]
    return result


def is_plausible_us(value: Any) -> bool:
    d = digits(value)
    if len(d) != 10:
        return False
    if d in INVALID_REPEAT_PHONES:
        return False
    if d[0] in {"0", "1"}:
        return False
    if d[3] in {"0", "1"}:
        return False
    return True


def normalize_slot(value: Any) -> str | None:
    if not value:
        return None
    normalized = format_us_phone(value)
    return normalized


def slot_names():
    return ("phone", "phone2", "phone3", "phone4")


def load_metadata(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {}
    return {}


def save_metadata(value: Any, metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, default=str)


def find_best_plausible_slot(recruiter: Recruiter) -> tuple[str | None, str | None]:
    chosen_field = None
    chosen_value = None
    for field in slot_names():
        value = getattr(recruiter, field, None)
        if not value:
            continue
        if is_plausible_us(value):
            normalized = normalize_slot(value)
            if normalized:
                chosen_field = field
                chosen_value = normalized
                if field == "phone":
                    return chosen_field, chosen_value
    return chosen_field, chosen_value


def slot_quality(value: Any) -> str:
    if not value:
        return "empty"
    d = digits(value)
    if len(d) == 10 and is_plausible_us(d):
        return "plausible_us"
    if len(d) == 10:
        return "implausible_us"
    if len(d) == 11:
        return "11_digits"
    if len(d) > 11:
        return "intl_or_long"
    return "short"


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely salvage recruiter phone numbers by moving plausible alternates into primary.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        recruiters = db.query(Recruiter).all()
        if args.limit:
            recruiters = recruiters[: args.limit]

        summary = Counter()
        changed_rows = []
        examples = []
        flagged_rows = []

        for recruiter in recruiters:
            slots = {field: getattr(recruiter, field, None) for field in slot_names()}
            qualities = {field: slot_quality(value) for field, value in slots.items() if value}
            if not qualities:
                continue

            summary["records_with_phone"] += 1
            summary[f"primary::{qualities.get('phone', 'empty')}"] += 1

            good_field, good_value = find_best_plausible_slot(recruiter)
            bad_primary = recruiter.phone and not is_plausible_us(recruiter.phone)
            safe_swap = bool(bad_primary and good_field and good_field != "phone")

            if safe_swap:
                summary["safe_primary_swaps"] += 1
                if args.apply:
                    old_primary = recruiter.phone
                    setattr(recruiter, good_field, normalize_slot(recruiter.phone))
                    recruiter.phone = good_value
                    metadata = load_metadata(recruiter.metadata_json)
                    salvage = metadata.setdefault("phone_salvage", [])
                    salvage.append({
                        "at": datetime.now(timezone.utc).isoformat(),
                        "action": "primary_swapped_from_alternate",
                        "previous_primary": old_primary,
                        "new_primary": good_value,
                        "from_field": good_field,
                    })
                    recruiter.metadata_json = save_metadata(recruiter.metadata_json, metadata)
                    recruiter.needs_review = True if recruiter.needs_review else recruiter.needs_review
                    recruiter.review_reason = recruiter.review_reason or "Phone salvage from alternate slot"
                    changed_rows.append({
                        "recruiter_id": recruiter.recruiter_id,
                        "recruiter_name": recruiter.recruiter_name,
                        "email": recruiter.email,
                        "before_phone": old_primary,
                        "after_phone": good_value,
                        "from_field": good_field,
                        "quality_before": qualities.get("phone"),
                        "quality_after": "plausible_us",
                    })
                    if len(examples) < 25:
                        examples.append({
                            "recruiter_id": recruiter.recruiter_id,
                            "recruiter_name": recruiter.recruiter_name,
                            "email": recruiter.email,
                            "before_phone": old_primary,
                            "after_phone": good_value,
                            "from_field": good_field,
                            "all_slots": slots,
                        })
                else:
                    changed_rows.append({
                        "recruiter_id": recruiter.recruiter_id,
                        "recruiter_name": recruiter.recruiter_name,
                        "email": recruiter.email,
                        "before_phone": recruiter.phone,
                        "after_phone": good_value,
                        "from_field": good_field,
                        "quality_before": qualities.get("phone"),
                        "quality_after": "plausible_us",
                    })
                    if len(examples) < 25:
                        examples.append({
                            "recruiter_id": recruiter.recruiter_id,
                            "recruiter_name": recruiter.recruiter_name,
                            "email": recruiter.email,
                            "before_phone": recruiter.phone,
                            "after_phone": good_value,
                            "from_field": good_field,
                            "all_slots": slots,
                        })
                continue

            if all(slot_quality(value) != "plausible_us" for value in slots.values() if value):
                summary["all_slots_suspicious"] += 1
            else:
                summary["already_has_plausible"] += 1

            if recruiter.phone and not is_plausible_us(recruiter.phone):
                summary["primary_flagged"] += 1
                if args.apply:
                    metadata = load_metadata(recruiter.metadata_json)
                    audit = metadata.setdefault("phone_audit", [])
                    audit.append({
                        "at": datetime.now(timezone.utc).isoformat(),
                        "issue": "implausible_primary_phone",
                        "primary_phone": recruiter.phone,
                    })
                    recruiter.metadata_json = save_metadata(recruiter.metadata_json, metadata)
                    recruiter.needs_review = True
                    reviewer_note = "phone_quality_implausible_primary"
                    if recruiter.review_reason:
                        if reviewer_note not in recruiter.review_reason:
                            recruiter.review_reason = f"{recruiter.review_reason}; {reviewer_note}"
                    else:
                        recruiter.review_reason = reviewer_note
                    flagged_rows.append({
                        "recruiter_id": recruiter.recruiter_id,
                        "recruiter_name": recruiter.recruiter_name,
                        "email": recruiter.email,
                        "primary_phone": recruiter.phone,
                        "issue": "implausible_primary_phone",
                    })

        if args.apply:
            db.commit()
        else:
            db.rollback()

        with CHANGES_PATH.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["recruiter_id", "recruiter_name", "email", "before_phone", "after_phone", "from_field", "quality_before", "quality_after"])
            writer.writeheader()
            for row in changed_rows:
                writer.writerow(row)

        flagged_path = OUTPUT_DIR / "phone_salvage_flags.csv"
        with flagged_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["recruiter_id", "recruiter_name", "email", "primary_phone", "issue"])
            writer.writeheader()
            for row in flagged_rows:
                writer.writerow(row)

        report = {
            "mode": "apply" if args.apply else "dry_run",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "records_with_phone": summary["records_with_phone"],
            "safe_primary_swaps": summary["safe_primary_swaps"],
            "all_slots_suspicious": summary["all_slots_suspicious"],
            "already_has_plausible": summary["already_has_plausible"],
            "primary_flagged": summary["primary_flagged"],
            "examples": examples,
            "report_path": str(REPORT_PATH),
            "changes_path": str(CHANGES_PATH),
            "flags_path": str(flagged_path),
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
