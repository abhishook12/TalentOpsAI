import re
from fastapi import APIRouter, Depends, Query, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import ProgrammingError
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

@router.get("/dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    cached = analytics_cache.get("dashboard_kpis")
    if cached is not None:
        return cached
    total_recruiters = db.query(Recruiter).count()
    active_recruiters = db.query(Recruiter).filter(Recruiter.is_active == True).count()
    needs_review = db.query(Recruiter).filter(Recruiter.needs_review == True).count()
    low_quality = db.query(Recruiter).filter(Recruiter.completeness_score < 50).count()
    with_email = db.query(Recruiter).filter(
        Recruiter.email.isnot(None), Recruiter.email != ""
    ).count()
    with_phone = db.query(Recruiter).filter(
        Recruiter.phone.isnot(None), Recruiter.phone != ""
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
    """Top states by recruiter count.

    Prefer `recruiters.state` when present, otherwise try to derive a 2-letter
    state code from `recruiters.location` (e.g. "TX", "Austin, TX").
    """
    cached = analytics_cache.get("recruiters_by_state")
    if cached is not None:
        return cached

    # Compute a best-effort 2-letter state value without relying on materialized views,
    # since many environments (or older datasets) may not have a populated `state` column.
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

    try:
        results = db.execute(text("SELECT state, count FROM mv_recruiters_by_state ORDER BY count DESC LIMIT 20")).mappings().all()

        # If the materialized view is present but returns too few states, fall back to live aggregation.
        # This commonly happens when older data stores state only in `location`.
        if len(results) < 2:
            distinct_from_location = db.execute(text(f"""
                SELECT COUNT(DISTINCT {computed_state_sql}) AS c
                FROM recruiters r
                WHERE {computed_state_sql} IS NOT NULL
            """)).mappings().first()
            if distinct_from_location and int(distinct_from_location["c"] or 0) >= 2:
                raise ProgrammingError("mv_recruiters_by_state appears incomplete for this dataset", None, None)
    except ProgrammingError as e:
        # Render/Neon may not have had materialized views created yet.
        logger.warning("mv_recruiters_by_state missing; falling back to live aggregation: %s", e)
        db.rollback()
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
                    COALESCE(c.state, r.state) AS state,
                    COUNT(DISTINCT c.company_id) AS count
                FROM companies c
                LEFT JOIN recruiters r ON r.company_id = c.company_id
                WHERE COALESCE(c.state, r.state) IS NOT NULL
                GROUP BY COALESCE(c.state, r.state)
            """)).mappings().all()
        except ProgrammingError as e2:
            # Some environments may not have `companies.state` yet.
            logger.warning("companies.state missing; using recruiters.state only: %s", e2)
            db.rollback()
            rows = db.execute(text("""
                SELECT
                    r.state AS state,
                    COUNT(DISTINCT c.company_id) AS count
                FROM companies c
                JOIN recruiters r ON r.company_id = c.company_id
                WHERE r.state IS NOT NULL AND r.state != ''
                GROUP BY r.state
            """)).mappings().all()

    counts = {row["state"]: row["count"] for row in rows}

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
            COALESCE(c.state, r.state) AS state_abbr,
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
        sql += " AND COALESCE(c.state, r.state) = :state"
        params["state"] = state.upper()


    sql += """
        GROUP BY c.company_id, c.company_name, c.location, c.industry, c.website, COALESCE(c.state, r.state)
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
