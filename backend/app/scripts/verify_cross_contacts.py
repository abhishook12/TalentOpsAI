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

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.contact_verification import build_contact_fingerprints, summarize_cluster
from app.utils.normalizer import normalize_text


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

GENERIC_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "msn.com",
    "live.com",
    "proton.me",
    "protonmail.com",
}

GENERIC_NAMES = {
    "name",
    "unknown",
    "recruiter",
    "recruiter name",
    "test",
    "n a",
    "na",
    "none",
    "null",
}


def merge_review_reason(existing: str | None, new_reason: str) -> str:
    existing_text = (existing or "").strip()
    new_text = (new_reason or "").strip()
    if not existing_text:
        return new_text

    prefix_end = existing_text.find("Cross-contact")
    prefix = existing_text[:prefix_end].strip() if prefix_end >= 0 else existing_text
    prefix = prefix.rstrip(".").strip()

    cross_contact_segments = []
    seen = set()
    for segment in re.findall(r"Cross-contact[^.]*\.", existing_text):
        cleaned = segment.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            cross_contact_segments.append(cleaned)

    normalized_new = new_text if new_text.endswith(".") else f"{new_text}."
    if normalized_new not in seen:
        cross_contact_segments.append(normalized_new)

    tail = " ".join(cross_contact_segments).strip()
    if prefix and tail:
        return f"{prefix} {tail}".strip()
    return tail or prefix or normalized_new


def _normalize_email(value: Any) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


def _normalize_phone(value: Any) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", str(value))


def _normalize_linkedin(value: Any) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = text.replace("https://", "").replace("http://", "")
    text = text.replace("www.", "")
    return text.rstrip("/")


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, index: int) -> int:
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
        elif self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
        else:
            self.parent[root_right] = root_left
            self.rank[root_left] += 1


def build_records(db):
    rows = (
        db.query(Recruiter, Company.company_name, Company.normalized_company_name)
        .outerjoin(Company, Recruiter.company_id == Company.company_id)
        .order_by(Recruiter.recruiter_id.asc())
        .all()
    )

    records = []
    for recruiter, company_name, company_normalized_name in rows:
        fingerprints = build_contact_fingerprints(recruiter, company_name, company_normalized_name)
        fingerprints["recruiter_id"] = recruiter.recruiter_id
        fingerprints["recruiter_name"] = recruiter.recruiter_name
        fingerprints["company_name"] = company_name
        fingerprints["company_normalized_name"] = company_normalized_name
        fingerprints["state"] = recruiter.state
        fingerprints["needs_review"] = bool(recruiter.needs_review)
        fingerprints["is_active"] = bool(recruiter.is_active)
        fingerprints["completeness_score"] = recruiter.completeness_score or 0
        fingerprints["trust_score"] = recruiter.trust_score or 0
        fingerprints["last_scan_at"] = recruiter.last_scan_at
        fingerprints["instance"] = recruiter
        records.append(fingerprints)
    return records


def build_cluster_data(records):
    uf = UnionFind(len(records))
    email_map: dict[str, list[int]] = defaultdict(list)
    phone_map: dict[str, list[int]] = defaultdict(list)
    linkedin_map: dict[str, list[int]] = defaultdict(list)
    name_company_map: dict[str, list[int]] = defaultdict(list)

    for index, record in enumerate(records):
        for email in record.get("emails", []):
            if email:
                email_map[email].append(index)
        for phone in record.get("phones", []):
            if phone:
                phone_map[phone].append(index)
        for linkedin in record.get("linkedins", []):
            if linkedin:
                linkedin_map[linkedin].append(index)

        name = normalize_text(record.get("recruiter_name"))
        company_key = ""
        if record.get("company_name"):
            company_key = normalize_text(record["company_name"])
        if name and company_key and name not in GENERIC_NAMES:
            name_company_map[f"{name}|{company_key}"].append(index)

    signal_maps = {
        "email": email_map,
        "phone": phone_map,
        "linkedin": linkedin_map,
    }

    for signal_name, mapping in signal_maps.items():
        for key, indices in mapping.items():
            if len(indices) < 2:
                continue
            first = indices[0]
            for other in indices[1:]:
                uf.union(first, other)

    clusters: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        clusters[uf.find(index)].append(index)

    cluster_rows: list[dict[str, Any]] = []
    for cluster_id, member_indices in enumerate(sorted(clusters.values(), key=len, reverse=True), start=1):
        member_records = [records[index] for index in member_indices]
        signals = set()
        for index in member_indices:
            record = records[index]
            if any(email_map[email] and len(email_map[email]) > 1 for email in record.get("emails", [])):
                signals.add("email")
            if any(phone_map[phone] and len(phone_map[phone]) > 1 for phone in record.get("phones", [])):
                signals.add("phone")
            if any(linkedin_map[linkedin] and len(linkedin_map[linkedin]) > 1 for linkedin in record.get("linkedins", [])):
                signals.add("linkedin")
        cluster = {"indices": set(member_indices), "keys": set(), "strong_signals": signals}
        cluster_rows.append(summarize_cluster(cluster_id, cluster, member_records))

    same_name_company_groups: list[dict[str, Any]] = []
    for key, indices in name_company_map.items():
        if len(indices) < 2:
            continue
        member_records = [records[index] for index in indices]
        shared_contact_overlap = False
        emails = set()
        phones = set()
        linkedins = set()
        for record in member_records:
            emails.update(record.get("emails", []))
            phones.update(record.get("phones", []))
            linkedins.update(record.get("linkedins", []))
        if any(
            len({value for value in values if value}) < len(member_records)
            for values in (emails, phones, linkedins)
        ):
            shared_contact_overlap = True

        same_name_company_groups.append({
            "group_key": key,
            "size": len(member_records),
            "shared_contact_overlap": shared_contact_overlap,
            "records": [
                {
                    "recruiter_id": record.get("recruiter_id"),
                    "recruiter_name": record.get("recruiter_name"),
                    "email": record.get("email"),
                    "phone": record.get("phone"),
                    "company_name": record.get("company_name"),
                    "state": record.get("state"),
                }
                for record in member_records[:20]
            ],
        })

    return cluster_rows, same_name_company_groups


