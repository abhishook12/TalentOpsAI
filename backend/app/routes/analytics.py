import re
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from typing import Optional
from app.database import get_db
from app.models.models import Recruiter, Candidate, Submission, Company, Vendor, PageVisit
from pydantic import BaseModel
from datetime import datetime, timedelta

STATE_MAP = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
    'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
    'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
    'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS', 'MISSOURI': 'MO',
    'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ',
    'NEW MEXICO': 'NM', 'NEW YORK': 'NY', 'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH',
    'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT',
    'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'
}
ABBR_TO_NAME = {v: k for k, v in STATE_MAP.items()}

def get_state_abbr(location: Optional[str]) -> str:
    if not location:
        return 'Unknown'
    loc_upper = location.upper()
    for state_name, abbr in STATE_MAP.items():
        if re.search(r'\b' + re.escape(state_name) + r'\b', loc_upper):
            return abbr
    
    tokens = re.findall(r'\b[A-Z]{2}\b', loc_upper)
    for token in tokens:
        if token in ABBR_TO_NAME:
            return token
            
    parts = [p.strip() for p in re.split(r'[,\s]+', loc_upper) if p.strip()]
    for p in reversed(parts):
        if p in ABBR_TO_NAME:
            return p
            
    return 'Unknown'

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

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    cached = analytics_cache.get("dashboard_kpis")
    if cached is not None:
        return cached
    total_recruiters    = db.query(Recruiter).count()
    active_recruiters   = db.query(Recruiter).filter(Recruiter.is_active == True).count()
    total_candidates    = db.query(Candidate).count()
    duplicate_candidates = db.query(Candidate).filter(Candidate.is_duplicate == True).count()
    total_submissions   = db.query(Submission).count()
    placed              = db.query(Submission).filter(Submission.status == "placed").count()
    interviews          = db.query(Submission).filter(Submission.status == "interview").count()
    offers              = db.query(Submission).filter(Submission.status == "offer").count()
    total_companies     = db.query(Company).count()
    total_vendors       = db.query(Vendor).count()

    placement_rate = round((placed / total_submissions * 100), 1) if total_submissions > 0 else 0
    duplicate_rate = round((duplicate_candidates / total_candidates * 100), 1) if total_candidates > 0 else 0

    result = {
        "recruiters": {
            "total": total_recruiters,
            "active": active_recruiters,
            "inactive": total_recruiters - active_recruiters
        },
        "candidates": {
            "total": total_candidates,
            "duplicates": duplicate_candidates,
            "duplicate_rate_percent": duplicate_rate
        },
        "submissions": {
            "total": total_submissions,
            "placed": placed,
            "interviews": interviews,
            "offers": offers,
            "placement_rate_percent": placement_rate
        },
        "companies": {"total": total_companies},
        "vendors": {"total": total_vendors}
    }
    analytics_cache.set("dashboard_kpis", result, ttl=30)
    return result

@router.get("/submissions-by-status")
def submissions_by_status(db: Session = Depends(get_db)):
    cached = analytics_cache.get("submissions_by_status")
    if cached is not None:
        return cached
    results = db.query(
        Submission.status,
        func.count(Submission.submission_id).label("count")
    ).group_by(Submission.status).all()
    res_list = [{"status": r.status, "count": r.count} for r in results]
    analytics_cache.set("submissions_by_status", res_list, ttl=30)
    return res_list

@router.get("/candidates-by-visa")
def candidates_by_visa(db: Session = Depends(get_db)):
    cached = analytics_cache.get("candidates_by_visa")
    if cached is not None:
        return cached
    results = db.query(
        Candidate.visa_status,
        func.count(Candidate.candidate_id).label("count")
    ).group_by(Candidate.visa_status).all()
    res_list = [{"visa_status": r.visa_status, "count": r.count} for r in results]
    analytics_cache.set("candidates_by_visa", res_list, ttl=30)
    return res_list

