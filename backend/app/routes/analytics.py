import re
from fastapi import APIRouter, Depends, Query, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional
from app.database import get_db
from app.models.models import Recruiter, Company, Vendor, PageVisit
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging



import time
from threading import Lock

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
                else:
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
logger = logging.getLogger("talentops.analytics")

router = APIRouter()

@router.get("/data-quality")
def get_data_quality(db: Session = Depends(get_db)):
    cached = analytics_cache.get("data_quality")
    if cached is not None:
        return cached

    total_recruiters = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
    total_companies = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
    states_covered = db.execute(text("SELECT COUNT(DISTINCT state) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar()
    
    try:
        db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    except Exception:
        db_size = "Unknown"

    real_emails = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%'")).scalar()
    phones = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL AND phone != ''")).scalar()
    companies_linked = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL")).scalar()
    with_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar()

    duplicate_risk = db.execute(text("SELECT COUNT(*) FROM (SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' GROUP BY phone HAVING COUNT(*) > 1) t")).scalar()
    needs_review = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE needs_review = true")).scalar()
    
    # State specific metrics
    unknown_state_count = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar()
    explicit_state_count = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state_source = 'recruiter_state_col' OR state_source = 'abbreviation_exact_match'")).scalar()
    # Explicit before backfill + any new explicit matches
    inferred_state_count = with_state - explicit_state_count
    # Add pre-existing clean states (which have state_source IS NULL but state IS NOT NULL) to explicit_state_count
    pre_existing_states = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE (state IS NOT NULL AND state != '') AND (state_source IS NULL OR state_source = '')")).scalar()
    explicit_state_count += pre_existing_states
    inferred_state_count = with_state - explicit_state_count

    # Calculate coverages safely
    email_cov = round((real_emails / total_recruiters * 100), 1) if total_recruiters else 0
    phone_cov = round((phones / total_recruiters * 100), 1) if total_recruiters else 0
    comp_cov = round((companies_linked / total_recruiters * 100), 1) if total_recruiters else 0
    state_cov = round((with_state / total_recruiters * 100), 1) if total_recruiters else 0
    review_cov = round((needs_review / total_recruiters * 100), 1) if total_recruiters else 0

    # Calculate overall score (weighted average of coverages)
    quality_score = round((email_cov * 0.4) + (phone_cov * 0.2) + (comp_cov * 0.2) + (state_cov * 0.2), 1)

    result = {
        "total_recruiters": total_recruiters,
        "total_companies": total_companies,
        "states_covered": states_covered or 0,
        "database_size": db_size,
        
        "email_coverage": email_cov,
        "phone_coverage": phone_cov,
        "company_coverage": comp_cov,
        "state_coverage": state_cov,
        "needs_review_percent": review_cov,
        "quality_score": quality_score,
        
        "missing_email_count": total_recruiters - real_emails,
        "missing_phone_count": total_recruiters - phones,
        "missing_company_count": total_recruiters - companies_linked,
        "missing_state_count": unknown_state_count,
        
        "duplicate_risk_count": duplicate_risk or 0,
        "needs_review_count": needs_review or 0,
        
        # New State Metrics
        "known_state_count": with_state,
        "unknown_state_count": unknown_state_count,
        "explicit_state_count": explicit_state_count,
        "inferred_state_count": inferred_state_count,
    }
    
    analytics_cache.set("data_quality", result, ttl=60)
    return result

@router.get("/dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    cached = analytics_cache.get("dashboard_kpis")
    if cached is not None:
        return cached
    total_recruiters = db.query(Recruiter).count()
    active_recruiters = db.query(Recruiter).filter(Recruiter.is_active == True).count()
    needs_review = db.query(Recruiter).filter(Recruiter.needs_review == True).count()
    low_quality = db.query(Recruiter).filter(Recruiter.completeness_score < 50).count()
    from sqlalchemy import or_
    with_email = db.query(Recruiter).filter(
        or_(
            (Recruiter.email.isnot(None)) & (Recruiter.email != "") & (~Recruiter.email.like("%@missing.local%")),
            (Recruiter.email2.isnot(None)) & (Recruiter.email2 != ""),
            (Recruiter.email3.isnot(None)) & (Recruiter.email3 != ""),
            (Recruiter.email4.isnot(None)) & (Recruiter.email4 != "")
        )
    ).count()
    with_phone = db.query(Recruiter).filter(
        or_(
            (Recruiter.phone.isnot(None)) & (Recruiter.phone != ""),
            (Recruiter.phone2.isnot(None)) & (Recruiter.phone2 != ""),
            (Recruiter.phone3.isnot(None)) & (Recruiter.phone3 != ""),
            (Recruiter.phone4.isnot(None)) & (Recruiter.phone4 != "")
        )
    ).count()
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
    analytics_cache.set("dashboard_kpis", result, ttl=30)
    return result

@router.get("/recruiters-by-state")
def recruiters_by_state(db: Session = Depends(get_db)):
    """Top states by recruiter count computed directly from live recruiter data."""
    cached = analytics_cache.get("recruiters_by_state")
    if cached is not None:
        return cached

    computed_state_sql = """
        COALESCE(
            NULLIF(TRIM(r.state), ''),
            CASE
                WHEN r.location ~ '^[A-Za-z]{2}$' THEN UPPER(r.location)
                WHEN r.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(r.location FROM '([A-Za-z]{2})$'))
                ELSE NULL
            END
        )
    """

    results = db.execute(text(f"""
        SELECT
            {computed_state_sql} AS state,
            COUNT(r.recruiter_id) AS count
        FROM recruiters r
        WHERE {computed_state_sql} IS NOT NULL
        GROUP BY {computed_state_sql}
        ORDER BY count DESC
        LIMIT 20
    """)).mappings().all()

    res_list = [{"state": r["state"], "count": int(r["count"])} for r in results]
    analytics_cache.set("recruiters_by_state", res_list, ttl=30)
    return res_list


@router.get("/companies-by-state")
def companies_by_state(db: Session = Depends(get_db)):
    cached = analytics_cache.get("companies_by_state")
    if cached is not None:
        return cached
    """
    Returns companies grouped by state, each with recruiter count.
    State is extracted from the company location field (last word / 2-letter abbr).
    """
    sql = text("""
        SELECT
            c.company_id,
            c.company_name,
            c.location,
            c.industry,
            c.website,
            COUNT(r.recruiter_id) AS recruiter_count,
            COALESCE(c.state, r.state) AS state_abbr
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        GROUP BY c.company_id, c.company_name, c.location, c.industry, c.website, COALESCE(c.state, r.state)
        ORDER BY recruiter_count DESC, c.company_name ASC
    """)
    rows = db.execute(sql).mappings().all()
    res = []
    for row in rows:
        res.append({
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "location": row["location"],
            "industry": row["industry"],
            "website": row["website"],
            "recruiter_count": int(row["recruiter_count"]),
            "state_abbr": row["state_abbr"] or 'Unknown',
        })
    analytics_cache.set("companies_by_state", res, ttl=30)
    return res

@router.get("/companies-count-by-state")
def companies_count_by_state(db: Session = Depends(get_db)):
    cached = analytics_cache.get("companies_count_by_state")
    if cached is not None:
        return cached

    try:
        sql = text("SELECT state, count FROM mv_state_company_counts")
        rows = db.execute(sql).mappings().all()
    except ProgrammingError as e:
        logger.warning("mv_state_company_counts missing; falling back to live aggregation: %s", e)
        db.rollback()
        try:
            rows = db.execute(text("""
                SELECT
                    COALESCE(COALESCE(r.state, c.state), 'Unknown') AS state,
                    COUNT(DISTINCT c.company_id) AS count
                FROM companies c
                LEFT JOIN recruiters r ON r.company_id = c.company_id
                GROUP BY COALESCE(COALESCE(r.state, c.state), 'Unknown')
            """)).mappings().all()
        except ProgrammingError as e2:
            # Some environments may not have `companies.state` yet.
            logger.warning("companies.state missing; using recruiters.state only: %s", e2)
            db.rollback()
            rows = db.execute(text("""
                SELECT
                    COALESCE(r.state, 'Unknown') AS state,
                    COUNT(DISTINCT c.company_id) AS count
                FROM companies c
                LEFT JOIN recruiters r ON r.company_id = c.company_id
                GROUP BY COALESCE(r.state, 'Unknown')
            """)).mappings().all()

    # Filter out actual empty string state keys if they slip through, map to Unknown
    counts = {}
    for row in rows:
        st = row["state"]
        if not st or st.strip() == '':
            st = 'Unknown'
        counts[st] = counts.get(st, 0) + row["count"]

    analytics_cache.set("companies_count_by_state", counts, ttl=30)
    return counts


@router.get("/companies-search")
def companies_search(
    response: Response,
    q: Optional[str] = Query(None, description="Search company name"),
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    min_recruiters: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Searchable + filterable company directory with recruiter counts.
    """
    sql = """
        SELECT
            c.company_id,
            c.company_name,
            c.location,
            c.industry,
            c.website,
            COUNT(DISTINCT r.recruiter_id) AS recruiter_count,
            COALESCE(c.state, MAX(r.state)) AS state_abbr,
            COUNT(CASE WHEN r.state IS NULL OR r.state = '' THEN 1 END) AS missing_state_count,
            COUNT(CASE WHEN r.needs_review = true THEN 1 END) AS needs_review_count,
            COUNT(*) OVER() AS full_count
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        WHERE 1=1
    """
    params = {"limit": limit, "min_recruiters": min_recruiters, "skip": skip}

    if q:
        from app.utils.normalizer import normalize_text
        clean_q = normalize_text(q)
        sql += " AND c.normalized_company_name ILIKE '%' || :q || '%'"
        params["q"] = clean_q
    if state and state.upper() != "ALL":
        sql += " AND (r.state = :state OR ( (r.state IS NULL OR r.state = '') AND c.state = :state ))"
        params["state"] = state.upper()


    sql += """
        GROUP BY c.company_id, c.company_name, c.location, c.industry, c.website, c.state
        HAVING COUNT(DISTINCT r.recruiter_id) >= :min_recruiters
        ORDER BY recruiter_count DESC, c.company_name ASC
        LIMIT :limit OFFSET :skip
    """
    rows = db.execute(text(sql), params).mappings().all()
    
    total_count = rows[0]["full_count"] if rows and "full_count" in rows[0] else 0
    response.headers["X-Total-Count"] = str(total_count)
    
    res = []
    for row in rows:
        res.append({
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "location": row["location"],
            "industry": row["industry"],
            "website": row["website"],
            "recruiter_count": int(row["recruiter_count"]),
            "state_abbr": row["state_abbr"] or 'Unknown',
            "missing_state_count": int(row["missing_state_count"]),
            "needs_review_count": int(row["needs_review_count"]),
        })
    return res


# ─── Visit Tracking ────────────────────────────────────────────────────────────

class VisitPayload(BaseModel):
    page: str
    path: str
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    time_on_page: Optional[int] = None   # seconds on previous page

@router.post("/log-visit")
def log_visit(payload: VisitPayload, request: Request, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "")[:300]
    # Try to get real IP behind proxy
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
    db.commit()
    analytics_cache.invalidate("visit_stats")
    return {"ok": True}


@router.get("/visit-stats")
def visit_stats(db: Session = Depends(get_db)):
    cached = analytics_cache.get("visit_stats")
    if cached is not None:
        return cached
    now = datetime.utcnow()

    # Last 7 days — visits per day
    seven_days_ago = now - timedelta(days=7)
    daily = db.execute(text("""
        SELECT DATE(visited_at) AS day, COUNT(*) AS visits
        FROM page_visits
        WHERE visited_at >= :since
        GROUP BY day ORDER BY day ASC
    """), {"since": seven_days_ago}).mappings().all()

    # Last 30 days — visits per week bucket
    thirty_days_ago = now - timedelta(days=30)
    weekly = db.execute(text("""
        SELECT
            DATE_TRUNC('week', visited_at)::date AS week_start,
            COUNT(*) AS visits
        FROM page_visits
        WHERE visited_at >= :since
        GROUP BY week_start ORDER BY week_start ASC
    """), {"since": thirty_days_ago}).mappings().all()

    # Top pages all-time
    top_pages = db.execute(text("""
        SELECT page, COUNT(*) AS visits
        FROM page_visits
        GROUP BY page ORDER BY visits DESC
        LIMIT 10
    """)).mappings().all()

    # Today vs yesterday totals
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    today_count = db.execute(text("""
        SELECT COUNT(*) FROM page_visits WHERE visited_at >= :s
    """), {"s": today_start}).scalar()
    yesterday_count = db.execute(text("""
        SELECT COUNT(*) FROM page_visits WHERE visited_at >= :s AND visited_at < :e
    """), {"s": yesterday_start, "e": today_start}).scalar()
    total_count = db.execute(text("SELECT COUNT(*) FROM page_visits")).scalar()

    result = {
        "total_visits": total_count,
        "today": today_count,
        "yesterday": yesterday_count,
        "daily": [{"day": str(r["day"]), "visits": r["visits"]} for r in daily],
        "weekly": [{"week": str(r["week_start"]), "visits": r["visits"]} for r in weekly],
        "top_pages": [{"page": r["page"], "visits": r["visits"]} for r in top_pages],
    }
    analytics_cache.set("visit_stats", result, ttl=30)
    return result
