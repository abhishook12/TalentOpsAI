from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter
from app.scripts.verify_cross_contacts import build_cluster_data, build_records


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def normalize_text(value: Any) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def normalize_email(value: Any) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


def normalize_phone(value: Any) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", str(value))


def merge_review_reason(existing: str | None, suffix: str) -> str | None:
    text = (existing or "").strip()
    suffix = (suffix or "").strip()
    if not text:
        return None
    cleaned = re.sub(r"(?:\s+)?Cross-contact verifier found duplicate cluster #[^.]*\.\s*", " ", text, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned:
        return cleaned
    return None


def score_record(record: dict[str, Any]) -> tuple:
    instance: Recruiter = record["instance"]
    metadata = {}
    if instance.metadata_json:
        try:
            metadata = json.loads(instance.metadata_json) if isinstance(instance.metadata_json, str) else dict(instance.metadata_json)
        except Exception:
            metadata = {}
    email_count = sum(1 for key in ("email", "email2", "email3", "email4") if getattr(instance, key, None))
    phone_count = sum(1 for key in ("phone", "phone2", "phone3", "phone4") if getattr(instance, key, None))
    metadata_count = len(metadata or {})
    return (
        int(instance.completeness_score or 0),
        int(instance.trust_score or 0),
        email_count,
        phone_count,
        1 if instance.state else 0,
        1 if instance.location else 0,
        1 if instance.linkedin else 0,
        metadata_count,
        1 if instance.is_active else 0,
        -(instance.recruiter_id or 0),
    )


def compact_metadata(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except Exception:
            return {"raw_metadata": value}
    return {"value": value}


def merge_canonical(canonical: Recruiter, donors: list[Recruiter]) -> None:
    existing_emails = {
        normalize_email(getattr(canonical, field, None))
        for field in ("email", "email2", "email3", "email4")
        if getattr(canonical, field, None)
    }
    existing_phones = {
        normalize_phone(getattr(canonical, field, None))
        for field in ("phone", "phone2", "phone3", "phone4")
        if getattr(canonical, field, None)
    }

    for donor in donors:
        for field in ("recruiter_name", "linkedin", "specialization", "title", "notes", "location", "state", "normalized_city", "review_reason", "state_source", "state_confidence", "state_reason"):
            if not getattr(canonical, field, None) and getattr(donor, field, None):
                setattr(canonical, field, getattr(donor, field))

        donor_emails = [getattr(donor, field, None) for field in ("email", "email2", "email3", "email4") if getattr(donor, field, None)]
        donor_phones = [getattr(donor, field, None) for field in ("phone", "phone2", "phone3", "phone4") if getattr(donor, field, None)]

        for email in donor_emails:
            norm = normalize_email(email)
            if not norm or norm in existing_emails:
                continue
            for field in ("email", "email2", "email3", "email4"):
                if not getattr(canonical, field, None):
                    setattr(canonical, field, email)
                    existing_emails.add(norm)
                    break

        for phone in donor_phones:
            norm = normalize_phone(phone)
            if not norm or norm in existing_phones:
                continue
            for field in ("phone", "phone2", "phone3", "phone4"):
                if not getattr(canonical, field, None):
                    setattr(canonical, field, phone)
                    existing_phones.add(norm)
                    break

        canonical_meta = compact_metadata(canonical.metadata_json)
        donor_meta = compact_metadata(donor.metadata_json)
        merge_bucket = canonical_meta.setdefault("duplicate_merge_sources", [])
        merge_bucket.append({
            "recruiter_id": donor.recruiter_id,
            "recruiter_name": donor.recruiter_name,
            "email": donor.email,
            "phone": donor.phone,
            "company_id": donor.company_id,
            "state": donor.state,
        })
        if donor_meta:
            alt = canonical_meta.setdefault("alternate_entries", [])
            alt.append(donor_meta)
        canonical.metadata_json = json.dumps(canonical_meta, default=str)

    canonical.review_reason = merge_review_reason(canonical.review_reason, "duplicate cleanup")
    if canonical.review_reason is None and not canonical.needs_review:
        canonical.needs_review = False


def build_delete_plan(clusters):
    high_clusters = [cluster for cluster in clusters if cluster.get("confidence") == "high" and int(cluster.get("size") or 0) > 1]
    plan = []
    for cluster in high_clusters:
        members = cluster.get("members", [])
        if len(members) < 2:
            continue
        plan.append({
            "cluster_id": cluster.get("cluster_id"),
            "size": int(cluster.get("size") or 0),
            "canonical_recruiter_id": cluster.get("canonical_recruiter_id"),
            "confidence": cluster.get("confidence"),
            "members": members,
        })
    return plan


def execute_delete_plan(db, records_by_id, plan, dry_run: bool):
    deleted_ids: list[int] = []
    kept_ids: list[int] = []
    cluster_summaries: list[dict[str, Any]] = []

    for cluster in plan:
        member_ids = [member["recruiter_id"] for member in cluster["members"]]
        member_records = [records_by_id[recruiter_id] for recruiter_id in member_ids if recruiter_id in records_by_id]
        if len(member_records) < 2:
            continue

        canonical_record = max(member_records, key=score_record)
        canonical_id = canonical_record["recruiter_id"]
        canonical_instance: Recruiter = canonical_record["instance"]
        donors = [record["instance"] for record in member_records if record["recruiter_id"] != canonical_id]

        cluster_summaries.append({
            "cluster_id": cluster["cluster_id"],
            "size": cluster["size"],
            "canonical_recruiter_id": canonical_id,
            "canonical_name": canonical_instance.recruiter_name,
            "canonical_email": canonical_instance.email,
            "canonical_phone": canonical_instance.phone,
            "deleted_count": len(donors),
            "member_ids": member_ids[:20],
        })

        kept_ids.append(canonical_id)
        deleted_ids.extend(donor.recruiter_id for donor in donors)

        if not dry_run:
            merge_canonical(canonical_instance, donors)

    if not dry_run and deleted_ids:
        for start in range(0, len(deleted_ids), 500):
            chunk = deleted_ids[start:start + 500]
            db.query(Recruiter).filter(Recruiter.recruiter_id.in_(chunk)).delete(synchronize_session=False)
        db.commit()

    return deleted_ids, kept_ids, cluster_summaries


def write_report(dry_run: bool, plan, deleted_ids, kept_ids, cluster_summaries):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "clusters_selected": len(plan),
        "deleted_copies": len(deleted_ids),
        "kept_canonicals": len(set(kept_ids)),
        "cluster_summaries": cluster_summaries[:50],
        "deleted_ids_sample": deleted_ids[:100],
        "kept_ids_sample": kept_ids[:100],
    }
    json_path = OUTPUT_DIR / "duplicate_delete_report.json"
    md_path = OUTPUT_DIR / "duplicate_delete_report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(
        "\n".join([
            "# Duplicate Delete Report",
            "",
            f"- Timestamp: `{report['timestamp']}`",
            f"- Dry run: `{dry_run}`",
            f"- Clusters selected: `{report['clusters_selected']}`",
            f"- Deleted copies: `{report['deleted_copies']}`",
            f"- Kept canonicals: `{report['kept_canonicals']}`",
        ]),
        encoding="utf-8",
    )
    return str(md_path), str(json_path)


def main():
    parser = argparse.ArgumentParser(description="Delete verified duplicate recruiters, keeping the richest canonical copy.")
    parser.add_argument("--apply", action="store_true", help="Apply the deletions.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        records = build_records(db)
        clusters, _ = build_cluster_data(records)
        records_by_id = {record["recruiter_id"]: record for record in records}
        plan = build_delete_plan(clusters)
        deleted_ids, kept_ids, cluster_summaries = execute_delete_plan(db, records_by_id, plan, dry_run=not args.apply)
        md_path, json_path = write_report(not args.apply, plan, deleted_ids, kept_ids, cluster_summaries)
        print(json.dumps({
            "dry_run": not args.apply,
            "clusters_selected": len(plan),
            "deleted_copies": len(deleted_ids),
            "kept_canonicals": len(set(kept_ids)),
            "report_md": md_path,
            "report_json": json_path,
        }, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