@router.get("/recruiter-productivity")
def recruiter_productivity(db: Session = Depends(get_db)):
    cached = analytics_cache.get("recruiter_productivity")
    if cached is not None:
        return cached
    results = db.query(
        Recruiter.recruiter_name,
        func.count(Submission.submission_id).label("total_submissions"),
        func.sum(case((Submission.status == "placed", 1), else_=0)).label("placements"),
        func.sum(case((Submission.status == "interview", 1), else_=0)).label("interviews")
    ).join(Submission, Submission.recruiter_id == Recruiter.recruiter_id, isouter=True)\
     .group_by(Recruiter.recruiter_id, Recruiter.recruiter_name).all()

    res_list = [{
        "recruiter": r.recruiter_name,
        "total_submissions": r.total_submissions or 0,
        "placements": r.placements or 0,
        "interviews": r.interviews or 0
    } for r in results]
    analytics_cache.set("recruiter_productivity", res_list, ttl=30)
    return res_list

@router.get("/submissions-trend")
def submissions_trend(db: Session = Depends(get_db)):
    cached = analytics_cache.get("submissions_trend")
    if cached is not None:
        return cached
    results = db.query(
        func.date_trunc("month", Submission.submission_date).label("month"),
        func.count(Submission.submission_id).label("count")
    ).group_by("month").order_by("month").all()
    res_list = [{"month": str(r.month)[:7], "count": r.count} for r in results]
    analytics_cache.set("submissions_trend", res_list, ttl=30)
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
            -- Extract state abbreviation: last token of location if 2 chars, else full location
            CASE
                WHEN c.location IS NULL OR TRIM(c.location) = '' THEN 'Unknown'
                WHEN LENGTH(TRIM(SPLIT_PART(c.location, ',', -1))) = 2
                    THEN UPPER(TRIM(SPLIT_PART(c.location, ',', -1)))
                WHEN LENGTH(TRIM(SPLIT_PART(c.location, ' ', -1))) = 2
                    THEN UPPER(TRIM(SPLIT_PART(c.location, ' ', -1)))
                ELSE TRIM(c.location)
            END AS state_abbr
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        GROUP BY c.company_id, c.company_name, c.location, c.industry, c.website
        ORDER BY recruiter_count DESC, c.company_name ASC
    """)
    rows = db.execute(sql).mappings().all()
    res = []
    for row in rows:
        abbr = get_state_abbr(row["location"])
        if abbr == 'Unknown' and row["state_abbr"] and len(row["state_abbr"]) == 2:
            abbr = row["state_abbr"]
        res.append({
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "location": row["location"],
            "industry": row["industry"],
            "website": row["website"],
            "recruiter_count": int(row["recruiter_count"]),
            "state_abbr": abbr,
        })
    analytics_cache.set("companies_by_state", res, ttl=30)
    return res

@router.get("/companies-count-by-state")
def companies_count_by_state(db: Session = Depends(get_db)):
    cached = analytics_cache.get("companies_count_by_state")
    if cached is not None:
        return cached

    sql = text("""
        SELECT
            c.company_id,
            c.location AS company_location,
            string_agg(DISTINCT r.location, '|||') AS recruiter_locations
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        GROUP BY c.company_id, c.location
    """)
    rows = db.execute(sql).mappings().all()

    counts = {}
    for row in rows:
        resolved_abbrs = set()
        c_loc = row["company_location"]
        if c_loc:
            abbr = get_state_abbr(c_loc)
            if abbr and abbr != 'Unknown':
                resolved_abbrs.add(abbr)

        rec_locs_str = row["recruiter_locations"]
        if rec_locs_str:
            for p in rec_locs_str.split('|||'):
                if p:
                    abbr = get_state_abbr(p)
                    if abbr and abbr != 'Unknown':
                        resolved_abbrs.add(abbr)

        for abbr in resolved_abbrs:
            counts[abbr] = counts.get(abbr, 0) + 1

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
            string_agg(DISTINCT r.location, '|||') AS recruiter_locations,
            COUNT(*) OVER() AS full_count,
            CASE
                WHEN c.location IS NULL OR TRIM(c.location) = '' THEN 'Unknown'
                WHEN LENGTH(TRIM(SPLIT_PART(c.location, ',', -1))) = 2
                    THEN UPPER(TRIM(SPLIT_PART(c.location, ',', -1)))
                WHEN LENGTH(TRIM(SPLIT_PART(c.location, ' ', -1))) = 2
                    THEN UPPER(TRIM(SPLIT_PART(c.location, ' ', -1)))
                ELSE TRIM(c.location)
            END AS state_abbr
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        WHERE 1=1
    """
    params = {"limit": limit, "min_recruiters": min_recruiters, "skip": skip}

    if q:
        sql += " AND c.company_name ILIKE '%' || :q || '%'"
        params["q"] = q
    if state and state.upper() != "ALL":
        state_upper = state.upper()
        state_name = ABBR_TO_NAME.get(state_upper)
        sql += """ AND (
            (
                c.location ILIKE :state_pattern_1
                OR c.location ILIKE :state_pattern_2
                OR c.location ILIKE :state_pattern_3
                OR c.location ILIKE :state_pattern_4
                OR c.location ILIKE :state_pattern_5
            """
        if state_name:
            sql += " OR c.location ILIKE :name_pattern"
        sql += """
            )
            OR EXISTS (
                SELECT 1 FROM recruiters r2
                WHERE r2.company_id = c.company_id
                  AND (
                    r2.location ILIKE :state_pattern_1
                    OR r2.location ILIKE :state_pattern_2
                    OR r2.location ILIKE :state_pattern_3
                    OR r2.location ILIKE :state_pattern_4
                    OR r2.location ILIKE :state_pattern_5
                    """
        if state_name:
            sql += " OR r2.location ILIKE :name_pattern"
        sql += """
                  )
            )
        )"""
        params["state_pattern_1"] = f"% {state_upper}"
        params["state_pattern_2"] = f"% {state_upper},%"
        params["state_pattern_3"] = f"% {state_upper} %"
        params["state_pattern_4"] = f"{state_upper} %"
        params["state_pattern_5"] = state_upper
        if state_name:
            params["name_pattern"] = f"%{state_name}%"

    sql += """
        GROUP BY c.company_id, c.company_name, c.location, c.industry, c.website
        HAVING COUNT(DISTINCT r.recruiter_id) >= :min_recruiters
        ORDER BY recruiter_count DESC, c.company_name ASC
        LIMIT :limit OFFSET :skip
    """
    rows = db.execute(text(sql), params).mappings().all()
    
    total_count = rows[0]["full_count"] if rows and "full_count" in rows[0] else 0
    response.headers["X-Total-Count"] = str(total_count)
    
    res = []
    for row in rows:
        abbr = get_state_abbr(row["location"])
        if not abbr or abbr == 'Unknown':
            if row["state_abbr"] and len(row["state_abbr"]) == 2:
                abbr = row["state_abbr"]
        
        if not abbr or abbr == 'Unknown':
            rec_locs = row["recruiter_locations"]
            if rec_locs:
                parts = rec_locs.split('|||')
                resolved_abbrs = []
                for p in parts:
                    a = get_state_abbr(p)
                    if a and a != 'Unknown':
                        resolved_abbrs.append(a)
                if resolved_abbrs:
                    if state and state.upper() in resolved_abbrs:
                        abbr = state.upper()
                    else:
                        abbr = resolved_abbrs[0]
                        
        if (not abbr or abbr == 'Unknown') and state and state.upper() != "ALL":
            abbr = state.upper()
            
        res.append({
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "location": row["location"],
            "industry": row["industry"],
            "website": row["website"],
            "recruiter_count": int(row["recruiter_count"]),
            "state_abbr": abbr or 'Unknown',
        })
    return res


# ─── Visit Tracking ────────────────────────────────────────────────────────────

class VisitPayload(BaseModel):
    page: str
    path: str

@router.post("/log-visit")
def log_visit(payload: VisitPayload, db: Session = Depends(get_db)):
    visit = PageVisit(page=payload.page, path=payload.path)
    db.add(visit)
    db.commit()
    # Invalidate cache for visit stats so it updates immediately
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
