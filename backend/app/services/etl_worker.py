import json
import os
import traceback
from datetime import datetime

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.models import Company, RawUpload, Recruiter, UploadJob
from ..utils.normalizer import extract_domain, normalize_text
from ..utils.state_normalizer import normalize_state_name
from ..utils.state_recovery import build_company_domain_state_index, infer_state_from_sources
from ..services.job_tracker import mark_progress, utc_now
from ..services.adaptive_parser import parse_file
from ..services.dedup_engine import deduplicate_and_enrich

def build_company_name(company_name: str | None) -> str | None:
    if not company_name:
        return None
    value = str(company_name).strip()
    return value if value else None

def get_or_create_company(
    db: Session,
    source_job_id: str | None,
    company_name: str | None,
    location: str | None,
    state: str | None,
    email: str | None,
    company_cache: dict[str, int],
):
    company_name = build_company_name(company_name)
    if not company_name:
        return None

    normalized_name = normalize_text(company_name)
    if not normalized_name:
        return None

    if normalized_name in company_cache:
        return company_cache[normalized_name]

    company = db.query(Company).filter(Company.normalized_company_name == normalized_name).first()
    if company:
        company_cache[normalized_name] = company.company_id
        return company.company_id

    domain = extract_domain(email) if email else ""
    if domain and domain not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}:
        company = db.query(Company).filter(
            (Company.website.ilike(f"%{domain}%")) |
            (Company.email_pattern.ilike(f"%{domain}%"))
        ).first()
        if company:
            company_cache[normalized_name] = company.company_id
            return company.company_id

    company = Company(
        company_name=company_name,
        normalized_company_name=normalized_name,
        location=location,
        state=state,
        data_source="etl",
        trust_score=80,
        is_active=True,
        source_job_id=source_job_id,
    )
    db.add(company)
    db.flush()
    company_cache[normalized_name] = company.company_id
    return company.company_id

def calculate_completeness(name: str | None, email: str | None, phone: str | None, company_id: int | None, location: str | None, state: str | None) -> int:
    score = 0
    if name: score += 25
    if email: score += 25
    if phone: score += 15
    if company_id: score += 15
    if location: score += 10
    if state: score += 10
    return min(score, 100)

