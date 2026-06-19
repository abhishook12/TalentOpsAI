from datetime import datetime, timedelta
from threading import Lock
from typing import Optional
import logging
import time

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Company, PageVisit, Recruiter, Vendor


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
logger = logging.getLogger("talentops.analytics")
router = APIRouter()


@router.get("/data-quality")
def get_data_quality(db: Session = Depends(get_db)):
    cached = analytics_cache.get("data_quality")
    if cached is not None:
        return cached

    recruiter_counts = db.execute(text("""
        SELECT
            COUNT(*) AS total_recruiters,
            COUNT(*) FILTER (WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%') AS real_emails,
            COUNT(*) FILTER (WHERE phone IS NOT NULL AND phone != '') AS phones,
            COUNT(*) FILTER (WHERE company_id IS NOT NULL) AS companies_linked,
            COUNT(*) FILTER (WHERE state IS NOT NULL AND state != '') AS with_state,
            COUNT(DISTINCT state) FILTER (WHERE state IS NOT NULL AND state != '') AS states_covered,
            COUNT(*) FILTER (WHERE needs_review = true) AS needs_review,
            COUNT(*) FILTER (WHERE state IS NULL OR state = '') AS unknown_state_count,
            COUNT(*) FILTER (WHERE state_source IN ('state_column', 'recruiter_state_col', 'abbreviation_exact_match')) AS direct_state_count,
            COUNT(*) FILTER (WHERE state_source = 'company_state') AS company_state_count,
            COUNT(*) FILTER (WHERE state_source LIKE 'company_majority_state%') AS company_majority_count,
            COUNT(*) FILTER (WHERE state_source = 'email_domain') AS domain_state_count,
            COUNT(*) FILTER (WHERE state_source IN ('recruiter_location', 'company_location', 'notes', 'review_reason', 'metadata_json', 'raw_data')) AS text_inferred_count
        FROM recruiters
    """)).mappings().one()

    total_recruiters = int(recruiter_counts["total_recruiters"] or 0)
    real_emails = int(recruiter_counts["real_emails"] or 0)
    phones = int(recruiter_counts["phones"] or 0)
    companies_linked = int(recruiter_counts["companies_linked"] or 0)
    with_state = int(recruiter_counts["with_state"] or 0)
    states_covered = int(recruiter_counts["states_covered"] or 0)
    needs_review = int(recruiter_counts["needs_review"] or 0)
    unknown_state_count = int(recruiter_counts["unknown_state_count"] or 0)
    direct_state_count = int(recruiter_counts["direct_state_count"] or 0)
    company_state_count = int(recruiter_counts["company_state_count"] or 0)
    company_majority_count = int(recruiter_counts["company_majority_count"] or 0)
    domain_state_count = int(recruiter_counts["domain_state_count"] or 0)
    text_inferred_count = int(recruiter_counts["text_inferred_count"] or 0)

    total_companies = db.execute(text("SELECT COUNT(*) FROM companies")).scalar() or 0

    try:
        db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    except Exception:
        db_size = "Unknown"

    duplicate_risk = db.execute(
        text("SELECT COUNT(*) FROM (SELECT phone FROM recruiters WHERE phone IS NOT NULL AND phone != '' GROUP BY phone HAVING COUNT(*) > 1) t")
    ).scalar() or 0

    explicit_state_count = direct_state_count
    pre_existing_states = db.execute(text("""
        SELECT COUNT(*)
        FROM recruiters
        WHERE (state IS NOT NULL AND state != '')
          AND (state_source IS NULL OR state_source = '')
    """)).scalar() or 0
    explicit_state_count += pre_existing_states
    inferred_state_count = max(with_state - explicit_state_count, 0)

    email_cov = round((real_emails / total_recruiters * 100), 1) if total_recruiters else 0
    phone_cov = round((phones / total_recruiters * 100), 1) if total_recruiters else 0
    comp_cov = round((companies_linked / total_recruiters * 100), 1) if total_recruiters else 0
    state_cov = round((with_state / total_recruiters * 100), 1) if total_recruiters else 0
    review_cov = round((needs_review / total_recruiters * 100), 1) if total_recruiters else 0
    quality_score = round((email_cov * 0.4) + (phone_cov * 0.2) + (comp_cov * 0.2) + (state_cov * 0.2), 1)

    result = {
        "total_recruiters": total_recruiters,
        "total_companies": total_companies,
        "states_covered": states_covered,
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
        "duplicate_risk_count": duplicate_risk,
        "needs_review_count": needs_review,
        "known_state_count": with_state,
        "unknown_state_count": unknown_state_count,
        "explicit_state_count": explicit_state_count,
        "inferred_state_count": inferred_state_count,
        "company_state_count": company_state_count,
        "company_majority_state_count": company_majority_count,
        "domain_state_count": domain_state_count,
        "text_inferred_state_count": text_inferred_count,
    }

    analytics_cache.set("data_quality", result, ttl=300)
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
            (Recruiter.email4.isnot(None)) & (Recruiter.email4 != ""),
        )
    ).count()

    with_phone = db.query(Recruiter).filter(
        or_(
            (Recruiter.phone.isnot(None)) & (Recruiter.phone != ""),
            (Recruiter.phone2.isnot(None)) & (Recruiter.phone2 != ""),
            (Recruiter.phone3.isnot(None)) & (Recruiter.phone3 != ""),
            (Recruiter.phone4.isnot(None)) & (Recruiter.phone4 != ""),
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
    analytics_cache.set("dashboard_kpis", result, ttl=300)
    return result


@router.get("/recruiters-by-state")
def recruiters_by_state(db: Session = Depends(get_db)):
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
            END,
            NULLIF(TRIM(c.state), ''),
            CASE
                WHEN c.location ~ '^[A-Za-z]{2}$' THEN UPPER(c.location)
                WHEN c.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(c.location FROM '([A-Za-z]{2})$'))
                ELSE NULL
            END
        )
    """

    results = db.execute(text(f"""
        SELECT
            {computed_state_sql} AS state,
            COUNT(r.recruiter_id) AS count
        FROM recruiters r
        LEFT JOIN companies c ON c.company_id = r.company_id
        WHERE {computed_state_sql} IS NOT NULL
        GROUP BY {computed_state_sql}
        ORDER BY count DESC, state ASC
    """)).mappings().all()

    res_list = [{"state": row["state"], "count": int(row["count"])} for row in results]
    analytics_cache.set("recruiters_by_state", res_list, ttl=300)
    return res_list


@router.get("/companies-count-by-state")
def companies_count_by_state(db: Session = Depends(get_db)):
    cached = analytics_cache.get("companies_count_by_state")
    if cached is not None:
        return cached

    rows = db.execute(text("""
        SELECT
            COALESCE(
                NULLIF(TRIM(c.state), ''),
                CASE
                    WHEN c.location ~ '^[A-Za-z]{2}$' THEN UPPER(c.location)
                    WHEN c.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(c.location FROM '([A-Za-z]{2})$'))
                    ELSE NULL
                END,
                NULLIF(TRIM(r.state), ''),
                'Unknown'
            ) AS state,
            COUNT(DISTINCT c.company_id) AS count
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        GROUP BY 1
        ORDER BY count DESC
    """)).mappings().all()

    counts = {}
    for row in rows:
        state = row["state"] or "Unknown"
        counts[state] = int(row["count"])

    analytics_cache.set("companies_count_by_state", counts, ttl=300)
    return counts


@router.get("/company-states")
def company_states(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    cached = analytics_cache.get(f"company_states_{company_id}")
    if cached is not None:
        return cached

    computed_state_sql = """
        COALESCE(
            NULLIF(TRIM(r.state), ''),
            CASE
                WHEN r.location ~ '^[A-Za-z]{2}$' THEN UPPER(r.location)
                WHEN r.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(r.location FROM '([A-Za-z]{2})$'))
                ELSE NULL
            END,
            NULLIF(TRIM(c.state), ''),
            CASE
                WHEN c.location ~ '^[A-Za-z]{2}$' THEN UPPER(c.location)
                WHEN c.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(c.location FROM '([A-Za-z]{2})$'))
                ELSE NULL
            END
        )
    """

    rows = db.execute(text(f"""
        SELECT
            {computed_state_sql} AS state,
            COUNT(r.recruiter_id) AS count
        FROM recruiters r
        LEFT JOIN companies c ON c.company_id = r.company_id
        WHERE r.company_id = :company_id
          AND {computed_state_sql} IS NOT NULL
        GROUP BY {computed_state_sql}
        ORDER BY count DESC, state ASC
    """), {"company_id": company_id}).mappings().all()

    result = [{"state": row["state"], "count": int(row["count"])} for row in rows]
    analytics_cache.set(f"company_states_{company_id}", result, ttl=300)
    return result


@router.get("/companies-search")
def companies_search(
    response: Response,
    q: Optional[str] = Query(None, description="Search company name"),
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    min_recruiters: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    dashboard_query = not q and (not state or state.upper() == 'ALL') and min_recruiters == 1 and limit == 6 and skip == 0
    cached = analytics_cache.get("companies_search_dashboard" if dashboard_query else "companies_search")
    if cached is not None and ((dashboard_query) or (not q and not state and min_recruiters == 0 and limit == 100 and skip == 0)):
        response.headers["X-Total-Count"] = str(cached["total_count"])
        return cached["rows"]

    sql = """
        SELECT
            c.company_id,
            c.company_name,
            c.location,
            c.industry,
            c.website,
            COUNT(DISTINCT r.recruiter_id) AS recruiter_count,
            COALESCE(
                NULLIF(TRIM(c.state), ''),
                CASE
                    WHEN c.location ~ '^[A-Za-z]{2}$' THEN UPPER(c.location)
                    WHEN c.location ~ '.*[ ,]([A-Za-z]{2})$' THEN UPPER(SUBSTRING(c.location FROM '([A-Za-z]{2})$'))
                    ELSE MAX(NULLIF(TRIM(r.state), ''))
                END,
                'Unknown'
            ) AS state_abbr,
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
        sql += " AND (r.state = :state OR ((r.state IS NULL OR r.state = '') AND c.state = :state))"
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
            "state_abbr": row["state_abbr"] or "Unknown",
            "missing_state_count": int(row["missing_state_count"]),
            "needs_review_count": int(row["needs_review_count"]),
        })

    if dashboard_query:
        analytics_cache.set("companies_search_dashboard", {"total_count": total_count, "rows": res}, ttl=300)
    elif not q and not state and min_recruiters == 0 and limit == 100 and skip == 0:
        analytics_cache.set("companies_search", {"total_count": total_count, "rows": res}, ttl=300)

    return res


