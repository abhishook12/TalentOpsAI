from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal
from app.models.models import Company, Recruiter
from app.utils.normalizer import normalize_text
from app.utils.state_mapper import extract_state_detailed


SOURCE_FILE = Path(r"C:\Users\User\Desktop\for location by claude\1 the below all compny but location wise\Recruiter_Contacts_Master.xlsx")
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
BATCH_ID = f"location_workbook_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
    "proton.me", "protonmail.com", "mail.com", "msn.com", "live.com", "yandex.com", "gmx.com",
}


def norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def norm_key(value: str | None) -> str:
    return normalize_text(value or "")


def norm_email(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    return value if "@" in value else None


def norm_phone(value: str | None) -> str | None:
    digits = re.sub(r"[^0-9]", "", value or "")
    return digits[-10:] if len(digits) >= 10 else None


def parse_state(*values: str | None):
    for value in values:
        if not value:
            continue
        state, reason = extract_state_detailed(value)
        if state:
            return state, reason
    return None, None


def profile_identity(name: str | None, email: str | None, phone: str | None, company: str | None):
    if email:
        return f"email::{email}"
    if phone:
        return f"phone::{phone}"
    if name and company:
        return f"name_company::{norm_key(name)}::{norm_key(company)}"
    return None


def parse_workbook():
    workbook = load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    profiles: dict[str, dict] = {}
    source_row_count = 0
    sheet_counts = Counter()

    for sheet in workbook.worksheets:
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [norm_text(str(cell)) if cell is not None else "" for cell in rows[0]]
        header_map = {header.lower(): idx for idx, header in enumerate(headers) if header}
        sheet_counts[sheet.title] += max(len(rows) - 1, 0)

        for row_index, row in enumerate(rows[1:], start=2):
            source_row_count += 1
            values = [norm_text(str(cell)) if cell is not None else "" for cell in row]

            def cell(*names, default=""):
                for name in names:
                    idx = header_map.get(name)
                    if idx is not None and idx < len(values):
                        return values[idx]
                return default

            name = cell("name")
            email = norm_email(cell("email", "email address", "email id"))
            phone = norm_phone(cell("phone", "mobile", "cell"))
            company = cell("company", "organization", "org") or (values[2] if len(values) > 2 else "")
            location = cell("location", "office location", "hq location") or (values[3] if len(values) > 3 else "")
            country = cell("country")
            office_location = cell("office location")
            hq_location = cell("hq location")

            state, state_reason = parse_state(location, office_location, hq_location, country)
            identity = profile_identity(name, email, phone, company)
            if not identity:
                continue

            profile = profiles.setdefault(
                identity,
                {
                    "identity_key": identity,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "company": company,
                    "locations": [],
                    "states": Counter(),
                    "sheet_names": set(),
                    "source_rows": [],
                },
            )

            if name and not profile["name"]:
                profile["name"] = name
            if email and not profile["email"]:
                profile["email"] = email
            if phone and not profile["phone"]:
                profile["phone"] = phone
            if company and not profile["company"]:
                profile["company"] = company
            if location:
                profile["locations"].append(location)
            if state:
                profile["states"][state] += 1
            profile["sheet_names"].add(sheet.title)
            profile["source_rows"].append(
                {
                    "sheet": sheet.title,
                    "row": row_index,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "company": company,
                    "location": location,
                    "office_location": office_location,
                    "hq_location": hq_location,
                    "country": country,
                    "state": state,
                    "state_reason": state_reason,
                }
            )

    company_groups: dict[str, list[dict]] = defaultdict(list)
    for profile in profiles.values():
        company_groups[norm_key(profile.get("company"))].append(profile)

    for profile in profiles.values():
        profile["sheet_names"] = sorted(profile["sheet_names"])
        profile["locations"] = list(dict.fromkeys([loc for loc in profile["locations"] if loc]))
        profile["source_row_count"] = len(profile["source_rows"])
        if profile["states"]:
            profile["dominant_state"], profile["dominant_state_count"] = profile["states"].most_common(1)[0]
        else:
            profile["dominant_state"], profile["dominant_state_count"] = None, 0
        profile["company_group_size"] = len(company_groups[norm_key(profile.get("company"))])

    return list(profiles.values()), source_row_count, sheet_counts, company_groups


def build_db_indexes(session):
    company_rows = session.query(Company).all()
    company_by_norm = {row.normalized_company_name or norm_key(row.company_name): row for row in company_rows if row.company_name}
    company_by_id = {row.company_id: row for row in company_rows}

    recruiters = session.query(Recruiter).all()

    email_index = {}
    phone_index = {}
    name_company_index = defaultdict(list)
    for row in recruiters:
        if row.email:
            email_index[row.email.strip().lower()] = row
        phone = norm_phone(row.phone)
        if phone:
            phone_index[phone] = row
        company_name = company_by_id.get(row.company_id).company_name if row.company_id and company_by_id.get(row.company_id) else ""
        if row.recruiter_name and company_name:
            name_company_index[f"{norm_key(row.recruiter_name)}::{norm_key(company_name)}"].append(row)

    return company_by_norm, company_by_id, email_index, phone_index, name_company_index


def get_or_create_company(session, company_name: str | None, company_state: str | None, company_location: str | None, company_cache: dict[str, Company]):
    if not company_name:
        return None, False
    norm_company = norm_key(company_name)
    if norm_company in company_cache:
        company = company_cache[norm_company]
        changed = False
        if not company.state and company_state:
            company.state = company_state
            changed = True
        if not company.location and company_location:
            company.location = company_location
            changed = True
        return company, changed

    company = Company(
        company_name=company_name,
        normalized_company_name=norm_company,
        location=company_location,
        state=company_state,
        data_source="location_workbook",
        source_job_id=BATCH_ID,
        is_active=True,
    )
    session.add(company)
    session.flush()
    company_cache[norm_company] = company
    return company, True


def merge_metadata(existing_value, evidence):
    metadata = {}
    if existing_value:
        try:
            parsed = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
            if isinstance(parsed, dict):
                metadata = dict(parsed)
        except Exception:
            metadata = {"raw_metadata": str(existing_value)}
    metadata["location_workbook_evidence"] = evidence
    return json.dumps(metadata, default=str)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Workbook not found: {SOURCE_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profiles, source_row_count, sheet_counts, company_groups = parse_workbook()

    session = SessionLocal()
    try:
        company_cache = {}
        db_company_norm_map, db_company_by_id, email_index, phone_index, name_company_index = build_db_indexes(session)
        company_cache.update(db_company_norm_map)

        existing_matches = []
        unique_candidates = []
        skipped_no_qualification = []
        ambiguous_existing = []
        stats = Counter()
        source_state_counts = Counter()
        company_state_summary = {}
        state_before = session.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar() or 0
        unknown_before = session.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar() or 0
        company_count_before = session.execute(text("SELECT COUNT(*) FROM companies")).scalar() or 0

        for profile in profiles:
            if not profile.get("phone") and not profile.get("locations"):
                skipped_no_qualification.append(profile)
                stats["skipped_no_phone_or_location"] += 1
                continue

            email = profile.get("email")
            phone = profile.get("phone")
            key = f"{norm_key(profile.get('name'))}::{norm_key(profile.get('company'))}" if profile.get("name") and profile.get("company") else None
            match = None
            match_type = None
            if email and email in email_index:
                match = email_index[email]
                match_type = "email"
            elif phone and phone in phone_index:
                match = phone_index[phone]
                match_type = "phone"
            elif key and key in name_company_index:
                matches = name_company_index[key]
                if len(matches) == 1:
                    match = matches[0]
                    match_type = "name_company"
                else:
                    ambiguous_existing.append(profile)
                    stats["ambiguous_existing"] += 1
                    continue

            if match:
                existing_matches.append(
                    {
                        "profile": profile,
                        "matched_recruiter_id": match.recruiter_id,
                        "matched_recruiter_name": match.recruiter_name,
                        "match_type": match_type,
                    }
                )
                stats[f"matched_{match_type}"] += 1
            else:
                unique_candidates.append(profile)
                stats["unique"] += 1

            if profile.get("dominant_state"):
                source_state_counts[profile["dominant_state"]] += 1
            company_key = norm_key(profile.get("company"))
            if company_key:
                company_state_summary.setdefault(company_key, Counter())
                if profile.get("dominant_state"):
                    company_state_summary[company_key][profile["dominant_state"]] += 1

        inserted_recruiters = 0
        updated_recruiters = 0
        companies_created = 0
        companies_updated = 0
        inserted_examples = []
        enriched_examples = []

        if args.apply:
            # First update existing recruiters with safe workbook evidence.
            for chunk_start in range(0, len(existing_matches), args.batch_size):
                chunk = existing_matches[chunk_start:chunk_start + args.batch_size]
                for item in chunk:
                    profile = item["profile"]
                    recruiter = email_index.get(profile.get("email"))
                    if not recruiter and profile.get("phone"):
                        recruiter = phone_index.get(profile.get("phone"))
                    if not recruiter and profile.get("name") and profile.get("company"):
                        recruiter_matches = name_company_index.get(f"{norm_key(profile.get('name'))}::{norm_key(profile.get('company'))}", [])
                        recruiter = recruiter_matches[0] if len(recruiter_matches) == 1 else None
                    if not recruiter:
                        continue

                    company_name = profile.get("company")
                    company_state = profile.get("dominant_state")
                    company_location = profile.get("locations")[0] if profile.get("locations") else None
                    company, company_changed = get_or_create_company(session, company_name, company_state, company_location, company_cache)
                    if company and recruiter.company_id != company.company_id:
                        recruiter.company_id = company.company_id
                        company_changed = True

                    profile_state = profile.get("dominant_state")
                    workbook_location = profile.get("locations")[0] if profile.get("locations") else None
                    evidence = {
                        "batch_id": BATCH_ID,
                        "source_file": str(SOURCE_FILE),
                        "match_type": item["match_type"],
                        "workbook_name": profile.get("name"),
                        "workbook_email": profile.get("email"),
                        "workbook_phone": profile.get("phone"),
                        "workbook_company": profile.get("company"),
                        "workbook_locations": profile.get("locations"),
                        "workbook_dominant_state": profile_state,
                        "workbook_sheet_names": profile.get("sheet_names"),
                    }

                    changed = False
                    if not recruiter.location and workbook_location:
                        recruiter.location = workbook_location
                        changed = True

                    if not recruiter.state and profile_state:
                        recruiter.state = profile_state
                        recruiter.state_source = "location_workbook"
                        recruiter.state_confidence = "high"
                        recruiter.state_reason = "location_workbook_dominant_state"
                        changed = True

                    if recruiter.state and profile_state and recruiter.state != profile_state:
                        evidence["state_conflict"] = {
                            "db_state": recruiter.state,
                            "workbook_state": profile_state,
                        }

                    if recruiter.needs_review and (recruiter.state or recruiter.location):
                        recruiter.needs_review = False
                        recruiter.review_reason = None
                        changed = True

                    recruiter.metadata_json = merge_metadata(recruiter.metadata_json, evidence)
                    recruiter.last_scan_at = datetime.now(timezone.utc)
                    if changed or company_changed:
                        updated_recruiters += 1
                        if len(enriched_examples) < 20:
                            enriched_examples.append(
                                {
                                    "recruiter_id": recruiter.recruiter_id,
                                    "recruiter_name": recruiter.recruiter_name,
                                    "email": recruiter.email,
                                    "company": company_name,
                                    "match_type": item["match_type"],
                                    "state": recruiter.state,
                                    "location": recruiter.location,
                                }
                            )

                session.commit()

            # Then insert only truly unique candidates with the minimum qualification.
            for profile in unique_candidates:
                company_name = profile.get("company")
                profile_state = profile.get("dominant_state")
                workbook_location = profile.get("locations")[0] if profile.get("locations") else None
                if not profile.get("phone") and not workbook_location:
                    continue

                company_location = workbook_location
                company_state = profile_state
                company, company_changed = get_or_create_company(session, company_name, company_state, company_location, company_cache)
                if company_changed:
                    if company and company.company_id not in db_company_by_id:
                        companies_created += 1
                    else:
                        companies_updated += 1

                recruiter = Recruiter(
                    recruiter_name=profile.get("name") or "Unknown",
                    normalized_recruiter_name=norm_key(profile.get("name")) or None,
                    email=profile.get("email"),
                    phone=profile.get("phone"),
                    company_id=company.company_id if company else None,
                    location=workbook_location,
                    state=profile_state,
                    state_source="location_workbook" if profile_state else None,
                    state_confidence="high" if profile_state else None,
                    state_reason="location_workbook_dominant_state" if profile_state else None,
                    needs_review=not bool(profile_state),
                    review_reason=None if profile_state else "Workbook row qualified by phone/location but state could not be derived",
                    data_source="location_workbook",
                    source_job_id=BATCH_ID,
                    raw_data=json.dumps(profile.get("source_rows", []), default=str),
                    metadata_json=json.dumps(
                        {
                            "batch_id": BATCH_ID,
                            "source_file": str(SOURCE_FILE),
                            "workbook_name": profile.get("name"),
                            "workbook_email": profile.get("email"),
                            "workbook_phone": profile.get("phone"),
                            "workbook_company": company_name,
                            "workbook_locations": profile.get("locations"),
                            "workbook_sheet_names": profile.get("sheet_names"),
                            "workbook_source_row_count": profile.get("source_row_count"),
                            "workbook_dominant_state": profile_state,
                        },
                        default=str,
                    ),
                )
                session.add(recruiter)
                inserted_recruiters += 1
                if len(inserted_examples) < 20:
                    inserted_examples.append(
                        {
                            "name": recruiter.recruiter_name,
                            "email": recruiter.email,
                            "company": company_name,
                            "phone": recruiter.phone,
                            "state": recruiter.state,
                            "location": recruiter.location,
                        }
                    )

                if inserted_recruiters % args.batch_size == 0:
                    session.commit()

            session.commit()

        state_after = session.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar() or 0
        unknown_after = session.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar() or 0
        company_count_after = session.execute(text("SELECT COUNT(*) FROM companies")).scalar() or 0
        state_counts = session.execute(text("""
            SELECT state, COUNT(*) AS cnt
            FROM recruiters
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state
            ORDER BY cnt DESC, state ASC
        """)).mappings().all()

        report = {
            "batch_id": BATCH_ID,
            "source_file": str(SOURCE_FILE),
            "apply": bool(args.apply),
            "source_row_count": source_row_count,
            "merged_profiles": len(profiles),
            "existing_matches": len(existing_matches),
            "unique_candidates": len(unique_candidates),
            "skipped_no_phone_or_location": len(skipped_no_qualification),
            "ambiguous_existing": len(ambiguous_existing),
            "stats": dict(stats),
            "source_state_counts": dict(source_state_counts),
            "state_before": int(state_before),
            "state_after": int(state_after),
            "unknown_before": int(unknown_before),
            "unknown_after": int(unknown_after),
            "company_count_before": int(company_count_before),
            "company_count_after": int(company_count_after),
            "inserted_recruiters": int(inserted_recruiters),
            "updated_recruiters": int(updated_recruiters),
            "companies_created": int(companies_created),
            "companies_updated": int(companies_updated),
            "inserted_examples": inserted_examples,
            "enriched_examples": enriched_examples,
            "skipped_examples": skipped_no_qualification[:20],
            "state_counts": {row["state"]: int(row["cnt"]) for row in state_counts},
            "top_company_state_breakdown": {
                company_key: dict(counter.most_common())
                for company_key, counter in sorted(company_state_summary.items(), key=lambda item: (-sum(item[1].values()), item[0]))[:25]
            },
        }

        json_path = OUTPUT_DIR / "location_workbook_apply_report.json"
        md_path = OUTPUT_DIR / "location_workbook_apply_report.md"
        json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

        lines = [
            "# Location Workbook Apply Report",
            "",
            f"Source workbook: `{SOURCE_FILE}`",
            f"Batch id: `{BATCH_ID}`",
            "",
            "## Results",
            f"- Source rows: `{source_row_count}`",
            f"- Merged profiles: `{len(profiles)}`",
            f"- Existing matches: `{len(existing_matches)}`",
            f"- Unique candidates: `{len(unique_candidates)}`",
            f"- Skipped missing phone/location: `{len(skipped_no_qualification)}`",
            f"- Ambiguous existing matches: `{len(ambiguous_existing)}`",
            f"- Inserted recruiters: `{inserted_recruiters}`",
            f"- Updated recruiters: `{updated_recruiters}`",
            f"- Companies created: `{companies_created}`",
            f"- Companies updated: `{companies_updated}`",
            "",
            "## Database impact",
            f"- State before: `{state_before}`",
            f"- State after: `{state_after}`",
            f"- Unknown before: `{unknown_before}`",
            f"- Unknown after: `{unknown_after}`",
            f"- Companies before: `{company_count_before}`",
            f"- Companies after: `{company_count_after}`",
            "",
            "## Top state evidence",
        ]
        for state, count in Counter(source_state_counts).most_common(20):
            lines.append(f"- {state}: `{count}`")
        lines.extend([
            "",
            "## Files",
            f"- JSON: `{json_path}`",
            f"- Markdown: `{md_path}`",
        ])
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))

    finally:
        session.close()


if __name__ == "__main__":
    main()
