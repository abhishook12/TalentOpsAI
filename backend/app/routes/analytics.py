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
from app.utils.logo_domains import select_logo_domain
from app.utils.state_sql import EFFECTIVE_RECRUITER_STATE_SQL_R, UNKNOWN_STATE_SENTINEL


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

logger = logging.getLogger("talentops.analytics")
router = APIRouter()


@router.get("/data-quality")
def get_data_quality():
    from ..olap_sidecar import olap_sidecar
    return olap_sidecar.get_data_quality()


@router.get("/dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    cached = analytics_cache.get("dashboard_kpis")
    if cached is not None:
        return cached

    sql = text("""
        SELECT 
            COUNT(*) as total_recruiters,
            COUNT(*) FILTER (WHERE is_active = true) as active_recruiters,
            COUNT(*) FILTER (WHERE needs_review = true) as needs_review,
            COUNT(*) FILTER (WHERE completeness_score < 50) as low_quality,
            COUNT(*) FILTER (WHERE 
                (email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%') OR 
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
    """)
    res = db.execute(sql).mappings().first()

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
    analytics_cache.set("dashboard_kpis", result, ttl=300)
    return result


@router.get("/recruiters-by-state")
def recruiters_by_state(db: Session = Depends(get_db)):
    cached = analytics_cache.get("recruiters_by_state")
    if cached is not None:
        return cached

    computed_state_sql = EFFECTIVE_RECRUITER_STATE_SQL_R

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
    analytics_cache.set("recruiters_by_state", res_list, ttl=3600)
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

    analytics_cache.set("companies_count_by_state", counts, ttl=3600)
    return counts


@router.get("/company-states")
def company_states(
    company_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    cached = analytics_cache.get(f"company_states_{company_id}")
    if cached is not None:
        return cached

    computed_state_sql = EFFECTIVE_RECRUITER_STATE_SQL_R

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

    unknown_row = db.execute(text(f"""
        SELECT COUNT(r.recruiter_id) AS count
        FROM recruiters r
        LEFT JOIN companies c ON c.company_id = r.company_id
        WHERE r.company_id = :company_id
          AND {computed_state_sql} IS NULL
    """), {"company_id": company_id}).mappings().first()

    result = [{"state": row["state"], "count": int(row["count"])} for row in rows]
    unknown_count = int(unknown_row["count"]) if unknown_row and unknown_row["count"] else 0
    if unknown_count > 0:
        result.append({"state": UNKNOWN_STATE_SENTINEL, "count": unknown_count})

    analytics_cache.set(f"company_states_{company_id}", result, ttl=3600)
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
    dir_query = not q and (not state or state.upper() == 'ALL') and min_recruiters == 1 and limit == 200 and skip == 0
    cache_key = "companies_search_dashboard" if dashboard_query else ("companies_search_dir" if dir_query else "companies_search")
    cached = analytics_cache.get(cache_key)
    if cached is not None and (dashboard_query or dir_query or (not q and not state and min_recruiters == 0 and limit == 100 and skip == 0)):
        response.headers["X-Total-Count"] = str(cached["total_count"])
        return cached["rows"]

    where_clauses = ["c.is_active = true"]
    params = {"limit": limit, "min_recruiters": min_recruiters, "skip": skip}

    if q:
        q_clean = q.strip()
        import re
        q_ilike = re.sub(r'\s+', '%', q_clean)
        # Use pg_trgm similarity (fuzzy matching) and ILIKE fallback for robustness
        where_clauses.append("(c.company_name % :q OR ca.alias_name % :q OR c.company_name ILIKE '%' || :q_ilike || '%' OR ca.alias_name ILIKE '%' || :q_ilike || '%')")
        params["q"] = q_clean
        params["q_ilike"] = q_ilike
        sim_col = "GREATEST(similarity(c.company_name, :q), COALESCE(similarity(ca.alias_name, :q), 0))"
    else:
        sim_col = "0"

    if state and state.upper() != "ALL":
        where_clauses.append("c.state = :state")
        params["state"] = state.upper()

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        WITH recruiter_counts AS (
            SELECT company_id, COUNT(recruiter_id) as rc_count
            FROM recruiters
            WHERE company_id IS NOT NULL
            GROUP BY company_id
        ),
        comp_stats AS (
            SELECT 
                c.company_id,
                c.company_name,
                c.location,
                c.industry,
                c.website,
                c.email_pattern,
                COALESCE(rc.rc_count, 0) AS recruiter_count,
                COALESCE(NULLIF(TRIM(c.state), ''), 'US') AS state_abbr,
                MAX({{sim_col}}) AS sim_score
            FROM companies c
            LEFT JOIN recruiter_counts rc ON c.company_id = rc.company_id
            LEFT JOIN company_aliases ca ON c.company_id = ca.canonical_company_id
            WHERE {{where_sql}}
            GROUP BY c.company_id, rc.rc_count
        )
        SELECT *, 0 AS missing_state_count, 0 AS needs_review_count, COUNT(*) OVER() AS full_count
        FROM comp_stats
        WHERE recruiter_count >= :min_recruiters
        ORDER BY sim_score DESC, recruiter_count DESC, company_name ASC
        LIMIT :limit OFFSET :skip
    """
    sql = sql.format(sim_col=sim_col, where_sql=where_sql)
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
            "email_pattern": row["email_pattern"],
            "logo_domain": select_logo_domain(row["website"], row["email_pattern"]),
            "recruiter_count": int(row["recruiter_count"]),
            "state_abbr": row["state_abbr"] or "Unknown",
            "missing_state_count": int(row["missing_state_count"]),
            "needs_review_count": int(row["needs_review_count"]),
        })

    if dashboard_query:
        analytics_cache.set("companies_search_dashboard", {"total_count": total_count, "rows": res}, ttl=3600)
    elif dir_query:
        analytics_cache.set("companies_search_dir", {"total_count": total_count, "rows": res}, ttl=3600)
    elif not q and not state and min_recruiters == 0 and limit == 100 and skip == 0:
        analytics_cache.set("companies_search", {"total_count": total_count, "rows": res}, ttl=3600)

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
    analytics_cache.set("visit_stats", result, ttl=3600)
    return result

@router.get("/enrichment-feed")
def get_enrichment_feed(db: Session = Depends(get_db)):
    try:
        discovered = db.execute(text("""
            SELECT r.recruiter_name, r.title, r.created_at, 'discovery' as type,
                   c.company_name, r.email, r.phone, r.location
            FROM recruiters r
            JOIN companies c ON r.company_id = c.company_id
            WHERE r.data_source = 'discovery_worker'
            AND r.company_id IS NOT NULL
            ORDER BY r.created_at DESC 
            LIMIT 50
        """)).fetchall()
        
        enriched = db.execute(text("""
            SELECT r.recruiter_name, r.title, r.updated_at as created_at, 'enriched' as type,
                   c.company_name, r.email, r.phone, r.location
            FROM recruiters r
            JOIN companies c ON r.company_id = c.company_id
            WHERE (r.phone IS NOT NULL OR r.email IS NOT NULL) 
            AND r.company_id IS NOT NULL
            AND r.updated_at > r.created_at
            ORDER BY r.updated_at DESC 
            LIMIT 50
        """)).fetchall()
        
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
def get_global_activity(
    limit: int = 200,
    db: Session = Depends(get_db)
):
    try:
        # Fetch the most recently updated high-quality records
        records = db.execute(text("""
            SELECT r.recruiter_id, r.recruiter_name, r.title, r.location, r.phone, r.email, 
                   r.created_at, r.updated_at, r.is_active, c.company_name
            FROM recruiters r
            LEFT JOIN companies c ON r.company_id = c.company_id
            WHERE r.recruiter_name IS NOT NULL AND r.recruiter_name != ''
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
                COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) as added,
                COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE AND (phone IS NOT NULL OR email IS NOT NULL) AND created_at < CURRENT_DATE AND is_active = true) as improved,
                COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE AND is_active = false) as removed
            FROM recruiters
            WHERE updated_at >= CURRENT_DATE OR created_at >= CURRENT_DATE
        """)).fetchone()
        
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
def get_executive_report(db: Session = Depends(get_db)):
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
        GROUP BY c.company_name
        ORDER BY total_recruiters DESC
        LIMIT 60
    """)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Agency Name", "Total Recruiters", "Known State Mapped", "State Mapped %", "With Email Count"])
    for row in results:
        comp, total, known, email_cnt = row[0], row[1], row[2], row[3]
        pct = round((known / total * 100), 1) if total > 0 else 0
        writer.writerow([comp, total, known, f"{pct}%", email_cnt])

    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=executive_agency_scorecard.csv"})


@router.get("/visitor-logs")
def get_visitor_logs(limit: int = 100, db: Session = Depends(get_db)):
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
def get_taxonomy_distribution(db: Session = Depends(get_db)):
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
        """)).fetchall()

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
def get_data_health(db: Session = Depends(get_db)):
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
        """)).fetchone()

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