class VisitPayload(BaseModel):
    page: str
    path: str
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    time_on_page: Optional[int] = None


@router.post("/log-visit")
def log_visit(payload: VisitPayload, request: Request, db: Session = Depends(get_db)):
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
    db.commit()
    analytics_cache.invalidate("visit_stats")
    return {"ok": True}


@router.get("/visit-stats")
def visit_stats(db: Session = Depends(get_db)):
    cached = analytics_cache.get("visit_stats")
    if cached is not None:
        return cached

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    daily = db.execute(text("""
        SELECT DATE(visited_at) AS day, COUNT(*) AS visits
        FROM page_visits
        WHERE visited_at >= :since
        GROUP BY day ORDER BY day ASC
    """), {"since": seven_days_ago}).mappings().all()

    thirty_days_ago = now - timedelta(days=30)
    weekly = db.execute(text("""
        SELECT
            DATE_TRUNC('week', visited_at)::date AS week_start,
            COUNT(*) AS visits
        FROM page_visits
        WHERE visited_at >= :since
        GROUP BY week_start ORDER BY week_start ASC
    """), {"since": thirty_days_ago}).mappings().all()

    top_pages = db.execute(text("""
        SELECT page, COUNT(*) AS visits
        FROM page_visits
        GROUP BY page ORDER BY visits DESC
        LIMIT 10
    """)).mappings().all()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    today_count = db.execute(text("SELECT COUNT(*) FROM page_visits WHERE visited_at >= :s"), {"s": today_start}).scalar() or 0
    yesterday_count = db.execute(
        text("SELECT COUNT(*) FROM page_visits WHERE visited_at >= :s AND visited_at < :e"),
        {"s": yesterday_start, "e": today_start},
    ).scalar() or 0
    total_count = db.execute(text("SELECT COUNT(*) FROM page_visits")).scalar() or 0

    result = {
        "total_visits": total_count,
        "today": today_count,
        "yesterday": yesterday_count,
        "daily": [{"day": str(r["day"]), "visits": r["visits"]} for r in daily],
        "weekly": [{"week": str(r["week_start"]), "visits": r["visits"]} for r in weekly],
        "top_pages": [{"page": r["page"], "visits": r["visits"]} for r in top_pages],
    }
    analytics_cache.set("visit_stats", result, ttl=300)
    return result
