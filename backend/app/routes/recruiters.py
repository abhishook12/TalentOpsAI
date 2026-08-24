import json
import re
import logging
from app.services.sync_layer import sync_manager
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload, contains_eager, selectinload
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from ..database import get_db
from ..services.auth_service import get_current_user_from_request
from ..models.auth_models import User
from ..services.auth_service import require_role
from ..models.models import Recruiter, Company

logger = logging.getLogger("talentops")

from ..utils.state_mapper import normalize_state, extract_state_detailed
from ..utils.state_recovery import infer_state_from_sources
from ..utils.filters import apply_state_filter, apply_company_filter
from ..utils.logo_domains import select_logo_domain
from ..utils.phone_normalizer import format_us_phone
from ..utils.normalizer import normalize_text, extract_domain
from .analytics import analytics_cache
router = APIRouter()

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")

class RecruiterCreate(BaseModel):
    recruiter_name: str
    email: str
    phone: Optional[str] = None
    email2: Optional[str] = None
    phone2: Optional[str] = None
    email3: Optional[str] = None
    phone3: Optional[str] = None
    email4: Optional[str] = None
    phone4: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    notes: Optional[str] = None
    company_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True
    needs_review: Optional[bool] = False
    review_reason: Optional[str] = None

class RecruiterUpdate(BaseModel):
    recruiter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    email2: Optional[str] = None
    phone2: Optional[str] = None
    email3: Optional[str] = None
    phone3: Optional[str] = None
    email4: Optional[str] = None
    phone4: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    notes: Optional[str] = None
    company_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

class RecruiterBatchUpdate(BaseModel):
    ids: List[int]
    recruiter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    email2: Optional[str] = None
    phone2: Optional[str] = None
    email3: Optional[str] = None
    phone3: Optional[str] = None
    email4: Optional[str] = None
    phone4: Optional[str] = None
    linkedin: Optional[str] = None
    specialization: Optional[str] = None
    notes: Optional[str] = None
    company_id: Optional[int] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


def _parse_json_blob(value):
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _split_loose_values(value):
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_split_loose_values(item))
        return values
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,\n;|]+", text) if part.strip()]


def _collect_text_values(value):
    if value is None:
        return []
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_collect_text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_collect_text_values(item))
        return values
    text = str(value).strip()
    return [text] if text else []


