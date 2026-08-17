from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional, Dict, Any, List
import logging
import time
import asyncio
import functools
import pandas as pd

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, func, String
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.auth_service import get_current_user_from_request
from ..services.recruiter_store import recruiter_store
from ..models.auth_models import User
from ..models.models import Company, PageVisit, Recruiter, Vendor
from ..utils.logo_domains import select_logo_domain
from ..utils.state_sql import EFFECTIVE_RECRUITER_STATE_SQL_R, UNKNOWN_STATE_SENTINEL


class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._lock = Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                del self._cache[key]
            return None

    def set(self, key, value, ttl=30):
        with self._lock:
            self._cache[key] = (value, time.time() + ttl)

    def invalidate(self, key):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

analytics_cache = SimpleCache()
# Cache to hold expensive analytical queries

import functools

def cached_endpoint(ttl_seconds=30):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and its arguments
            key_parts = [func.__name__]
            # Add kwargs stringified (excluding Db sessions which are unhashable)
            for k, v in sorted(kwargs.items()):
                if k != 'db':
                    if hasattr(v, 'id') and k == 'current_user':
                        key_parts.append(f"{k}={v.id}")
                    else:
                        key_parts.append(f"{k}={v}")
            cache_key = ":".join(key_parts)
            
            cached = analytics_cache.get(cache_key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            analytics_cache.set(cache_key, result, ttl=ttl_seconds)
            return result
        return wrapper
    return decorator

logger = logging.getLogger("talentops.analytics")
# Maps common recruiter email domains to proper display names for companies
# that may not have PostgreSQL records on production.
DOMAIN_DISPLAY_NAMES = {
    'roberthalf.com': 'Robert Half',
    'insightglobal.com': 'Insight Global',
    'teksystems.com': 'TEKsystems',
    'randstadusa.com': 'Randstad',
    'randstaddigital.com': 'Randstad Digital',
    'beaconhillstaffing.com': 'Beacon Hill Staffing Group',
    'kforce.com': 'Kforce',
    'brooksource.com': 'Brooksource',
    'aerotek.com': 'Aerotek',
    'kornferry.com': 'Korn Ferry',
    'apexsystems.com': 'Apex Systems',
    'oxfordcorp.com': 'Oxford Global Resources',
    'inspyrsolutions.com': 'INSPYR Solutions',
    'kellyservices.com': 'Kelly Services',
    'cybercoders.com': 'CyberCoders',
    'actalentsservices.com': 'Actalent Services',
    'judge.com': 'The Judge Group',
    'vaco.com': 'Vaco',
    'manpower.com': 'Manpower',
    'manpowergroup.com': 'ManpowerGroup',
    'experis.com': 'Experis',
    'hays.com': 'Hays',
    'adeccousa.com': 'Adecco',
    'modis.com': 'Modis',
    'akkodis.com': 'Akkodis',
    'accenture.com': 'Accenture',
    'deloitte.com': 'Deloitte',
    'cognizant.com': 'Cognizant',
    'infosys.com': 'Infosys',
    'wipro.com': 'Wipro',
    'collabera.com': 'Collabera',
    'eliassen.com': 'Eliassen Group',
    'addisongroup.com': 'Addison Group',
    'astoncarter.com': 'Aston Carter',
    'allegisgroup.com': 'Allegis Group',
    'russelltobin.com': 'Russell Tobin',
    'kellymitchell.com': 'KellyMitchell',
    'heidrick.com': 'Heidrick & Struggles',
    'spencerstuart.com': 'Spencer Stuart',
    'russellreynolds.com': 'Russell Reynolds',
    'stand8.io': 'Stand 8',
    'bhsg.com': 'BHSG',
    'bluestonestaffing.com': 'Bluestone Staffing',
    'bluestonesg.com': 'Bluestone SG',
    'mribluestone.com': 'MRI Bluestone',
    'bluestone-llc.com': 'Bluestone LLC',
    'motionrecruitment.com': 'Motion Recruitment',
    'signatureconsultants.com': 'Signature Consultants',
}

FREE_EMAIL_PROVIDERS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com',
    'live.com', 'msn.com', 'comcast.net', 'att.net', 'sbcglobal.net', 'verizon.net',
    'me.com', 'mail.com', 'protonmail.com', 'ymail.com', 'cox.net', 'charter.net',
    'earthlink.net', 'talentops.ai'
}

def infer_company_from_domain(domain: Optional[str]) -> Optional[str]:
    if not domain or not isinstance(domain, str):
        return None
    d = domain.strip().lower()
    if not d or d in FREE_EMAIL_PROVIDERS:
        return None
    if d in DOMAIN_DISPLAY_NAMES:
        return DOMAIN_DISPLAY_NAMES[d]
    
    # Strip common TLDs
    base = re.sub(r"\.(com|net|org|io|co|ai|us|ca|tech|info|biz|global|llc)$", "", d)
    # Split on hyphens, underscores, dots
    words = re.split(r"[-_.]+", base)
    clean_words = []
    for w in words:
        if not w:
            continue
        if w.lower() in {"sg", "it", "llc", "inc", "corp", "hr", "ai", "us", "uk", "ca"}:
            clean_words.append(w.upper())
        else:
            clean_words.append(w.capitalize())
    return " ".join(clean_words) if clean_words else None