def process_smart_import(job_id: str, filepath: str, column_map: dict = None):
    """
    New Adaptive ETL Pipeline.
    Uses adaptive_parser and dedup_engine.
    """
    db: Session = SessionLocal()
    job = db.query(UploadJob).filter(UploadJob.job_id == job_id).first()
    
    if not job:
        db.close()
        return

    mark_progress(job, status="parsing", current_step="Parsing files (adaptive)", progress_percent=5)
    db.commit()

    try:
        # Step 1: Parse entire file with adaptive parser
        parse_result = parse_file(filepath)
        
        if parse_result.errors:
            job.errors = json.dumps([{"error": e} for e in parse_result.errors])
            job.error_message = f"Parsing failed: {parse_result.errors[0]}"
            mark_progress(job, status="failed", current_step="Parse failed", progress_percent=100)
            db.commit()
            db.close()
            return
            
        total_data_rows = parse_result.total_parsed_rows
        job.total_rows = total_data_rows
        db.commit()

        if total_data_rows == 0:
            job.errors = json.dumps([{"error": "No data rows found in file."}])
            mark_progress(job, status="mapping_failed", current_step="No rows mapped", progress_percent=100)
            db.commit()
            db.close()
            return

        mark_progress(job, status="mapping", current_step="Deduplicating rows", progress_percent=20)
        db.commit()

        # Gather all parsed rows across all sheets
        all_raw_dicts = []
        for sheet in parse_result.sheets:
            for r in sheet.parsed_rows:
                all_raw_dicts.append(r.to_dict())

        # Step 2: Run within-file Deduplication Engine
        unique_profiles, duplicate_report = deduplicate_and_enrich(all_raw_dicts)
        
        duplicate_rows_count = len(all_raw_dicts) - len(unique_profiles)
        
        mark_progress(
            job, 
            status="importing", 
            current_step="Validating against database", 
            progress_percent=40,
            duplicate_rows=duplicate_rows_count
        )
        db.commit()

        # Step 3: Database validation & insertion
        inserted = 0
        skipped = 0
        errors = 0
        processed = 0
        valid_rows = 0
        warning_rows = 0
        possible_duplicate_rows = 0
        enriched_rows = 0
        failed_rows = 0
        error_log = duplicate_report  # include dedup report in errors for visibility

        # Load existing cache
        existing_emails = {
            email for (email,) in db.query(Recruiter.email).yield_per(5000) if email
        }
        company_cache: dict[str, int] = {
            normalized: company_id
            for company_id, normalized in db.query(Company.company_id, Company.normalized_company_name).all()
            if normalized
        }
        all_companies = db.query(Company).all()
        company_by_id = {company.company_id: company for company in all_companies}
        company_domain_index = build_company_domain_state_index(all_companies)

        pending_rows = []
        for profile in unique_profiles:
            processed += 1
            try:
                email = profile.get("email")
                if not email or '@' not in email:
                    skipped += 1
                    failed_rows += 1
                    continue

                if email in existing_emails:
                    skipped += 1
                    # It's an existing db dup
                    continue

                raw_name = profile.get("name")
                fallback_name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                recruiter_name = raw_name or fallback_name

                # Normalize State
                state_val = profile.get("state")
                loc_val = profile.get("location")
                state_to_normalize = state_val or loc_val or ""
                norm_state, needs_state_review, state_review_reason = normalize_state_name(state_to_normalize)
                state_source = "state_column" if state_val else ("location_column" if loc_val and norm_state else None)
                state_confidence = "high" if state_val else ("low" if needs_state_review else "medium")

                company_name = profile.get("company")
                try:
                    company_id = get_or_create_company(
                        db,
                        job_id,
                        company_name,
                        loc_val,
                        norm_state,
                        email,
                        company_cache,
                    )
                except Exception as company_error:
                    company_id = None
                    warning_rows += 1
                    error_log.append({"row": processed, "reason": f"Company lookup failed: {company_error}"})

                needs_review = profile.get("needs_review", False)
                review_reasons = profile.get("review_reasons", [])

                metadata_dict = profile.get("metadata_json") or {}
                state_result = infer_state_from_sources(
                    [
                        ("state_column", state_val),
                        ("location_column", loc_val),
                        ("company_state", company_by_id.get(company_id).state if company_id and company_by_id.get(company_id) else None),
                        ("email_domain", email),
                    ],
                    domain_index=company_domain_index,
                )
                if state_result:
                    norm_state = state_result["state"]
                    state_source = state_result["state_source"]
                    state_confidence = state_result["state_confidence"]
                    state_review_reason = state_result["state_reason"]
                    if state_result.get("evidence"):
                        metadata_dict["state_recovery"] = {
                            "source": state_source,
                            "confidence": state_confidence,
                            "reason": state_review_reason,
                            "evidence": state_result["evidence"],
                        }

                if needs_state_review:
                    needs_review = True
                    review_reasons.append(state_review_reason)
                
                if not company_id:
                    needs_review = True
                    if "missing_company" not in review_reasons:
                        review_reasons.append("missing_company")

                # Store all review reasons in metadata
                if review_reasons:
                    metadata_dict["review_reasons"] = list(set(review_reasons))
                
                if profile.get("duplicate_match_type"):
                    possible_duplicate_rows += 1

                pending_rows.append({
                    "raw_row": {
                        "job_id": job_id,
                        "raw_data": json.dumps(profile.get("raw_data") or {}, default=str),
                        "source_filename": job.filename,
                    },
                    "recruiter_row": {
                        "recruiter_name": recruiter_name,
                        "normalized_recruiter_name": normalize_text(recruiter_name),
                        "email": email,
                        "phone": profile.get("phone"),
                        "email2": profile.get("email2"),
                        "phone2": profile.get("phone2"),
                        "email3": profile.get("email3"),
                        "phone3": profile.get("phone3"),
                        "email4": profile.get("email4"),
                        "phone4": profile.get("phone4"),
                        "linkedin": profile.get("linkedin"),
                        "title": profile.get("title"),
                        "specialization": profile.get("specialization"),
                        "notes": profile.get("notes"),
                        "company_id": company_id,
                        "location": loc_val,
                        "state": norm_state,
                        "normalized_city": normalize_text(loc_val) if loc_val else None,
                        "location_confidence": "high" if not needs_state_review else "low",
                        "state_source": state_source,
                        "state_confidence": state_confidence,
                        "state_reason": state_review_reason if needs_state_review else None,
                        "completeness_score": calculate_completeness(
                            recruiter_name, email, profile.get("phone"), company_id, loc_val, norm_state
                        ),
                        "needs_review": needs_review,
                        "review_reason": ", ".join(set(review_reasons)) if review_reasons else None,
                        "data_source": "etl",
                        "trust_score": 80 if company_id else 65,
                        "is_active": True,
                        "source_job_id": job_id,
                        "raw_data": json.dumps(profile.get("raw_data") or {}, default=str),
                        "metadata_json": json.dumps(metadata_dict, default=str),
                    },
                })
                existing_emails.add(email)
                inserted += 1
                valid_rows += 1
                if needs_review:
                    warning_rows += 1

            except Exception as e:
                errors += 1
                failed_rows += 1
                error_log.append({"row": processed, "reason": str(e)})

        # Bulk Insert
        if pending_rows:
            try:
                db.bulk_insert_mappings(RawUpload, [item["raw_row"] for item in pending_rows])
                db.bulk_insert_mappings(Recruiter, [item["recruiter_row"] for item in pending_rows])
                db.commit()
            except Exception as batch_error:
                db.rollback()
                for item in pending_rows:
                    try:
                        raw_record = RawUpload(**item["raw_row"])
                        recruiter_record = Recruiter(**item["recruiter_row"])
                        db.add(raw_record)
                        db.add(recruiter_record)
                        db.commit()
                    except Exception as row_error:
                        db.rollback()
                        errors += 1
                        failed_rows += 1
                        error_log.append({"row": "batch_retry", "reason": f"Row retry failed: {row_error}"})

        # Finalize
        if inserted == 0 and total_data_rows > 0 and duplicate_rows_count == 0:
            final_status = "mapping_failed"
        else:
            final_status = "completed"

        mark_progress(
            job,
            status=final_status,
            current_step="Import finished",
            progress_percent=100,
            processed_rows=processed,
            inserted_rows=inserted,
            skipped_rows=skipped,
            error_count=errors,
            valid_rows=valid_rows,
            warning_rows=warning_rows,
            duplicate_rows=duplicate_rows_count,
            possible_duplicate_rows=possible_duplicate_rows,
            enriched_rows=enriched_rows,
            failed_rows=failed_rows,
        )
        job.errors = json.dumps(error_log)
        job.completed_at = utc_now()
        db.commit()

    except Exception as e:
        db.rollback()
        mark_progress(job, status="failed", current_step="Import failed", progress_percent=100)
        job.errors = json.dumps([{"row": 0, "reason": f"Fatal pipeline error: {traceback.format_exc()}"}])
        job.error_message = str(e)
        job.completed_at = utc_now()
        db.commit()
    finally:
        db.close()