def _dedupe_values(values, normalizer):
    seen = set()
    deduped = []
    for value in values:
        normalized = normalizer(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


def _normalize_email(value):
    return str(value).strip().lower() if value else ""


def _normalize_phone(value):
    return re.sub(r"[^\d+]+", "", str(value)).strip() if value else ""


def _search_quality_tier(record):
    score = record.get("completeness_score")
    if score is None or (isinstance(score, float) and score != score):
        completeness = 0
    else:
        try:
            completeness = int(score)
        except (ValueError, TypeError):
            completeness = 0
            
    if record.get("needs_review"):
        return "needs_review"
    if completeness >= 80:
        return "high"
    if completeness >= 50:
        return "medium"
    return "low"


def _match_reason_for_row(row, query: str, normalized_query: str, query_digits: str, query_domain: str) -> str:
    normalized_recruiter_name = str(row.get("normalized_recruiter_name") or "")
    normalized_company_name = str(row.get("normalized_company_name") or "")
    if normalized_query and normalized_recruiter_name == normalized_query:
        return "recruiter_name_exact"
    if normalized_query and normalized_company_name == normalized_query:
        return "company_exact"

    emails = [row.get("email"), row.get("email2"), row.get("email3"), row.get("email4"), row.get("alternate_emails")]
    if any(_normalize_email(value) == query.lower() for value in emails if value):
        return "email_exact"

    phones = [row.get("phone"), row.get("phone2"), row.get("phone3"), row.get("phone4"), row.get("alternate_phones")]
    if query_digits and any(re.sub(r"\D+", "", _normalize_phone(value)) == query_digits for value in phones if value):
        return "phone_exact"

    if query_domain and (
        any(extract_domain(value) == query_domain for value in emails if value)
        or extract_domain(row.get("website") or "") == query_domain
        or extract_domain(row.get("email_pattern") or "") == query_domain
    ):
        return "domain_exact"

    recruiter_name = str(row.get("recruiter_name") or "").lower()
    company_name = str(row.get("company_name") or "").lower()
    q_lower = query.lower()
    if recruiter_name.startswith(q_lower):
        return "recruiter_name_prefix"
    if company_name.startswith(q_lower):
        return "company_prefix"
    if q_lower in recruiter_name:
        return "recruiter_name_fuzzy"
    if q_lower in company_name:
        return "company_fuzzy"
    return "metadata_fuzzy"


def _refine_search_score(row, query: str, normalized_query: str, query_digits: str, query_domain: str) -> int:
    score = int(row.get("relevance_score") or 0)
    normalized_recruiter_name = str(row.get("normalized_recruiter_name") or "")
    normalized_company_name = str(row.get("normalized_company_name") or "")
    q_lower = query.lower()

    if normalized_query:
        if normalized_recruiter_name == normalized_query:
            score += 120
        elif normalized_recruiter_name.startswith(normalized_query):
            score += 45
        if normalized_company_name == normalized_query:
            score += 90
        elif normalized_company_name.startswith(normalized_query):
            score += 30

    if query_domain:
        email_values = [row.get("email"), row.get("email2"), row.get("email3"), row.get("email4"), row.get("alternate_emails")]
        if any(extract_domain(value) == query_domain for value in email_values if value):
            score += 140
        if extract_domain(row.get("website") or "") == query_domain or extract_domain(row.get("email_pattern") or "") == query_domain:
            score += 110

    if query_digits:
        phone_values = [row.get("phone"), row.get("phone2"), row.get("phone3"), row.get("phone4"), row.get("alternate_phones")]
        if any(re.sub(r"\D+", "", _normalize_phone(value)) == query_digits for value in phone_values if value):
            score += 120

    location = str(row.get("location") or "").lower()
    state = str(row.get("state") or row.get("company_state") or "").lower()
    if q_lower and q_lower in location:
        score += 28
    if q_lower and q_lower == state:
        score += 36

    completeness = int(row.get("completeness_score") or 0)
    score += min(completeness // 4, 25)
    if row.get("is_active"):
        score += 8
    if row.get("needs_review"):
        score -= 20
    if row.get("location_confidence") == "high":
        score += 8
    elif row.get("location_confidence") == "manual_review":
        score -= 8
    if row.get("state_source") in {"company_state", "email_domain_company", "location_workbook"}:
        score += 6

    return score


def _extract_emails_from_text(values):
    matches = []
    for value in values:
        matches.extend(EMAIL_PATTERN.findall(str(value)))
    return _dedupe_values(matches, _normalize_email)


def _extract_phones_from_text(values):
    matches = []
    for value in values:
        for match in PHONE_PATTERN.findall(str(value)):
            digits = _normalize_phone(match)
            if len(re.sub(r"\D+", "", digits)) < 10:
                continue
            matches.append(digits)
    return _dedupe_values(matches, lambda item: re.sub(r"\D+", "", _normalize_phone(item)))


def _collect_all_contacts(record):
    raw = _parse_json_blob(getattr(record, "raw_data", None)) or {}
    metadata = _parse_json_blob(getattr(record, "metadata_json", None)) or {}
    source_texts = _collect_text_values(raw) + _collect_text_values(metadata)

    direct_emails = [
        getattr(record, "email", None),
        getattr(record, "email2", None),
        getattr(record, "email3", None),
        getattr(record, "email4", None),
    ]
    direct_phones = [
        getattr(record, "phone", None),
        getattr(record, "phone2", None),
        getattr(record, "phone3", None),
        getattr(record, "phone4", None),
    ]

    metadata_emails = (
        _split_loose_values(getattr(record, "alternate_emails", None))
        + _split_loose_values(metadata.get("all_emails"))
        + _split_loose_values(metadata.get("extra_emails"))
    )
    metadata_phones = (
        _split_loose_values(getattr(record, "alternate_phones", None))
        + _split_loose_values(metadata.get("all_phones"))
        + _split_loose_values(metadata.get("extra_phones"))
    )

    all_emails = _dedupe_values(
        [value for value in direct_emails + metadata_emails + _extract_emails_from_text(source_texts) if value],
        _normalize_email,
    )
    all_phones = _dedupe_values(
        [value for value in direct_phones + metadata_phones + _extract_phones_from_text(source_texts) if value],
        lambda item: re.sub(r"\D+", "", _normalize_phone(item)),
    )
    return all_emails, all_phones

def serialize_recruiter(r):
    all_emails, all_phones = _collect_all_contacts(r)
    return {
        "recruiter_id": r.recruiter_id,
        "recruiter_name": r.recruiter_name,
        "email": r.email,
        "phone": r.phone,
        "email2": r.email2,
        "phone2": r.phone2,
        "email3": r.email3,
        "phone3": r.phone3,
        "email4": r.email4,
        "phone4": r.phone4,
        "alternate_emails": getattr(r, "alternate_emails", None),
        "alternate_phones": getattr(r, "alternate_phones", None),
        "all_emails": all_emails,
        "all_phones": all_phones,
        "linkedin": r.linkedin,
        "specialization": r.specialization,
        "notes": r.notes,
        "metadata_json": r.__dict__.get("metadata_json"),
        "raw_data": r.__dict__.get("raw_data"),
        "company_id": r.company_id,
        "company_name": r.company.company_name if hasattr(r, "company") and r.company else None,
        "location": r.location if r.location else (r.company.location if hasattr(r, "company") and r.company else None),
        "state": r.state,
        "normalized_city": getattr(r, "normalized_city", None),
        "completeness_score": getattr(r, "completeness_score", 0),
        "needs_review": getattr(r, "needs_review", False),
        "review_reason": getattr(r, "review_reason", None),
        "location_confidence": getattr(r, "location_confidence", "high"),
        "state_source": getattr(r, "state_source", None),
        "state_confidence": getattr(r, "state_confidence", None),
        "state_reason": getattr(r, "state_reason", None),
        "email_status": getattr(r, "email_status", "unknown"),
        "email_confidence": getattr(r, "email_confidence", 0),
        "email_generated": getattr(r, "email_generated", False),
        "raw_email_value": getattr(r, "raw_email_value", None),
        "repair_reason": getattr(r, "repair_reason", None),
        "last_scan_at": str(r.last_scan_at) if getattr(r, "last_scan_at", None) else None,
        "is_active": r.is_active,
        "source_job_id": getattr(r, "source_job_id", None),
        "created_at": str(r.created_at) if getattr(r, "created_at", None) else None,
        "structured_emails": [{
            "id": e.id, "email": e.email, "email_type": e.email_type, "status": e.status, 
            "confidence_score": e.confidence_score, "is_primary": e.is_primary, "source": e.source
        } for e in getattr(r, "structured_emails", [])],
        "structured_phones": [{
            "id": p.id, "phone_number": p.phone_number, "phone_type": p.phone_type,
            "is_primary": p.is_primary, "belongs_to_person": p.belongs_to_person, "source": p.source
        } for p in getattr(r, "structured_phones", [])],
        "structured_locations": [{
            "id": l.id, "city": l.city, "state": l.state, "location_type": l.location_type,
            "is_fallback": l.is_fallback, "source": l.source
        } for l in getattr(r, "structured_locations", [])],
    }


def _update_state_metadata(r, db: Session) -> None:
    company = db.query(Company).filter(Company.company_id == r.company_id).first() if r.company_id else None
    state_result = infer_state_from_sources(
        [
            ("recruiter_location", r.location),
            ("company_state", company.state if company else None),
            ("company_location", company.location if company else None),
            ("notes", r.notes),
            ("review_reason", r.review_reason),
            ("metadata_json", r.metadata_json),
            ("raw_data", r.raw_data),
        ]
    )
    if state_result:
        r.state = state_result["state"]
        r.state_source = state_result["state_source"]
        r.state_confidence = state_result["state_confidence"]
        r.state_reason = state_result["state_reason"]
        if state_result.get("evidence"):
            meta = {}
            if r.metadata_json:
                try:
                    meta = json.loads(r.metadata_json) if isinstance(r.metadata_json, str) else dict(r.metadata_json)
                except Exception:
                    meta = {"raw_metadata": str(r.metadata_json)}
            meta["state_recovery"] = {
                "source": r.state_source,
                "confidence": r.state_confidence,
                "reason": r.state_reason,
                "evidence": state_result.get("evidence"),
            }
            r.metadata_json = json.dumps(meta, default=str)
        return

    r.state = None
    r.state_source = None
    r.state_confidence = None
    r.state_reason = None

def apply_recruiter_update(r, update_data: dict, db: Session):
    if "email" in update_data and update_data["email"] and update_data["email"] != r.email:
        existing = db.query(Recruiter).filter(Recruiter.email == update_data["email"],
            Recruiter.recruiter_id != r.recruiter_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    for phone_field in ("phone", "phone2", "phone3", "phone4"):
        if phone_field in update_data:
            update_data[phone_field] = format_us_phone(update_data[phone_field]) if update_data[phone_field] else None

    for key, value in update_data.items():
        setattr(r, key, value)

    if any(field in update_data for field in ("location", "company_id", "notes", "metadata_json", "raw_data", "review_reason")):
        _update_state_metadata(r, db)
    
    return r

from ..services.recruiter_store import recruiter_store

# --- Smart Ranked Search ---
@router.get("/search")
def search_recruiters(
    q: str = Query(..., min_length=1, description="Search query"),
    company: Optional[str] = Query(None, description="Filter by company"),
    location: Optional[str] = Query(None, description="Filter by location"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Smart weighted search using DuckDB Parquet store.
    """
    results = recruiter_store.search(
        q=q,
        company=company,
        location=location,
        specialization=specialization,
        limit=limit
    )
    
    from .analytics import infer_company_from_domain, DOMAIN_DISPLAY_NAMES, FREE_EMAIL_PROVIDERS

    # Batch fetch PostgreSQL metadata for numeric IDs
    comp_ids = []
    for r in results:
        val = r.get('company_id')
        if val is not None:
            try:
                num = float(val)
                if num.is_integer() and -2147483648 <= int(num) <= 2147483647:
                    comp_ids.append(int(num))
            except (TypeError, ValueError):
                pass
    
    companies_dict = {}
    if comp_ids:
        try:
            uncached = [cid for cid in comp_ids if not analytics_cache.get(f"comp_obj_{cid}")]
            if uncached:
                comps = db.query(Company).filter(Company.company_id.in_(uncached)).all()
                for c in comps:
                    analytics_cache.set(f"comp_obj_{c.company_id}", c, ttl=600)
            for cid in comp_ids:
                cached_comp = analytics_cache.get(f"comp_obj_{cid}")
                if cached_comp:
                    companies_dict[cid] = cached_comp
        except Exception:
            pass

    formatted = []
    for row in results:
        comp = companies_dict.get(row.get('company_id'))
        
        # 1. Infer domain from email or pg
        rec_domain = None
        email_val = row.get('email')
        if email_val and '@' in str(email_val):
            d = str(email_val).split('@')[-1].strip().lower()
            if d and d not in FREE_EMAIL_PROVIDERS:
                rec_domain = d
        
        # 1. Infer domain from email, pg, or recruiter_store company_overall
        raw_key = str(row.get('company_id')) if row.get('company_id') is not None else None
        store_domain = recruiter_store.get_company_domain(raw_key) if raw_key else None
        pg_logo = select_logo_domain(comp.website, comp.email_pattern) if comp else None
        company_domain = rec_domain or pg_logo or store_domain
        
        # 2. Resolve company name
        if company_domain and company_domain in DOMAIN_DISPLAY_NAMES:
            c_name = DOMAIN_DISPLAY_NAMES[company_domain]
        elif company_domain:
            c_name = infer_company_from_domain(company_domain)
        elif comp and comp.company_name:
            c_name = comp.company_name
        elif raw_key and not raw_key.isdigit():
            c_name = raw_key
        else:
            c_name = "Unknown Company" if raw_key and raw_key.isdigit() else (raw_key or "Unknown Company")

        logo_url = (f"https://www.google.com/s2/favicons?domain={company_domain}&sz=128" if company_domain else None)

        comp_data = {
            "company_id": comp.company_id if comp else row.get("company_id"),
            "company_name": c_name,
            "canonical_name": c_name,
            "primary_domain": company_domain,
            "logo_url": logo_url,
            "website": comp.website if comp else (f"https://{company_domain}" if company_domain else None),
            "email_pattern": company_domain,
            "location": comp.location if comp else row.get("location"),
            "state": comp.state if comp else row.get("state"),
        }

        formatted.append({
            "recruiter_id": row.get("recruiter_id"),
            "recruiter_name": row.get("recruiter_name"),
            "email": row.get("email"),
            "phone": row.get("phone"),
            "email2": row.get("email2"),
            "phone2": row.get("phone2"),
            "email3": row.get("email3"),
            "phone3": row.get("phone3"),
            "email4": row.get("email4"),
            "phone4": row.get("phone4"),
            "alternate_emails": row.get("alternate_emails"),
            "alternate_phones": row.get("alternate_phones"),
            "linkedin": row.get("linkedin"),
            "specialization": row.get("specialization"),
            "notes": row.get("notes"),
            "quality_score": row.get("quality_score"),
            "company_id": row.get("company_id"),
            "company_name": c_name,
            "company_domain": company_domain,
            "logo_url": logo_url,
            "company": comp_data,
            "location": row.get("location") or (comp.location if comp else None),
            "state": row.get("state"),
            "is_active": row.get("is_active", True),
            "needs_review": row.get("needs_review", False),
            "completeness_score": row.get("completeness_score", 0),
            "location_confidence": row.get("location_confidence"),
            "state_source": row.get("state_source"),
            "created_at": str(row.get("created_at")) if row.get("created_at") else None,
            "relevance_score": int(row.get("relevance_score", 0)),
            "seniority_level": row.get("seniority_level", "Specialist"),
            "timezone": row.get("timezone", "America/New_York"),
            "timezone_code": row.get("timezone_code", "ET"),
            "company_scale": row.get("company_scale", "Enterprise"),
            "is_deliverable": row.get("is_deliverable", True),
            "quality_tier": _search_quality_tier(row),
        })
    return formatted

from sqlalchemy.orm import load_only
from ..services.recruiter_store import METRO_HUBS

@router.get("/metro-hubs")
def get_metro_hubs(current_user: User = Depends(get_current_user_from_request)):
    """Return available metropolitan hiring clusters."""
    return [
        {"id": k, "name": v["name"], "states": v["states"], "top_cities": v["cities"][:4]}
        for k, v in METRO_HUBS.items()
    ]

@router.get("")
@router.get("/")
def get_recruiters(
    response: Response,
    page: int = 1,
    limit: int = Query(default=50, ge=1, le=100),
    search: Optional[str] = None,
    state: Optional[str] = None,
    state_status: Optional[str] = None,
    city: Optional[str] = None,
    company: Optional[str] = None,
    company_id: Optional[int] = None,
    company_key: Optional[str] = None,
    title: Optional[str] = None,
    specialization_sector: Optional[str] = None,
    seniority_level: Optional[str] = None,
    timezone_code: Optional[str] = None,
    company_scale: Optional[str] = None,
    metro_hub: Optional[str] = None,
    is_deliverable: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    missing_email: Optional[bool] = None,
    is_active: Optional[bool] = None,
    min_completeness: Optional[int] = None,
    needs_review: Optional[bool] = None,
    email_inference_status: Optional[str] = None,
    source_job_id: Optional[str] = None,
    data_source: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_desc: Optional[bool] = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    # Cache ALL recruiter list queries aggressively
    data_version = recruiter_store.data_version
    cache_key = f"rec_list_duckdb_{data_version}_{current_user.id}_{page}_{limit}_{search or ''}_{state or ''}_{metro_hub or ''}_{company_id or ''}_{company_key or ''}_{sort_by}_{sort_desc}_{needs_review}_{has_phone}_{is_active}_{is_deliverable}_{specialization_sector or ''}_{seniority_level or ''}_{timezone_code or ''}_{company_scale or ''}_{data_source or ''}"
    cached = analytics_cache.get(cache_key)
    if cached is not None:
        return cached

    # DuckDB handles all filtering, pagination, and sorting directly from Parquet
    results, total_count = recruiter_store.list_recruiters(
        page=page,
        limit=limit,
        search=search,
        state=state,
        metro_hub=metro_hub,
        company_id=company_id,
        company_key=company_key,
        company_name=company,
        specialization=title,
        specialization_sector=specialization_sector,
        seniority_level=seniority_level,
        timezone_code=timezone_code,
        company_scale=company_scale,
        is_deliverable=is_deliverable,
        has_phone=has_phone,
        is_active=is_active,
        needs_review=needs_review,
        email_status=email_inference_status,
        data_source=data_source,
        sort_by=sort_by,
        sort_desc=sort_desc
    )
    
    response.headers["X-Total-Count"] = str(total_count)
    
    import math
    total_pages = math.ceil(total_count / limit) if limit else 1
    
    # We need company details, so we'll fetch them from PostgreSQL for the results
    # Active Parquet imports can store company names in company_id. Only pass
    # actual integer IDs to PostgreSQL; string keys remain valid and are used
    # directly as the recruiter company name below.
    comp_ids = []
    for value in {r.get('company_id') for r in results if r.get('company_id') is not None}:
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                val_int = int(numeric_value)
                if -2147483648 <= val_int <= 2147483647:
                    comp_ids.append(val_int)
        except (TypeError, ValueError):
            continue
    companies_dict = {}
    if comp_ids:
        try:
            # Only query IDs not already cached
            uncached_ids = [cid for cid in comp_ids if not analytics_cache.get(f"comp_obj_{cid}")]
            if uncached_ids:
                companies = db.query(Company).filter(Company.company_id.in_(uncached_ids)).all()
                for c in companies:
                    analytics_cache.set(f"comp_obj_{c.company_id}", c, ttl=600)
            
            for cid in comp_ids:
                cached_comp = analytics_cache.get(f"comp_obj_{cid}")
                if cached_comp:
                    companies_dict[cid] = cached_comp
        except Exception as e:
            logger.warning(f"Failed to fetch company details for recruiters: {e}")
            try:
                db.rollback()
            except Exception:
                pass
    
    def _basic_company(company_row):
        return {
            "company_id": company_row.company_id,
            "company_name": company_row.company_name,
            "canonical_name": getattr(company_row, "canonical_name", None) or company_row.company_name,
            "location": company_row.location,
            "state": company_row.state,
            "website": company_row.website,
            "primary_domain": getattr(company_row, "primary_domain", None),
            "logo_url": getattr(company_row, "logo_url", None),
            "email_pattern": company_row.email_pattern
        } if company_row else None
    from .analytics import DOMAIN_DISPLAY_NAMES
    
    free_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net', 'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com', 'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'}
    
    formatted_results = []
    for r in results:
        comp = companies_dict.get(r.get('company_id'))
        
        pg_logo = select_logo_domain(comp.website, comp.email_pattern) if comp else None
        rec_domain = None
        email_val = r.get('email')
        if email_val and '@' in email_val:
            d = email_val.split('@')[-1].lower()
            if d not in free_domains:
                rec_domain = d
        
        raw_key = str(r.get('company_id')) if r.get('company_id') is not None else None
        store_domain = recruiter_store.get_company_domain(raw_key) if raw_key else None
        company_domain = rec_domain or pg_logo or store_domain

        if company_domain and company_domain in DOMAIN_DISPLAY_NAMES:
            c_name = DOMAIN_DISPLAY_NAMES[company_domain]
        elif comp and comp.company_name:
            c_name = comp.company_name
        elif company_domain:
            c_name = company_domain.split('.')[0].replace('-', ' ').title()
        elif raw_key and not raw_key.isdigit():
            c_name = raw_key
        else:
            c_name = "Unknown Company" if raw_key and raw_key.isdigit() else (raw_key or "Unknown Company")

        company_obj = _basic_company(comp)
        if not company_obj and (c_name or company_domain):
            company_obj = {
                "company_id": r.get('company_id'),
                "company_name": c_name,
                "canonical_name": c_name,
                "location": r.get('location'),
                "state": r.get('state'),
                "website": f"https://{company_domain}" if company_domain else None,
                "primary_domain": company_domain,
                "logo_url": r.get("logo_url") or (f"https://www.google.com/s2/favicons?domain={company_domain}&sz=128" if company_domain else None),
                "email_pattern": None
            }

        formatted_results.append({
            "recruiter_id": r.get("recruiter_id"),
            "recruiter_name": r.get("recruiter_name"),
            "email": r.get("email"),
            "phone": r.get("phone"),
            "email2": r.get("email2"),
            "phone2": r.get("phone2"),
            "email3": r.get("email3"),
            "phone3": r.get("phone3"),
            "email4": r.get("email4"),
            "phone4": r.get("phone4"),
            "alternate_emails": r.get("alternate_emails"),
            "alternate_phones": r.get("alternate_phones"),
            "linkedin": r.get("linkedin"),
            "specialization": r.get("specialization"),
            "notes": r.get("notes"),
            "company_id": r.get("company_id"),
            "company_name": c_name,
            "company_domain": company_domain,
            "logo_url": r.get("logo_url") or (comp.logo_url if comp else None) or (f"https://www.google.com/s2/favicons?domain={company_domain}&sz=128" if company_domain else None),
            "company": company_obj,
            "location": r.get("location") or (comp.location if comp else None),
            "state": r.get("state"),
            "normalized_city": r.get("normalized_city"),
            "completeness_score": r.get("completeness_score", 0),
            "quality_score": r.get("quality_score", 0),
            "trust_score": r.get("trust_score", 95),
            "seniority_level": r.get("seniority_level", "Specialist"),
            "timezone": r.get("timezone", "America/New_York"),
            "timezone_code": r.get("timezone_code", "ET"),
            "company_scale": r.get("company_scale", "Boutique"),
            "is_deliverable": bool(r.get("is_deliverable", True)),
            "deliverability_status": r.get("deliverability_status", "valid_mx"),
            "needs_review": r.get("needs_review", False),
            "review_reason": r.get("review_reason"),
            "location_confidence": r.get("location_confidence"),
            "company_confidence": r.get("company_confidence", 0),
            "company_reasoning": r.get("company_reasoning"),
            "email_status": r.get("email_status", "unknown"),
            "email_confidence": r.get("email_confidence", 0),
            "email_generated": r.get("email_generated", False),
            "raw_email_value": r.get("raw_email_value"),
            "repair_reason": r.get("repair_reason"),
            "state_source": r.get("state_source"),
            "state_confidence": r.get("state_confidence"),
            "state_reason": r.get("state_reason"),
            "last_scan_at": str(r.get("last_scan_at")) if r.get("last_scan_at") else None,
            "is_active": r.get("is_active", True),
            "data_source": r.get("data_source"),
            "source_job_id": r.get("source_job_id"),
            "created_at": str(r.get("created_at")) if r.get("created_at") else None,
            "structured_emails": [],
            "structured_phones": [],
            "structured_locations": [],
        })

    ret_data = {
        "total_count": total_count,
        "page": page,
        "total_pages": total_pages,
        "results": formatted_results
    }
    analytics_cache.set(cache_key, ret_data, ttl=300)
    return ret_data

import csv
from io import StringIO
from fastapi.responses import StreamingResponse

@router.get("/export")
def export_recruiters(
    search: Optional[str] = None,
    state: Optional[str] = None,
    state_status: Optional[str] = None,
    city: Optional[str] = None,
    company: Optional[str] = None,
    company_id: Optional[int] = None,
    title: Optional[str] = None,
    has_phone: Optional[bool] = None,
    missing_email: Optional[bool] = None,
    is_active: Optional[bool] = None,
    min_completeness: Optional[int] = None,
    needs_review: Optional[bool] = None,
    source_job_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    from sqlalchemy.orm import contains_eager
    query = db.query(Recruiter).join(Recruiter.company, isouter=True)\
              .filter()\
              .options(
                  contains_eager(Recruiter.company),
                  selectinload(Recruiter.structured_emails),
                  selectinload(Recruiter.structured_phones),
                  selectinload(Recruiter.structured_locations)
              )
    
    from ..utils.normalizer import normalize_text
    
    if search:
        clean_search = normalize_text(search)
        query = query.filter(
            Recruiter.normalized_recruiter_name.ilike(f"%{clean_search}%") |
            Recruiter.email.ilike(f"%{search}%") |
            Recruiter.specialization.ilike(f"%{search}%") |
            Company.normalized_company_name.ilike(f"%{clean_search}%") |
            Recruiter.location.ilike(f"%{search}%") |
            Company.location.ilike(f"%{search}%")
        )
    
    if state:
        query = apply_state_filter(query, state)
    if state_status:
        from sqlalchemy import or_, and_
        if state_status == 'known':
            query = query.filter(
                or_(
                    and_(Recruiter.state != None, Recruiter.state != ''),
                    and_(Company.state != None, Company.state != '')
                )
            )
        elif state_status == 'unknown':
            query = query.filter(
                or_(Recruiter.state == None, Recruiter.state == ''),
                or_(Company.state == None, Company.state == '')
            )
    if city:
        query = query.filter(Recruiter.normalized_city.ilike(f"%{city}%"))
    if company_id is not None:
        query = query.filter(Recruiter.company_id == company_id)
    elif company:
        query = apply_company_filter(query, company)
    if title:
        query = query.filter(Recruiter.specialization.ilike(f"%{title}%"))
    if has_phone is True:
        query = query.filter(Recruiter.phone.isnot(None), Recruiter.phone != "")
    elif has_phone is False:
        query = query.filter((Recruiter.phone.is_(None)) | (Recruiter.phone == ""))
    if missing_email is True:
        query = query.filter((Recruiter.email.is_(None)) | (Recruiter.email == ""))
    elif missing_email is False:
        query = query.filter(Recruiter.email.isnot(None), Recruiter.email != "")
    if is_active is not None:
        query = query.filter(Recruiter.is_active == is_active)
    if min_completeness is not None:
        query = query.filter(Recruiter.completeness_score >= min_completeness)
    if needs_review is not None:
        query = query.filter(Recruiter.needs_review == needs_review)
    if source_job_id:
        query = query.filter(Recruiter.source_job_id == source_job_id)

    # Prevent bandwidth explosion by limiting exports
    recruiters = query.limit(10000).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Email", "Company", "Phone Number", "Designation"
    ])
    
    for r in recruiters:
        # Resolve best email
        email_val = r.email or ""
        if not email_val and hasattr(r, 'structured_emails') and r.structured_emails:
            for e in r.structured_emails:
                if e.email:
                    email_val = e.email
                    break
                    
        # Resolve best phone
        phone_val = r.phone or ""
        if not phone_val and hasattr(r, 'structured_phones') and r.structured_phones:
            for p in r.structured_phones:
                if p.phone_number:
                    phone_val = p.phone_number
                    break

        # Resolve company
        company_val = (r.company.company_name if r.company else "") or getattr(r, 'company_name', '') or ""

        # Resolve designation
        designation_val = r.title or r.specialization or getattr(r, 'position', '') or ""

        writer.writerow([
            r.recruiter_name or "",
            email_val,
            company_val,
            phone_val,
            designation_val
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recruiters_export.csv"}
    )


@router.get("/{recruiter_id}")
def get_recruiter(recruiter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    return serialize_recruiter(r)

@router.post("/{recruiter_id}/email/approve")
def approve_email(recruiter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    
    # Approve means the email is verified
    r.email_status = "verified"
    r.email_confidence = 100
    r.repair_reason = "Manually approved by user"
    
    db.commit()
    
    sync_manager.request_sync()
    db.refresh(r)
    return serialize_recruiter(r)

@router.post("/{recruiter_id}/email/reject")
def reject_email(recruiter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    
    # Reject means revert to raw_email_value and set status to unknown or rejected
    if getattr(r, "raw_email_value", None):
        r.email = r.raw_email_value
    else:
        r.email = None
        
    r.email_status = "rejected"
    r.email_confidence = 0
    r.repair_reason = "Manually rejected by user"
    
    db.commit()
    
    sync_manager.request_sync()
    db.refresh(r)
    return serialize_recruiter(r)

@router.post("/", status_code=201)
def create_recruiter(data: RecruiterCreate, db: Session = Depends(get_db), admin: User = Depends(require_role(["superadmin", "admin"]))):
    current_user = admin
    existing = db.query(Recruiter).filter(Recruiter.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
        
    r_data = data.dict()
    for phone_field in ("phone", "phone2", "phone3", "phone4"):
        if r_data.get(phone_field):
            r_data[phone_field] = format_us_phone(r_data[phone_field])
    state = normalize_state(r_data.get('location'))
    state_source = "recruiter_location" if state else None
    state_confidence = "high" if state else None
    state_reason = None
    if not state and r_data.get('company_id'):
        company = db.query(Company).filter(Company.company_id == r_data['company_id']).first()
        if company and company.location:
            state, state_reason = extract_state_detailed(company.location)
            if state:
                state_source = "company_location"
                state_confidence = "high"
    if state and not state_reason and r_data.get('location'):
        _, state_reason = extract_state_detailed(r_data.get('location'))

    r = Recruiter(user_id=current_user.id, **r_data, state=state, state_source=state_source, state_confidence=state_confidence, state_reason=state_reason)
    db.add(r)
    db.commit()
    sync_manager.request_sync()
    db.refresh(r)
    return serialize_recruiter(r)

@router.put("/{recruiter_id}")
def update_recruiter(recruiter_id: int, data: RecruiterUpdate, db: Session = Depends(get_db), admin: User = Depends(require_role(["superadmin", "admin"]))):

    is_admin = admin.role and admin.role.name.lower() in ('admin', 'superadmin')
    if not is_admin:
        raise HTTPException(status_code=403, detail="Read-only access: Cannot modify global recruiter database")
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    update_data = data.dict(exclude_unset=True)
    apply_recruiter_update(r, update_data, db)
        
    db.commit()
        
    sync_manager.request_sync()
    db.refresh(r)
    return serialize_recruiter(r)

@router.delete("/{recruiter_id}")
def delete_recruiter(recruiter_id: int, db: Session = Depends(get_db), admin: User = Depends(require_role(["superadmin", "admin"]))):

    is_admin = admin.role and admin.role.name.lower() in ('admin', 'superadmin')
    if not is_admin:
        raise HTTPException(status_code=403, detail="Read-only access: Cannot modify global recruiter database")
    r = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    db.delete(r)
    db.commit()
    sync_manager.request_sync()
    return {"message": "Recruiter deleted"}

@router.post("/batch-delete")
def batch_delete_recruiters(payload: dict, db: Session = Depends(get_db), admin: User = Depends(require_role(["superadmin", "admin"]))):
    ids = [int(i) for i in payload.get("ids", []) if str(i).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No recruiter ids supplied")
    deleted = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    sync_manager.request_sync()
    return {"message": "Recruiters deleted", "deleted_count": deleted}

@router.post("/batch-update")
def batch_update_recruiters(payload: RecruiterBatchUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    ids = [int(i) for i in payload.ids if str(i).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No recruiter ids supplied")

    update_data = payload.dict(exclude_unset=True, exclude={"ids"})
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates supplied")

    recruiters = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(ids)).all()
    if not recruiters:
        raise HTTPException(status_code=404, detail="No recruiters found")

    updated = 0
    for recruiter in recruiters:
        apply_recruiter_update(recruiter, update_data, db)
        updated += 1
    db.commit()
    sync_manager.request_sync()
    return {"message": "Recruiters updated", "updated_count": updated}




@router.post("/{recruiter_id}/report")
def report_recruiter(recruiter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    from sqlalchemy import text
    try:
        res = db.execute(
            text("UPDATE recruiters SET report_count = report_count + 1 WHERE recruiter_id = :id RETURNING report_count"),
            {"id": recruiter_id}
        ).fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Recruiter not found")
        count = res[0]
        if count >= 3:
            db.execute(
                text("UPDATE recruiters SET needs_review = true, review_reason = 'Flagged by users 3 times', is_active = false WHERE recruiter_id = :id"),
                {"id": recruiter_id}
            )
        db.commit()
        sync_manager.request_sync()
        return {"message": "Report logged successfully", "report_count": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from ..services.scraper import auto_enhance_recruiter_data

@router.post("/{recruiter_id}/enhance")
def enhance_recruiter(recruiter_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    company_name = None
    company_domain = None
    if recruiter.company_id:
        company = db.query(Company).filter(Company.company_id == recruiter.company_id).first()
        if company:
            company_name = company.company_name
            if company.website:
                company_domain = company.website.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                
    result = auto_enhance_recruiter_data(recruiter.recruiter_name, company_name, company_domain)
    
    from ..services.scraper import is_human_name
    if is_human_name(recruiter.recruiter_name, company_name) and not result.get('email') and company_domain and recruiter.company_id and " " in recruiter.recruiter_name:
        first = recruiter.recruiter_name.split(' ')[0].lower()
        last = recruiter.recruiter_name.split(' ')[-1].lower()
        
        # 1. Use cached pattern if available
        if company and company.email_pattern:
            fmt = company.email_pattern
            if fmt == "{first}.{last}":
                result['email'] = f"{first}.{last}@{company_domain}"
            elif fmt == "{f}{last}":
                result['email'] = f"{first[0]}{last}@{company_domain}"
            elif fmt == "{first}{l}":
                result['email'] = f"{first}{last[0]}@{company_domain}"
            elif fmt == "{first}_{last}":
                result['email'] = f"{first}_{last}@{company_domain}"
            elif fmt == "{first}":
                result['email'] = f"{first}@{company_domain}"
            elif fmt == "{last}":
                result['email'] = f"{last}@{company_domain}"
        else:
            # 2. Derive pattern from peers if not cached
            peers = db.query(Recruiter).filter(Recruiter.company_id == recruiter.company_id,
                Recruiter.email.notlike('%@missing.local'),
                Recruiter.email.notlike('%@talentops.ai'),
                Recruiter.email != None,
                Recruiter.recruiter_name.like('% %')
            ).limit(10).all()
            
            for peer in peers:
                parts = peer.recruiter_name.split(' ')
                if len(parts) >= 2:
                    p_first = parts[0].lower()
                    p_last = parts[-1].lower()
                    e_local = peer.email.split('@')[0].lower()
                    
                    format_found = None
                    if e_local == f"{p_first}.{p_last}":
                        format_found = "{first}.{last}"
                        result['email'] = f"{first}.{last}@{company_domain}"
                    elif e_local == f"{p_first[0]}{p_last}":
                        format_found = "{f}{last}"
                        result['email'] = f"{first[0]}{last}@{company_domain}"
                    elif e_local == f"{p_first}{p_last[0]}":
                        format_found = "{first}{l}"
                        result['email'] = f"{first}{last[0]}@{company_domain}"
                    elif e_local == f"{p_first}_{p_last}":
                        format_found = "{first}_{last}"
                        result['email'] = f"{first}_{last}@{company_domain}"
                    elif e_local == f"{p_first}":
                        format_found = "{first}"
                        result['email'] = f"{first}@{company_domain}"
                    elif e_local == f"{p_last}":
                        format_found = "{last}"
                        result['email'] = f"{last}@{company_domain}"
                    
                    if format_found and company:
                        company.email_pattern = format_found
                        break

    updated = []
    if result.get('email') and (not recruiter.email or recruiter.email.endswith('@missing.local')):
        recruiter.email = result['email']
        updated.append("email")
    if result.get('phone') and not recruiter.phone:
        recruiter.phone = result['phone']
        updated.append("phone")
    if result.get('location'):
        state_abbr = result['location']
        if not recruiter.location or not recruiter.state:
            from ..utils.state_mapper import ABBR_TO_NAME
            full_state = ABBR_TO_NAME.get(state_abbr, state_abbr)
            recruiter.location = full_state
            recruiter.state = state_abbr
            recruiter.state_source = "ddg_enhancement"
            recruiter.state_confidence = "medium"
            updated.append("location")
        
    if updated:
        from sqlalchemy.sql import func
        recruiter.last_scan_at = func.now()
        db.commit()
        sync_manager.request_sync()
        return {"message": f"Successfully enhanced {', '.join(updated)}!", "data": result}
    else:
        # Update last_scan_at using raw SQL to prevent SQLAlchemy onupdate trigger from modifying updated_at
        from sqlalchemy import text
        db.execute(
            text("UPDATE recruiters SET last_scan_at = NOW() WHERE recruiter_id = :rid"),
            {"rid": recruiter.recruiter_id}
        )
        db.commit()
        sync_manager.request_sync()
        return {"message": "No new verified data found.", "data": result}

from pydantic import BaseModel
class ChromeExtensionPayload(BaseModel):
    recruiter_name: str
    title: str | None = None
    location: str | None = None
    company_name: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    scraped_at: str | None = None
    tags: list[str] | None = None

import uuid
import json
from ..utils.state_mapper import extract_state_detailed
from ..utils.normalizer import normalize_text
from ..utils.location_validator import is_location_north_america

@router.post("/extension", status_code=201)
def extension_webhook(data: ChromeExtensionPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Check location filter
    if data.location and not is_location_north_america(data.location):
        return {"message": "Ignored - location outside North America", "saved": False}

    # 1. Resolve Company
    company_id = None
    if data.company_name:
        norm_comp = normalize_text(data.company_name)
        company = db.query(Company).filter(Company.normalized_company_name == norm_comp).first()
        if company:
            company_id = company.company_id
        else:
            new_comp = Company(
                company_name=data.company_name,
                normalized_company_name=norm_comp,
                is_active=True,
                data_source="chrome_extension"
            )
            db.add(new_comp)
            db.commit()
            sync_manager.request_sync()
            db.refresh(new_comp)
            company_id = new_comp.company_id
            
    # 2. Extract state from location if available
    state = None
    state_source = None
    state_confidence = None
    state_reason = None
    if data.location:
        state, state_reason = extract_state_detailed(data.location)
        if state:
            state_source = "extension_location"
            state_confidence = "high"

    # 3. Create placeholder email
    email = f"linkedin_{uuid.uuid4().hex[:8]}@missing.local"

    # 4. Create Recruiter
    new_rec = Recruiter(user_id=current_user.id, 
        recruiter_name=data.recruiter_name[:150] if data.recruiter_name else "",
        normalized_recruiter_name=normalize_text(data.recruiter_name)[:150] if data.recruiter_name else "",
        email=email[:150] if email else "",
        title=data.title[:150] if data.title else None,
        company_id=company_id,
        location=data.location[:255] if data.location else None,
        state=state[:2] if state else None,
        state_source=state_source[:150] if state_source else None,
        state_confidence=state_confidence[:50] if state_confidence else None,
        state_reason=state_reason,
        linkedin=data.linkedin_url[:255] if data.linkedin_url else None,
        data_source=(data.source or "chrome_extension")[:100],
        tags=data.tags,
        is_active=True
    )
    db.add(new_rec)
    db.commit()
    sync_manager.request_sync()
    db.refresh(new_rec)
    
    return {
        "status": "success",
        "recruiter_id": new_rec.recruiter_id,
        "message": "Candidate clipped from LinkedIn successfully"
    }


@router.post("/{recruiter_id}/auto-fix-email")
def api_auto_fix_recruiter_email(
    recruiter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Autonomously heals, typo-fixes, or synthesizes a valid corporate email for a recruiter."""
    from ..services.email_healer import email_healer

    result = email_healer.repair_recruiter_email(recruiter_id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('message', 'Failed to heal email'))

    # Update in Postgres if row exists
    pg_rec = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    return result


class ExportRecruitersPayload(BaseModel):
    recruiter_ids: Optional[List[int]] = None
    search: Optional[str] = None
    state: Optional[str] = None
    company_key: Optional[str] = None
    specialization: Optional[str] = None
    has_phone: Optional[bool] = None
    limit: Optional[int] = 10000


@router.get("/{recruiter_id}/colleagues")
def get_recruiter_colleagues(
    recruiter_id: int,
    limit: int = 15,
    current_user: User = Depends(get_current_user_from_request)
):
    """Retrieve peer recruiters at the same company for Colleague Graph."""
    rec = recruiter_store.get_by_id(recruiter_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recruiter not found")
        
    company_key = rec.get("company_id")
    if not company_key:
        return {"colleagues": [], "company": None}
        
    from app.services.enrichment_service import get_company_colleagues
    colleagues = get_company_colleagues(company_key=company_key, exclude_id=recruiter_id, limit=limit)
    return {
        "company": company_key,
        "total_colleagues": len(colleagues),
        "colleagues": colleagues
    }


@router.post("/export")
def export_recruiters_endpoint(
    payload: ExportRecruitersPayload,
    current_user: User = Depends(get_current_user_from_request)
):
    """Stream matching recruiters directly as downloadable CSV."""
    csv_content = recruiter_store.export_recruiters_csv(
        search=payload.search,
        state=payload.state,
        company_key=payload.company_key,
        specialization=payload.specialization,
        has_phone=payload.has_phone,
        recruiter_ids=payload.recruiter_ids,
        limit=min(payload.limit or 10000, 50000)
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=talentops_recruiters_export.csv",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

