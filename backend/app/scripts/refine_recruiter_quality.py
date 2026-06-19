from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.models.models import Company, Recruiter
from app.utils.normalizer import normalize_text, extract_domain
from app.utils.state_recovery import infer_state_from_sources


PLACEHOLDER_DOMAINS = {
    "missing.local",
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "live.com",
    "msn.com",
}


def company_domain(company: Company | None) -> str:
    if not company:
        return ""
    return extract_domain(company.website or company.email_pattern or "")


def calc_completeness(recruiter: Recruiter, company: Company | None) -> int:
    score = 0
    if recruiter.recruiter_name:
        score += 15
    if recruiter.email and "@missing.local" not in recruiter.email:
        score += 20
    if recruiter.phone:
        score += 15
    if recruiter.linkedin:
        score += 10
    if recruiter.company_id or company:
        score += 15
    if recruiter.location:
        score += 10
    if recruiter.state:
        score += 10
    if recruiter.specialization or recruiter.title:
        score += 10
    if recruiter.notes:
        score += 5
    return min(score, 100)


def build_review_flags(recruiter: Recruiter, company: Company | None) -> list[str]:
    flags: list[str] = []
    if not recruiter.company_id:
        flags.append("missing_company")
    if not recruiter.state:
        flags.append("missing_state")
    if not recruiter.phone and not recruiter.linkedin:
        flags.append("thin_contact_profile")
    domain = extract_domain(recruiter.email or "")
    if domain in PLACEHOLDER_DOMAINS:
        flags.append("personal_email_domain")
    if recruiter.recruiter_name and len(recruiter.recruiter_name.strip()) <= 2:
        flags.append("suspicious_short_name")
    if company and recruiter.company_id and not company.company_name:
        flags.append("blank_company_name")
    return flags


def infer_state(recruiter: Recruiter, company: Company | None):
    return infer_state_from_sources(
        [
            ("recruiter_location", recruiter.location),
            ("company_state", company.state if company else None),
            ("company_location", company.location if company else None),
            ("notes", recruiter.notes),
            ("review_reason", recruiter.review_reason),
            ("metadata_json", recruiter.metadata_json),
            ("raw_data", recruiter.raw_data),
        ]
    )


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        company_by_id = {company.company_id: company for company in companies}

        updated = 0
        inferred_states = 0
        review_counts = Counter()

        last_recruiter_id = 0
        batch_size = 1000
        processed = 0
        while True:
            recruiters = (
                db.query(Recruiter)
                .filter(Recruiter.recruiter_id > last_recruiter_id)
                .order_by(Recruiter.recruiter_id.asc())
                .limit(batch_size)
                .all()
            )
            if not recruiters:
                break

            for recruiter in recruiters:
                company = company_by_id.get(recruiter.company_id)
                changed = False

                normalized_name = normalize_text(recruiter.recruiter_name or "")
                if recruiter.normalized_recruiter_name != normalized_name:
                    recruiter.normalized_recruiter_name = normalized_name
                    changed = True

                completeness = calc_completeness(recruiter, company)
                if recruiter.completeness_score != completeness:
                    recruiter.completeness_score = completeness
                    changed = True

                if not recruiter.state:
                    inferred = infer_state(recruiter, company)
                    if inferred:
                        recruiter.state = inferred["state"]
                        recruiter.state_source = inferred["state_source"]
                        recruiter.state_confidence = inferred["state_confidence"]
                        recruiter.state_reason = inferred["state_reason"]
                        inferred_states += 1
                        changed = True

                flags = build_review_flags(recruiter, company)
                for flag in flags:
                    review_counts[flag] += 1

                desired_needs_review = bool(flags) or completeness < 45
                if recruiter.needs_review != desired_needs_review:
                    recruiter.needs_review = desired_needs_review
                    changed = True

                computed_reason = ", ".join(flags[:4]) if flags else None
                if desired_needs_review and recruiter.review_reason != computed_reason:
                    recruiter.review_reason = computed_reason
                    changed = True
                elif not desired_needs_review and recruiter.review_reason in {None, "", computed_reason}:
                    recruiter.review_reason = None
                    changed = True

                desired_location_confidence = "high" if recruiter.state else ("low" if recruiter.location else "manual_review")
                if recruiter.location_confidence != desired_location_confidence:
                    recruiter.location_confidence = desired_location_confidence
                    changed = True

                metadata = {}
                if recruiter.metadata_json:
                    try:
                        metadata = recruiter.metadata_json if isinstance(recruiter.metadata_json, dict) else json.loads(recruiter.metadata_json)
                    except Exception:
                        metadata = {}
                quality_summary = {
                    "completeness_score": completeness,
                    "needs_review": desired_needs_review,
                    "review_flags": flags,
                    "email_domain": extract_domain(recruiter.email or ""),
                    "company_domain": company_domain(company),
                }
                if metadata.get("quality_summary") != quality_summary:
                    metadata["quality_summary"] = quality_summary
                    recruiter.metadata_json = json.dumps(metadata, default=str)
                    changed = True

                if changed:
                    updated += 1

            processed += len(recruiters)
            last_recruiter_id = recruiters[-1].recruiter_id
            db.commit()
            print(f"processed={processed} updated={updated} inferred_states={inferred_states}")

        db.commit()
        print(f"updated_records={updated}")
        print(f"inferred_states={inferred_states}")
        print(f"top_review_flags={review_counts.most_common(10)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