def apply_updates(db, records, clusters, same_name_company_groups, dry_run: bool = True):
    records_by_id = {record["recruiter_id"]: record for record in records}
    touched = 0
    flagged = 0
    updates: list[dict[str, Any]] = []

    for cluster in clusters:
        size = int(cluster.get("size") or 0)
        if size < 2:
            continue
        confidence = cluster.get("confidence") or "low"
        if confidence == "low":
            continue

        canonical_id = cluster.get("canonical_recruiter_id")
        for member in cluster.get("members", []):
            recruiter_id = member["recruiter_id"]
            record = records_by_id.get(recruiter_id)
            if not record:
                continue
            if recruiter_id == canonical_id:
                continue

            instance: Recruiter = record["instance"]
            meta = {}
            if instance.metadata_json:
                try:
                    meta = json.loads(instance.metadata_json) if isinstance(instance.metadata_json, str) else dict(instance.metadata_json)
                except Exception:
                    meta = {"raw_metadata": str(instance.metadata_json)}

            contact_meta = meta.get("contact_verification") if isinstance(meta.get("contact_verification"), dict) else {}
            contact_meta.update({
                "cluster_id": cluster.get("cluster_id"),
                "cluster_size": size,
                "confidence": confidence,
                "role": "duplicate",
                "canonical_recruiter_id": canonical_id,
                "strong_signals": cluster.get("strong_signals", []),
                "verified_at": datetime.utcnow().isoformat(),
            })
            meta["contact_verification"] = contact_meta
            new_reason = f"Cross-contact verifier found duplicate cluster #{cluster.get('cluster_id')} via {', '.join(cluster.get('strong_signals', [])) or 'shared contact data'}."
            updates.append({
                "recruiter_id": recruiter_id,
                "needs_review": True,
                "review_reason": merge_review_reason(instance.review_reason, new_reason),
                "last_scan_at": datetime.utcnow(),
                "metadata_json": json.dumps(meta, default=str),
            })
            touched += 1

    for group in same_name_company_groups:
        for member in group.get("records", []):
            record = records_by_id.get(member["recruiter_id"])
            if not record:
                continue
            instance: Recruiter = record["instance"]
            meta = {}
            if instance.metadata_json:
                try:
                    meta = json.loads(instance.metadata_json) if isinstance(instance.metadata_json, str) else dict(instance.metadata_json)
                except Exception:
                    meta = {"raw_metadata": str(instance.metadata_json)}
            contact_meta = meta.get("contact_verification") if isinstance(meta.get("contact_verification"), dict) else {}
            contact_meta.update({
                "group_key": group["group_key"],
                "role": "review_candidate",
                "reason": "same_name_same_company",
                "shared_contact_overlap": bool(group.get("shared_contact_overlap")),
                "verified_at": datetime.utcnow().isoformat(),
            })
            meta["contact_verification"] = contact_meta
            group_reason = "Cross-contact review candidate: same name and company."
            if group.get("shared_contact_overlap"):
                group_reason = "Cross-contact review candidate: same name, same company, and overlapping contact data."
            updates.append({
                "recruiter_id": member["recruiter_id"],
                "needs_review": True,
                "review_reason": merge_review_reason(instance.review_reason, group_reason),
                "last_scan_at": datetime.utcnow(),
                "metadata_json": json.dumps(meta, default=str),
            })
            flagged += 1

    if dry_run:
        db.rollback()
        return touched, flagged

    chunk_size = 500
    for start in range(0, len(updates), chunk_size):
        db.bulk_update_mappings(Recruiter, updates[start:start + chunk_size])
    db.commit()

    return touched, flagged