router = APIRouter()

@router.get("")
@router.get("/")
def get_analytics_root():
    return {"status": "Analytics engine active"}

@router.get("/data-quality")
@cached_endpoint(ttl_seconds=300)
def get_data_quality(current_user: User = Depends(get_current_user_from_request)):
    from ..olap_sidecar import olap_sidecar
    return olap_sidecar.get_data_quality(user_id=current_user.id)


@router.get("/dashboard")
@cached_endpoint(ttl_seconds=300)
def get_dashboard_kpis(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):

    is_admin = current_user.role and current_user.role.name.lower() in ('admin', 'superadmin')
    
    # Force reload from disk to pick up any new Parquet data from bulk imports
    recruiter_store.reload()
    duck_conn = recruiter_store._conn
    
    sql = """
        SELECT 
            COUNT(*) as total_recruiters,
            COUNT(*) FILTER (WHERE is_active = true) as active_recruiters,
            COUNT(*) FILTER (WHERE needs_review = true) as needs_review,
            COUNT(*) FILTER (WHERE completeness_score < 50) as low_quality,
            COUNT(*) FILTER (WHERE 
                (email IS NOT NULL AND email != '') OR 
                (email2 IS NOT NULL AND email2 != '') OR 
                (email3 IS NOT NULL AND email3 != '') OR 
                (email4 IS NOT NULL AND email4 != '')
            ) as with_email,
            COUNT(*) FILTER (WHERE 
                (phone IS NOT NULL AND phone != '') OR 
                (phone2 IS NOT NULL AND phone2 != '') OR 
                (phone3 IS NOT NULL AND phone3 != '') OR 
                (phone4 IS NOT NULL AND phone4 != '')
            ) as with_phone
        FROM recruiters
    """
    if duck_conn:
        res = duck_conn.execute(sql).fetchone()
        total_recruiters = res[0] or 0
        active_recruiters = res[1] or 0
        needs_review = res[2] or 0
        low_quality = res[3] or 0
        with_email = res[4] or 0
        with_phone = res[5] or 0
    else:
        # Fallback if DuckDB fails for some reason
        res = db.execute(text(sql)).mappings().first()
        total_recruiters = res["total_recruiters"] or 0
        active_recruiters = res["active_recruiters"] or 0
        needs_review = res["needs_review"] or 0
        low_quality = res["low_quality"] or 0
        with_email = res["with_email"] or 0
        with_phone = res["with_phone"] or 0

    total_companies = db.query(Company).count()
    total_vendors = db.query(Vendor).count()

    email_rate = round((with_email / total_recruiters * 100), 1) if total_recruiters > 0 else 0
    review_rate = round((needs_review / total_recruiters * 100), 1) if total_recruiters > 0 else 0

    result = {
        "recruiters": {
            "total": total_recruiters,
            "active": active_recruiters,
            "inactive": total_recruiters - active_recruiters,
            "needs_review": needs_review,
            "low_quality": low_quality,
            "with_email": with_email,
            "with_phone": with_phone,
            "email_coverage_percent": email_rate,
            "needs_review_percent": review_rate,
        },
        "companies": {"total": total_companies},
        "vendors": {"total": total_vendors},
    }
    return result


@router.get("/recruiters-by-state")
@cached_endpoint(ttl_seconds=3600)
def recruiters_by_state(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Use DuckDB Parquet store (2.1M full dataset) instead of PostgreSQL (128K subset)
    try:
        recruiter_store._ensure_loaded()
        duck_conn = recruiter_store._conn
        if duck_conn:
            results = duck_conn.execute("""
                SELECT
                    state,
                    COUNT(*) AS count
                FROM recruiters
                WHERE state IS NOT NULL AND state != '' AND state != 'US'
                GROUP BY state
                ORDER BY count DESC, state ASC
            """).fetchall()
            return [{"state": row[0], "count": int(row[1])} for row in results]
    except Exception as e:
        logger.warning(f"DuckDB recruiters-by-state failed, falling back to PostgreSQL: {e}")

    # Fallback to PostgreSQL
    computed_state_sql = EFFECTIVE_RECRUITER_STATE_SQL_R
    is_admin = current_user.role and current_user.role.name.lower() == 'admin'
    where_clause = "1=1"

    results = db.execute(text(f"""
        SELECT
            {computed_state_sql} AS state,
            COUNT(r.recruiter_id) AS count
        FROM recruiters r 
        LEFT JOIN companies c ON c.company_id = r.company_id
        WHERE {where_clause} AND {computed_state_sql} IS NOT NULL
        GROUP BY {computed_state_sql}
        ORDER BY count DESC, state ASC
    """)).mappings().all()

    res_list = [{"state": row["state"], "count": int(row["count"])} for row in results]
    return res_list


@router.get("/companies-count-by-state")
def companies_count_by_state(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    cached = analytics_cache.get("companies_count_by_state")
    if cached is not None:
        return cached

    rows = db.execute(text("""
        SELECT
            COALESCE(
                NULLIF(TRIM(c.state), ''),
                NULLIF(TRIM(r.state), ''),
                'Unknown'
            ) AS state,
            COUNT(DISTINCT c.company_id) AS count
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        WHERE 1=1
        GROUP BY 1
        ORDER BY count DESC
    """)).mappings().all()

    counts = {"user_id": current_user.id}
    for row in rows:
        state = row["state"] or "Unknown"
        counts[state] = int(row["count"])

    analytics_cache.set("companies_count_by_state", counts, ttl=3600)
    return counts


@router.get("/company-states")
def company_states(
    company_id: Optional[int] = Query(None, ge=1),
    company_key: Optional[str] = Query(None, min_length=1),
    db: Session = Depends(get_db),
):
    data_version = recruiter_store.data_version
    selected_key = company_key or (str(company_id) if company_id is not None else None)
    cache_key = f"company_states_{data_version}_{selected_key or 'all'}"
    cached = analytics_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        recruiter_store._ensure_loaded()
        duck_conn = recruiter_store._conn
        if duck_conn:
            where_clause = "WHERE CAST(company_id AS VARCHAR) = ?" if selected_key else "WHERE 1=1"
            params = [selected_key] if selected_key else []
            
            rows = duck_conn.execute(f"""
                SELECT state, COUNT(*) as count
                FROM recruiters
                {where_clause} AND state IS NOT NULL AND state != ''
                GROUP BY state
                ORDER BY count DESC, state ASC
            """, params).fetchall()
            
            unknown_row = duck_conn.execute(f"""
                SELECT COUNT(*) as count
                FROM recruiters
                {where_clause} AND (state IS NULL OR state = '')
            """, params).fetchone()
            
            result = [{"state": row[0], "count": int(row[1])} for row in rows]
            unknown_count = int(unknown_row[0]) if unknown_row and unknown_row[0] else 0
            if unknown_count > 0:
                result.append({"state": UNKNOWN_STATE_SENTINEL, "count": unknown_count})
                
            analytics_cache.set(cache_key, result, ttl=60)
            return result
    except Exception as e:
        logger.warning(f"DuckDB company-states failed: {e}")
        
    return []


@router.get("/companies-search")
def companies_search(
    response: Response,
    q: Optional[str] = Query(None, description="Search company name"),
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    min_recruiters: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
):
    # Counts and company keys live in the active Parquet dataset. Include its
    # version in the cache key so Directory never mixes old company metadata
    # with the current recruiter file.
    data_version = recruiter_store.data_version
    cache_key = f"companies_search_{data_version}_{current_user.id}_{q or ''}_{state or ''}_{min_recruiters}_{limit}_{skip}"
    cached = analytics_cache.get(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached["total_count"])
        return cached["rows"]

    matched_keys = []
    if q and q.strip():
        try:
            pattern = f"%{q.strip()}%"
            matching_pg = db.query(Company.company_id).filter(Company.company_name.ilike(pattern)).all()
            matched_keys = [str(r[0]) for r in matching_pg]
        except Exception:
            pass

    active_companies = recruiter_store.company_directory(q, state, matched_keys=matched_keys)
    if min_recruiters > 0:
        active_companies = [row for row in active_companies if row['recruiter_count'] >= min_recruiters]

    total_count = len(active_companies)
    paginated_companies = active_companies[skip:skip+limit]

    # Numeric values can retain database metadata. Name-based keys are still
    # valid companies in the active data and must remain discoverable.
    numeric_ids = []
    for row in paginated_companies:
        try:
            value = float(row['company_key'])
            if value.is_integer():
                val_int = int(value)
                # Filter out values that exceed PostgreSQL 32-bit integer limits
                if -2147483648 <= val_int <= 2147483647:
                    numeric_ids.append(val_int)
        except ValueError:
            pass
            
    metadata = {}
    if numeric_ids:
        try:
            for company in db.query(Company).filter(Company.company_id.in_(numeric_ids)).all():
                metadata[str(company.company_id)] = company
        except Exception as e:
            logger.warning(f"Failed to fetch PostgreSQL metadata for companies: {e}")
            try:
                db.rollback()
            except Exception:
                pass

    enriched_results = []
    for row in paginated_companies:
        key = row['company_key']
        parquet_domain = row.get('dominant_domain')  # Most common email domain from Parquet
        normalized_numeric_key = None
        try:
            numeric_value = float(key)
            if numeric_value.is_integer():
                normalized_numeric_key = str(int(numeric_value))
        except ValueError:
            pass
        company = metadata.get(normalized_numeric_key)

        # --- Resolve logo_domain: prefer Parquet (ground truth from emails) ---
        pg_logo = select_logo_domain(company.website, company.email_pattern) if company else None
        logo_domain = parquet_domain or pg_logo

        # --- Resolve company name ---
        if parquet_domain and parquet_domain in DOMAIN_DISPLAY_NAMES:
            name = DOMAIN_DISPLAY_NAMES[parquet_domain]
        elif company and company.company_name:
            name = company.company_name
        elif parquet_domain:
            name = parquet_domain.split('.')[0].replace('-', ' ').title()
        else:
            name = f"Unknown Company" if key.isdigit() else key

        # --- Resolve email_pattern: prefer Parquet domain ---
        email_pattern = parquet_domain or (company.email_pattern if company else None)

        enriched_results.append({
            "company_key": key,
            "company_id": company.company_id if company else None,
            "company_name": name,
            "location": company.location if company else None,
            "industry": company.industry if company else None,
            "website": company.website if company else None,
            "email_pattern": email_pattern,
            "linkedin_url": company.linkedin_url if company else None,
            "notes": company.notes if company else None,
            "tags": company.tags if company else None,
            "state_abbr": company.state if company and company.state else "US",
            "sim_score": 0,
            "missing_state_count": 0,
            "needs_review_count": 0,
            "recruiter_count": row['recruiter_count'],
            "logo_domain": logo_domain,
            "full_count": total_count,
        })
    
    final_result = {"total_count": total_count, "rows": enriched_results}
    analytics_cache.set(cache_key, final_result, ttl=60)
    response.headers["X-Total-Count"] = str(total_count)
    return enriched_results

class VisitPayload(BaseModel):
    page: str
    path: str
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    time_on_page: Optional[int] = None


@router.post("/log-visit")
def log_visit(payload: VisitPayload, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    ua = request.headers.get("user-agent", "")[:300]
    forwarded = request.headers.get("x-forwarded-for")
    ip = (forwarded.split(",")[0].strip() if forwarded else None) or str(request.client.host)

    visit = PageVisit(
        page=payload.page,
        path=payload.path,
        user_email=payload.user_email,
        session_id=payload.session_id,
        time_on_page=payload.time_on_page,
        user_agent=ua,
        ip_address=ip,
    )
    db.add(visit)
    
    from ..utils.visitor_tracking import upsert_visitor_session
    upsert_visitor_session(
        db=db,
        session_id=payload.session_id,
        ip_address=ip,
        user_agent_str=ua,
        user_email=payload.user_email,
        is_page_view=True,
        time_on_page=payload.time_on_page
    )
    
    db.commit()
    analytics_cache.invalidate("visit_stats")
    return {"ok": True}


@router.get("/visit-stats")
def visit_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    cached = analytics_cache.get(f"visit_stats_{current_user.id}")
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    daily = db.execute(text("""
        SELECT DATE(visited_at) AS day, COUNT(*) AS visits
        FROM page_visits
        WHERE user_email = :user_email AND visited_at >= :since
        GROUP BY day ORDER BY day ASC
    """), {"since": seven_days_ago, "user_email": current_user.email}).mappings().all()

    thirty_days_ago = now - timedelta(days=30)
    
    # Conditional SQL for week truncation based on DB type
    import os
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or ""
    is_sqlite = not db_url.startswith("postgresql")

    if is_sqlite:
        week_sql = "strftime('%Y-%m-%d', visited_at, 'weekday 0', '-6 days') AS week_start"
    else:
        week_sql = "DATE_TRUNC('week', visited_at)::date AS week_start"

    weekly = db.execute(text(f"""
        SELECT
            {week_sql},
            COUNT(*) AS visits
        FROM page_visits
        WHERE user_email = :user_email AND visited_at >= :since
        GROUP BY week_start ORDER BY week_start ASC
    """), {"since": thirty_days_ago, "user_email": current_user.email}).mappings().all()

    top_pages = db.execute(text("""
        SELECT page, COUNT(*) AS visits
        FROM page_visits
        WHERE user_email = :user_email
        GROUP BY page ORDER BY visits DESC
        LIMIT 10
    """), {"user_email": current_user.email}).mappings().all()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    today_count = db.execute(text("SELECT COUNT(*) FROM page_visits WHERE user_email = :user_email AND visited_at >= :s"), {"s": today_start, "user_email": current_user.email}).scalar() or 0
    yesterday_count = db.execute(
        text("SELECT COUNT(*) FROM page_visits WHERE user_email = :user_email AND visited_at >= :s AND visited_at < :e"),
        {"s": yesterday_start, "e": today_start, "user_email": current_user.email},
    ).scalar() or 0
    total_count = db.execute(text("SELECT COUNT(*) FROM page_visits WHERE user_email = :user_email"), {"user_email": current_user.email}).scalar() or 0

    searches_today = db.execute(
        text("SELECT COUNT(*) FROM action_logs WHERE user_email = :user_email AND created_at >= :s AND action_type = 'SEARCH_RECRUITERS'"),
        {"s": today_start, "user_email": current_user.email}
    ).scalar() or 0

    result = {
        "total_visits": total_count,
        "today": today_count,
        "yesterday": yesterday_count,
        "searches_today": searches_today,
        "daily": [{"day": str(r["day"]), "visits": r["visits"]} for r in daily],
        "weekly": [{"week": str(r["week_start"]), "visits": r["visits"]} for r in weekly],
        "top_pages": [{"page": r["page"], "visits": r["visits"]} for r in top_pages],
    }
    analytics_cache.set(f"visit_stats_{current_user.id}", result, ttl=3600)
    return result

@router.get("/enrichment-feed")
@cached_endpoint(ttl_seconds=30)
def get_enrichment_feed(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    try:
        discovered = db.execute(text("""
            SELECT r.recruiter_name, r.title, r.created_at, 'discovery' as type,
                   c.company_name, r.email, r.phone, r.location
            FROM recruiters r
            JOIN companies c ON r.company_id = c.company_id
            WHERE (r.user_id = :user_id OR r.user_id IS NULL) AND r.data_source = 'discovery_worker'
            AND r.company_id IS NOT NULL
            ORDER BY r.created_at DESC 
            LIMIT 50
        """), {"user_id": current_user.id}).fetchall()
        
        enriched = db.execute(text("""
            SELECT r.recruiter_name, r.title, r.updated_at as created_at, 'enriched' as type,
                   c.company_name, r.email, r.phone, r.location
            FROM recruiters r
            JOIN companies c ON r.company_id = c.company_id
            WHERE (r.user_id = :user_id OR r.user_id IS NULL)
            AND (r.phone IS NOT NULL OR r.email IS NOT NULL) 
            AND r.company_id IS NOT NULL
            AND r.updated_at > r.created_at
            ORDER BY r.updated_at DESC 
            LIMIT 50
        """), {"user_id": current_user.id}).fetchall()
        
        import re
        
        def smart_parse_name(raw_name, existing_phone):
            raw_name = str(raw_name).strip()
            # If it's mostly numbers/symbols, it's a phone number
            if re.match(r'^[\d\s\(\)\-\+\.]+$', raw_name) and len(raw_name) >= 7:
                return "Unknown Contact", raw_name
            return raw_name, existing_phone

        feed = []
        for row in discovered:
            ts = row[2].isoformat() if row[2] else None
            if ts and not ts.endswith('Z') and '+' not in ts: ts += 'Z'
            
            real_name, smart_phone = smart_parse_name(row[0], row[6])
            
            feed.append({
                "id": f"disc_{hash(str(row[0]) + str(row[2]))}",
                "name": real_name,
                "title": row[1] or "Talent Acquisition",
                "timestamp": ts,
                "type": row[3],
                "company": row[4] or "Unknown Company",
                "email": row[5] or "",
                "phone": smart_phone or "",
                "location": row[7] or "",
                "message": f"AI Discovered: {real_name}"
            })
            
        for row in enriched:
            ts = row[2].isoformat() if row[2] else None
            if ts and not ts.endswith('Z') and '+' not in ts: ts += 'Z'
            
            real_name, smart_phone = smart_parse_name(row[0], row[6])
            
            feed.append({
                "id": f"enr_{hash(str(row[0]) + str(row[2]))}",
                "name": real_name,
                "title": row[1] or "Talent Acquisition",
                "timestamp": ts,
                "type": row[3],
                "company": row[4] or "Unknown Company",
                "email": row[5] or "",
                "phone": smart_phone or "",
                "location": row[7] or "",
                "message": f"Profile Enriched: {real_name}"
            })
            
        feed.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return {"feed": feed[:50]}
    except Exception as e:
        return {"feed": []}

@router.get("/global-activity")
@cached_endpoint(ttl_seconds=30)
def get_global_activity(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    try:
        # Fetch the most recently updated high-quality records
        records = db.execute(text("""
            SELECT r.recruiter_id, r.recruiter_name, r.title, r.location, r.phone, r.email, 
                   r.created_at, r.updated_at, r.is_active, c.company_name
        FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        WHERE r.user_id = :user_id AND r.recruiter_name IS NOT NULL AND r.recruiter_name != ''
              AND c.company_name IS NOT NULL AND c.company_name != ''
              AND r.email IS NOT NULL AND r.email != '' AND r.email NOT LIKE '%@missing.local' AND r.email NOT LIKE 'no-email-%' AND r.email NOT LIKE 'linkedin_%'
              AND r.location IS NOT NULL AND r.location != ''
            ORDER BY r.updated_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        feed = []
        for row in records:
            created = row[6]
            updated = row[7]
            is_active = row[8]
            has_contact = bool(row[4]) or bool(row[5])
            
            # Determine category
            category = "unknown"
            if is_active is False:
                category = "removed"
            elif created and updated and (updated - created).total_seconds() < 60:
                # Created within the last minute of its update = brand new addition
                category = "added"
            elif has_contact:
                category = "improved"
            else:
                category = "needs_improvement"
                
            ts = updated.isoformat() if updated else None
            if ts and not ts.endswith('Z') and '+' not in ts: ts += 'Z'
            
            feed.append({
                "id": row[0],
                "name": row[1] or "Unknown",
                "title": row[2] or "",
                "location": row[3] or "",
                "phone": row[4] or "",
                "email": row[5] or "",
                "company": row[9] or "Unknown Company",
                "timestamp": ts,
                "category": category
            })
            
        daily_stats_row = db.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE user_id = :user_id AND created_at >= CURRENT_DATE) as added,
                COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE AND (phone IS NOT NULL OR email IS NOT NULL) AND created_at < CURRENT_DATE AND is_active = true) as improved,
                COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE AND is_active = false) as removed
            FROM recruiters
            WHERE updated_at >= CURRENT_DATE OR created_at >= CURRENT_DATE
        """), {"user_email": current_user.email, "user_id": current_user.id}).fetchone()
        
        daily_stats = {
            "added": daily_stats_row[0] or 0,
            "improved": daily_stats_row[1] or 0,
            "removed": daily_stats_row[2] or 0
        }
            
        return {"activity": feed, "daily_stats": daily_stats}
    except Exception as e:
        print(f"Error in global activity: {e}")
        return {"activity": [], "daily_stats": {"added": 0, "improved": 0, "removed": 0}}


@router.get("/executive-report")
def get_executive_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Generates an executive scorecard across top staffing giants and nationwide coverage."""
    from fastapi.responses import Response
    import csv
    import io
    
    computed_state_sql = EFFECTIVE_RECRUITER_STATE_SQL_R
    results = db.execute(text(f"""
        SELECT 
            COALESCE(c.company_name, 'Independent / Unassigned') AS company_name,
            COUNT(r.recruiter_id) AS total_recruiters,
            COUNT(*) FILTER (WHERE {computed_state_sql} IS NOT NULL AND {computed_state_sql} != 'US') AS known_state_count,
            COUNT(*) FILTER (WHERE r.email IS NOT NULL AND r.email != '' AND r.email NOT LIKE '%missing.local%') AS with_email_count
        FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        WHERE r.user_id = :user_id
        GROUP BY c.company_name
        ORDER BY total_recruiters DESC
        LIMIT 60
    """), {"user_email": current_user.email, "user_id": current_user.id}).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Agency Name", "Total Recruiters", "Known State Mapped", "State Mapped %", "With Email Count"])
    for row in results:
        comp, total, known, email_cnt = row[0], row[1], row[2], row[3]
        pct = round((known / total * 100), 1) if total > 0 else 0
        writer.writerow([comp, total, known, f"{pct}%", email_cnt])

    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=executive_agency_scorecard.csv"})


@router.get("/visitor-logs")
def get_visitor_logs(limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    try:
        visits = db.execute(text("""
            SELECT id, page, path, user_email, session_id, time_on_page, user_agent, ip_address, visited_at
            FROM page_visits 
            ORDER BY visited_at DESC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

        results = []
        for v in visits:
            ts = v["visited_at"].isoformat() if v["visited_at"] else None
            if ts and not ts.endswith('Z') and '+' not in ts: ts += 'Z'
            
            # Simple User Agent Parser
            ua = v["user_agent"] or ""
            browser = "Unknown Browser"
            os = "Unknown OS"
            if "Edg/" in ua: browser = "Edge"
            elif "Chrome/" in ua: browser = "Chrome"
            elif "Firefox/" in ua: browser = "Firefox"
            elif "Safari/" in ua and "Chrome/" not in ua: browser = "Safari"
            
            if "Windows" in ua: os = "Windows"
            elif "Mac OS X" in ua: os = "macOS"
            elif "Linux" in ua: os = "Linux"
            elif "Android" in ua: os = "Android"
            elif "iPhone" in ua or "iPad" in ua: os = "iOS"

            results.append({
                "id": v["id"],
                "page": v["page"],
                "path": v["path"],
                "user_email": v["user_email"],
                "session_id": v["session_id"],
                "time_on_page": v["time_on_page"],
                "ip_address": v["ip_address"] or "Unknown IP",
                "browser": browser,
                "os": os,
                "timestamp": ts,
                "raw_ua": ua
            })
        return {"logs": results}
    except Exception as e:
        print(f"Error in visitor logs: {e}")
        return {"logs": []}

@router.get("/taxonomy-distribution")
def get_taxonomy_distribution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """
    Returns the distribution of recruiter taxonomy categories for a pie chart,
    plus the count of uncategorized records.
    """
    cached = analytics_cache.get("taxonomy_dist")
    if cached is not None:
        return cached

    try:
        rows = db.execute(text("""
            SELECT
                COALESCE(taxonomy_category, 'Uncategorized') AS category,
                COUNT(*) AS count
            FROM recruiters
            WHERE is_active = true
            GROUP BY COALESCE(taxonomy_category, 'Uncategorized')
            ORDER BY count DESC
        """), {"user_email": current_user.email, "user_id": current_user.id}).fetchall()

        distribution = [{"category": r[0], "count": r[1]} for r in rows]

        total = sum(r[1] for r in rows)
        uncategorized = next((r[1] for r in rows if r[0] == "Uncategorized"), 0)

        result = {
            "distribution": distribution,
            "total": total,
            "categorized": total - uncategorized,
            "uncategorized": uncategorized,
            "coverage_pct": round((total - uncategorized) / total * 100, 1) if total > 0 else 0
        }

        analytics_cache.set("taxonomy_dist", result, ttl=120)
        return result
    except Exception as e:
        logger.error(f"Taxonomy distribution error: {e}")
        return {"distribution": [], "total": 0, "categorized": 0, "uncategorized": 0, "coverage_pct": 0}

@router.get("/data-health")
def get_data_health(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """
    Returns data health and completeness metrics for the recruiter database.
    """
    cached = analytics_cache.get("data_health")
    if cached is not None:
        return cached

    try:
        # We check total active recruiters, and how many are missing core fields
        row = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE email IS NULL OR email = '') as missing_email,
                COUNT(*) FILTER (WHERE phone IS NULL OR phone = '') as missing_phone,
                COUNT(*) FILTER (WHERE location IS NULL OR location = '') as missing_location,
                COUNT(*) FILTER (WHERE company_id IS NULL) as missing_company,
                COUNT(*) FILTER (WHERE linkedin IS NULL OR linkedin = '') as missing_linkedin
            FROM recruiters
            WHERE is_active = true
        """), {"user_email": current_user.email, "user_id": current_user.id}).fetchone()

        if not row or row[0] == 0:
            return {"total": 0, "metrics": []}
            
        t = row[0]
        metrics = [
            {"field": "Email", "missing": row[1], "present": t - row[1], "health_pct": round((t - row[1])/t * 100, 1)},
            {"field": "Phone", "missing": row[2], "present": t - row[2], "health_pct": round((t - row[2])/t * 100, 1)},
            {"field": "Location", "missing": row[3], "present": t - row[3], "health_pct": round((t - row[3])/t * 100, 1)},
            {"field": "Company", "missing": row[4], "present": t - row[4], "health_pct": round((t - row[4])/t * 100, 1)},
            {"field": "LinkedIn", "missing": row[5], "present": t - row[5], "health_pct": round((t - row[5])/t * 100, 1)}
        ]
        
        # Calculate overall score (average of health percentages)
        overall_score = sum(m["health_pct"] for m in metrics) / len(metrics)
        
        result = {
            "total_active": t,
            "overall_health_score": round(overall_score, 1),
            "metrics": metrics
        }
        
        analytics_cache.set("data_health", result, ttl=300)
        return result
    except Exception as e:
        logger.error(f"Data health error: {e}")
        return {"total_active": 0, "overall_health_score": 0, "metrics": []}


@router.get("/debug-parquet")
def debug_parquet(force_download: bool = False):
    import os, traceback
    from app.services.recruiter_store import PARQUET_FILE, recruiter_store
    
    res = {
        "parquet_exists": os.path.exists(PARQUET_FILE),
        "parquet_size": os.path.getsize(PARQUET_FILE) if os.path.exists(PARQUET_FILE) else -1,
        "store_loaded": recruiter_store._loaded,
        "record_count": recruiter_store._record_count
    }
    
    if force_download:
        try:
            if os.path.exists(PARQUET_FILE):
                os.remove(PARQUET_FILE)
            recruiter_store.reload()
            res["msg"] = "Force downloaded and reloaded"
            res["new_size"] = os.path.getsize(PARQUET_FILE) if os.path.exists(PARQUET_FILE) else -1
            res["new_count"] = recruiter_store._record_count
        except Exception as e:
            res["error"] = str(e)
            res["trace"] = traceback.format_exc()
            
    return res

@router.get("/insights")
def get_smart_insights(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    cached = analytics_cache.get("dashboard_insights")
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # 1. Recruiter Growth
    today_recs = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE user_id = :user_id AND created_at >= :s"), {"s": today_start, "user_id": current_user.id}).scalar() or 0
    yest_recs = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE user_id = :user_id AND created_at >= :s AND created_at < :e"), {"s": yesterday_start, "e": today_start, "user_id": current_user.id}).scalar() or 0
    
    growth_insight = "Recruiter database is stable with normal operations."
    if today_recs > yest_recs and yest_recs > 0:
        pct = round(((today_recs - yest_recs) / yest_recs) * 100)
        growth_insight = f"You imported {pct}% more recruiters today than yesterday."
    elif today_recs > 0 and yest_recs == 0:
        growth_insight = f"You added {today_recs} new recruiters today."

    # 2. Top State Insight
    top_state_row = db.execute(text("SELECT location, COUNT(*) as c FROM recruiters WHERE user_id = :user_id AND location IS NOT NULL AND location != '' GROUP BY location ORDER BY c DESC LIMIT 1"), {"user_id": current_user.id}).fetchone()
    state_insight = "Geographic distribution is balanced."
    if top_state_row:
        state_insight = f"{top_state_row[0]} generated the highest recruiter density."

    # 3. Traffic Insight
    searches = db.execute(text("SELECT COUNT(*) FROM action_logs WHERE user_email = :user_email AND created_at >= :s AND action_type = 'SEARCH_RECRUITERS'"), {"s": today_start, "user_email": current_user.email}).scalar() or 0
    traffic_insight = "System traffic is at baseline levels."
    if searches > 10:
        traffic_insight = f"High search volume detected: {searches} recruiter searches today."
    elif searches > 0:
        traffic_insight = f"Active sourcing ongoing: {searches} queries executed today."

    insights = [
        {"id": 1, "text": growth_insight, "type": "growth", "icon": "ti-trending-up"},
        {"id": 2, "text": state_insight, "type": "geo", "icon": "ti-map-pin"},
        {"id": 3, "text": traffic_insight, "type": "traffic", "icon": "ti-activity"}
    ]

    analytics_cache.set("dashboard_insights", {"insights": insights}, ttl=300)
    return {"insights": insights}

@router.get("/quality-metrics")
def get_quality_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    # Phase 8 Metrics
    avg_rec_score = db.execute(text("SELECT AVG(completeness_score) FROM recruiters WHERE completeness_score IS NOT NULL")).scalar() or 0
    avg_comp_score = db.execute(text("SELECT AVG(completeness_score) FROM companies WHERE completeness_score IS NOT NULL")).scalar() or 0
    
    overall_health = (avg_rec_score + avg_comp_score) / 2 if (avg_rec_score or avg_comp_score) else 0
    
    recs_completed = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE quality_flags IS NOT NULL")).scalar() or 0
    comps_completed = db.execute(text("SELECT COUNT(*) FROM companies WHERE quality_flags IS NOT NULL")).scalar() or 0
    
    unknown_recs = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE recruiter_name ILIKE 'unknown%' OR location ILIKE 'unknown%'")).scalar() or 0
    
    duplicates = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE merged_into_id IS NOT NULL")).scalar() or 0
    
    low_profiles = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE completeness_score < 50")).scalar() or 0
    
    avg_confidence = db.execute(text("SELECT AVG(confidence) FROM repair_logs")).scalar() or 0
    
    return {
        "overall_health": round(overall_health, 1),
        "avg_recruiter_completeness": round(avg_rec_score, 1),
        "avg_company_completeness": round(avg_comp_score, 1),
        "recruiters_completed": recs_completed,
        "companies_completed": comps_completed,
        "unknown_remaining": unknown_recs,
        "duplicates_identified": duplicates,
        "low_quality_profiles": low_profiles,
        "average_repair_confidence": round(avg_confidence, 1)
    }

@router.get("/repair-logs")
def get_repair_logs(limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    logs = db.execute(text("SELECT id, entity_type, entity_id, field_name, old_value, new_value, confidence, evidence, source, created_at FROM repair_logs ORDER BY created_at DESC LIMIT :limit"), {"limit": limit}).fetchall()
    
    res = []
    for l in logs:
        ts = l[9].isoformat() if l[9] else None
        if ts and not ts.endswith('Z') and '+' not in ts: ts += 'Z'
        res.append({
            "id": l[0],
            "entity_type": l[1],
            "entity_id": l[2],
            "field_name": l[3],
            "old_value": l[4],
            "new_value": l[5],
            "confidence": l[6],
            "evidence": l[7],
            "source": l[8],
            "timestamp": ts
        })
    return {"logs": res}


@router.get("/identity-quality")
def get_identity_quality(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    from ..services.identity_engine import identity_engine
    
    total_companies = db.query(Company).count()
    verified_companies = db.query(Company).filter(Company.verification_status == "verified").count()
    missing_logos = db.query(Company).filter(Company.verification_status == "missing").count()
    unresolved_companies = db.query(Company).filter(Company.verification_status == "unresolved").count()
    invalid_logos = db.query(Company).filter(Company.verification_status == "invalid").count()
    duplicates_merged = identity_engine.state.get("duplicates_merged", 0)
    
    return {
        "total_companies": total_companies,
        "verified_companies": verified_companies,
        "missing_logos": missing_logos,
        "invalid_logos": invalid_logos,
        "unresolved_companies": unresolved_companies,
        "duplicates_merged": duplicates_merged,
        "job_state": identity_engine.state
    }

@router.post("/trigger-identity-job")
async def trigger_identity_job(current_user: User = Depends(get_current_user_from_request)):
    from ..services.identity_engine import identity_engine
    if identity_engine.is_running:
        return {"status": "already running", "state": identity_engine.state}
    
    await identity_engine.start_job()
    return {"status": "started", "state": identity_engine.state}