def write_report(records, clusters, same_name_company_groups, touched, flagged, dry_run: bool):
    total = len(records)
    strong_clusters = [cluster for cluster in clusters if int(cluster.get("size") or 0) > 1 and cluster.get("confidence") in {"high", "medium"}]
    review_groups = [group for group in same_name_company_groups]
    confidence_counts = Counter(cluster.get("confidence", "low") for cluster in clusters if int(cluster.get("size") or 0) > 1)
    confidence_record_counts = Counter()
    confidence_duplicate_counts = Counter()
    for cluster in clusters:
        if int(cluster.get("size") or 0) <= 1:
            continue
        confidence = cluster.get("confidence", "low")
        size = int(cluster.get("size") or 0)
        confidence_record_counts[confidence] += size
        confidence_duplicate_counts[confidence] += max(size - 1, 0)

    safe_duplicate_total = confidence_duplicate_counts.get("high", 0)
    review_duplicate_total = confidence_duplicate_counts.get("medium", 0)
    weak_duplicate_total = confidence_duplicate_counts.get("low", 0)
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "total_recruiters_scanned": total,
        "duplicate_clusters": len(strong_clusters),
        "same_name_company_review_groups": len(review_groups),
        "records_marked_for_review": touched,
        "records_marked_review_candidate": flagged,
        "cluster_counts_by_confidence": dict(confidence_counts),
        "cluster_records_by_confidence": dict(confidence_record_counts),
        "duplicate_records_by_confidence": dict(confidence_duplicate_counts),
        "safe_duplicate_total": safe_duplicate_total,
        "review_duplicate_total": review_duplicate_total,
        "weak_duplicate_total": weak_duplicate_total,
        "estimated_canonical_survivors": total - safe_duplicate_total - review_duplicate_total - weak_duplicate_total,
        "strong_clusters": strong_clusters[:20],
        "review_groups": review_groups[:20],
    }

    json_path = OUTPUT_DIR / "contact_verification_report.json"
    md_path = OUTPUT_DIR / "contact_verification_report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Cross Contact Verification Report",
        "",
        f"- Timestamp: `{report['timestamp']}`",
        f"- Dry run: `{dry_run}`",
        f"- Recruiters scanned: `{total}`",
        f"- Duplicate clusters: `{report['duplicate_clusters']}`",
        f"- Same-name/company review groups: `{report['same_name_company_review_groups']}`",
        f"- Records marked for review: `{touched}`",
        f"- Records marked review candidate: `{flagged}`",
        f"- Safe duplicate copies (high confidence): `{safe_duplicate_total}`",
        f"- Review-needed duplicate copies (medium confidence): `{review_duplicate_total}`",
        f"- Weak duplicate copies (low confidence): `{weak_duplicate_total}`",
        "",
        "## Confidence Breakdown",
        f"- High-confidence clusters: `{confidence_counts.get('high', 0)}`",
        f"- Medium-confidence clusters: `{confidence_counts.get('medium', 0)}`",
        f"- Low-confidence clusters: `{confidence_counts.get('low', 0)}`",
        "",
        "## Strong Clusters",
    ]
    if strong_clusters:
        for cluster in strong_clusters[:20]:
            lines.append(
                f"- Cluster {cluster['cluster_id']} ({cluster['confidence']}, size {cluster['size']}): "
                f"{cluster.get('canonical_name') or 'Unknown'} / {cluster.get('canonical_email') or 'No email'}"
            )
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Review Groups")
    if review_groups:
        for group in review_groups[:20]:
            lines.append(f"- {group['group_key']} (size {group['size']})")
    else:
        lines.append("- None")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return str(md_path), str(json_path)


def main():
    parser = argparse.ArgumentParser(description="Cross-contact verification across the recruiter database.")
    parser.add_argument("--apply", action="store_true", help="Persist review flags and metadata.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        records = build_records(db)
        clusters, same_name_company_groups = build_cluster_data(records)
        touched, flagged = apply_updates(db, records, clusters, same_name_company_groups, dry_run=not args.apply)
        md_path, json_path = write_report(records, clusters, same_name_company_groups, touched, flagged, dry_run=not args.apply)
        print(json.dumps({
            "dry_run": not args.apply,
            "scanned": len(records),
            "duplicate_clusters": len([c for c in clusters if int(c.get("size") or 0) > 1 and c.get("confidence") in {"high", "medium"}]),
            "records_marked_for_review": touched,
            "records_marked_review_candidate": flagged,
            "report_md": md_path,
            "report_json": json_path,
        }, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
