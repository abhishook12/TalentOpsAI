"""
Admin Terminal API
All endpoints require the X-Admin-Token header = ADMIN_SECRET_KEY (default: talentops-admin-1012)
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db
from app.models.models import Recruiter, Company, Candidate, Submission, Vendor, PageVisit
from datetime import datetime, timedelta
from collections import defaultdict
import time

router = APIRouter()

ADMIN_SECRET = "talentops-admin-1012"


def verify_admin(x_admin_token: Optional[str] = Header(None)):
    if x_admin_token != ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token."
        )


# ── 1. Live database stats ────────────────────────────────────────────────────
@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _=Depends(verify_admin)):
    t0 = time.time()
    rows = db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM recruiters)  AS total_recruiters,
            (SELECT COUNT(*) FROM recruiters WHERE is_active = true) AS active_recruiters,
            (SELECT COUNT(*) FROM recruiters WHERE email IS NOT NULL AND email <> '') AS with_email,
            (SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL AND phone <> '') AS with_phone,
            (SELECT COUNT(*) FROM companies)   AS total_companies,
            (SELECT COUNT(*) FROM candidates)  AS total_candidates,
            (SELECT COUNT(*) FROM submissions) AS total_submissions,
            (SELECT COUNT(*) FROM vendors)     AS total_vendors,
            (SELECT COUNT(*) FROM recruiters WHERE created_at >= NOW() - INTERVAL '24 hours') AS added_today,
            (SELECT COUNT(*) FROM recruiters WHERE created_at >= NOW() - INTERVAL '7 days')  AS added_week,
            (SELECT COUNT(DISTINCT location) FROM recruiters WHERE location IS NOT NULL AND location <> '') AS unique_locations,
            (SELECT COUNT(DISTINCT company_id) FROM recruiters WHERE company_id IS NOT NULL) AS recruiters_linked_to_company
    """)).mappings().one()
    elapsed = round((time.time() - t0) * 1000, 1)
    return {**dict(rows), "query_ms": elapsed}


# ── 2. Top states by recruiter count ─────────────────────────────────────────
@router.get("/top-states")
def admin_top_states(limit: int = 15, db: Session = Depends(get_db), _=Depends(verify_admin)):
    rows = db.execute(text("""
        SELECT
            TRIM(SPLIT_PART(location, ',', -1)) AS state,
            COUNT(*) AS count
        FROM recruiters
        WHERE location IS NOT NULL AND TRIM(location) <> ''
        GROUP BY state
        ORDER BY count DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


# ── 3. Recent imports ─────────────────────────────────────────────────────────
@router.get("/recent-imports")
def admin_recent_imports(limit: int = 20, db: Session = Depends(get_db), _=Depends(verify_admin)):
    rows = db.execute(text("""
        SELECT
            DATE(created_at) AS import_date,
            COUNT(*) AS count
        FROM recruiters
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY import_date DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return [dict(r) for r in rows]


# ── 4. Duplicate detector (by email) ─────────────────────────────────────────
@router.get("/duplicates")
def admin_duplicates(limit: int = 50, db: Session = Depends(get_db), _=Depends(verify_admin)):
    rows = db.execute(text("""
        SELECT
            LOWER(TRIM(email)) AS email,
            COUNT(*) AS count,
            array_agg(recruiter_id ORDER BY recruiter_id) AS ids,
            array_agg(name ORDER BY recruiter_id) AS names
        FROM recruiters
        WHERE email IS NOT NULL AND TRIM(email) <> ''
        GROUP BY LOWER(TRIM(email))
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    result = []
    for r in rows:
        result.append({
            "email": r["email"],
            "count": r["count"],
            "ids": list(r["ids"]),
            "names": list(r["names"]),
        })
    return {"total_duplicate_groups": len(result), "duplicates": result}


# ── 5. Empty-field audit ──────────────────────────────────────────────────────
@router.get("/field-audit")
def admin_field_audit(db: Session = Depends(get_db), _=Depends(verify_admin)):
    total = db.query(Recruiter).count()
    if total == 0:
        return {}
    rows = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE name IS NULL OR name = '')     AS missing_name,
            COUNT(*) FILTER (WHERE email IS NULL OR email = '')   AS missing_email,
            COUNT(*) FILTER (WHERE phone IS NULL OR phone = '')   AS missing_phone,
            COUNT(*) FILTER (WHERE company_id IS NULL)            AS missing_company,
            COUNT(*) FILTER (WHERE location IS NULL OR location = '') AS missing_location,
            COUNT(*) FILTER (WHERE title IS NULL OR title = '')   AS missing_title
        FROM recruiters
    """)).mappings().one()
    return {
        "total": total,
        "fields": {
            k: {"missing": v, "pct": round(v / total * 100, 1)}
            for k, v in rows.items()
        }
    }


# ── 6. Table sizes ────────────────────────────────────────────────────────────
@router.get("/table-sizes")
def admin_table_sizes(db: Session = Depends(get_db), _=Depends(verify_admin)):
    rows = db.execute(text("""
        SELECT
            relname AS table_name,
            pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
            pg_total_relation_size(relid) AS size_bytes,
            n_live_tup AS live_rows
        FROM pg_stat_user_tables
        ORDER BY size_bytes DESC
    """)).mappings().all()
    return [dict(r) for r in rows]


# ── 7. Companies without recruiter ───────────────────────────────────────────
@router.get("/orphan-companies")
def admin_orphan_companies(limit: int = 50, db: Session = Depends(get_db), _=Depends(verify_admin)):
    rows = db.execute(text("""
        SELECT c.company_id, c.company_name, c.location, c.website
        FROM companies c
        LEFT JOIN recruiters r ON r.company_id = c.company_id
        WHERE r.recruiter_id IS NULL
        ORDER BY c.company_name ASC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return {"count": len(rows), "companies": [dict(r) for r in rows]}


# ── 8. Cache clear ────────────────────────────────────────────────────────────
@router.post("/clear-cache")
def admin_clear_cache(_=Depends(verify_admin)):
    from app.routes.analytics import analytics_cache
    analytics_cache._cache.clear()
    return {"status": "ok", "message": "Analytics cache cleared."}


# ── 9. Read-only SQL console ──────────────────────────────────────────────────
from pydantic import BaseModel

class SqlQuery(BaseModel):
    sql: str

BLOCKED = ["drop ", "delete ", "update ", "insert ", "alter ", "create ", "truncate ", "grant ", "revoke "]

@router.post("/sql")
def admin_sql(body: SqlQuery, db: Session = Depends(get_db), _=Depends(verify_admin)):
    sql_lower = body.sql.strip().lower()
    if not sql_lower.startswith("select"):
        raise HTTPException(400, "Only SELECT statements are allowed.")
    for kw in BLOCKED:
        if kw in sql_lower:
            raise HTTPException(400, f"Blocked keyword: {kw.strip()}")
    if len(body.sql) > 2000:
        raise HTTPException(400, "Query too long (max 2000 chars).")
    try:
        t0 = time.time()
        result = db.execute(text(body.sql))
        rows = result.mappings().all()
        elapsed = round((time.time() - t0) * 1000, 1)
        columns = list(rows[0].keys()) if rows else []
        return {
            "columns": columns,
            "rows": [dict(r) for r in rows[:200]],
            "total": len(rows),
            "query_ms": elapsed,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


# ── 10. System info ───────────────────────────────────────────────────────────
@router.get("/system-info")
def admin_system_info(db: Session = Depends(get_db), _=Depends(verify_admin)):
    pg_ver = db.execute(text("SELECT version()")).scalar()
    db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    uptime = db.execute(text("SELECT date_trunc('second', now() - pg_postmaster_start_time())")).scalar()
    connections = db.execute(text("SELECT count(*) FROM pg_stat_activity")).scalar()
    slow_queries = db.execute(text("""
        SELECT count(*) FROM pg_stat_activity
        WHERE state = 'active'
        AND now() - query_start > interval '5 seconds'
    """)).scalar()
    return {
        "postgres_version": pg_ver,
        "database_size": db_size,
        "uptime": str(uptime),
        "active_connections": connections,
        "slow_queries": slow_queries,
    }


# ── 11. Visitor Log Book ──────────────────────────────────────────────────────

def _browser_from_ua(ua: str) -> str:
    if not ua:
        return "Unknown"
    if "Edg/" in ua:
        return "Edge"
    if "Chrome/" in ua:
        return "Chrome"
    if "Firefox/" in ua:
        return "Firefox"
    if "Safari/" in ua:
        return "Safari"
    if "curl" in ua:
        return "cURL"
    if "python" in ua.lower():
        return "Python"
    return "Unknown"


@router.get("/visitor-logs")
def admin_visitor_logs(
    days: int = 7,
    limit: int = 200,
    db: Session = Depends(get_db),
    _=Depends(verify_admin)
):
    """
    Returns visitor sessions grouped in Python (reliable across all visit rows).
    """
    since = datetime.utcnow() - timedelta(days=max(1, days))
    visits = (
        db.query(PageVisit)
        .filter(PageVisit.visited_at >= since)
        .order_by(PageVisit.visited_at.asc())
        .limit(5000)
        .all()
    )

    groups = {}
    for v in visits:
        sid = (v.session_id or "").strip()
        if not sid:
            day = v.visited_at.date().isoformat() if v.visited_at else "unknown"
            sid = f"legacy-{v.ip_address or 'unknown'}-{day}"
        if sid not in groups:
            ua = v.user_agent or ""
            groups[sid] = {
                "session_id": sid,
                "user_email": v.user_email or "Anonymous",
                "ip_address": v.ip_address or "—",
                "browser": _browser_from_ua(ua),
                "user_agent": ua[:120],
                "pages": [],
                "paths": [],
                "timestamps": [],
                "times_on_page": [],
                "page_count": 0,
                "total_seconds": 0,
                "session_start": v.visited_at,
                "session_end": v.visited_at,
            }
        g = groups[sid]
        g["pages"].append(v.page)
        g["paths"].append(v.path)
        g["timestamps"].append(str(v.visited_at) if v.visited_at else "")
        g["times_on_page"].append(int(v.time_on_page or 0))
        g["page_count"] += 1
        g["total_seconds"] += int(v.time_on_page or 0)
        if v.visited_at and (not g["session_start"] or v.visited_at < g["session_start"]):
            g["session_start"] = v.visited_at
        if v.visited_at and (not g["session_end"] or v.visited_at > g["session_end"]):
            g["session_end"] = v.visited_at
        if v.user_email:
            g["user_email"] = v.user_email

    sessions = sorted(groups.values(), key=lambda x: x["session_end"] or datetime.min, reverse=True)[:limit]
    for s in sessions:
        s["session_start"] = str(s["session_start"])
        s["session_end"] = str(s["session_end"])

    return {
        "sessions": sessions,
        "total": len(sessions),
        "total_visits": len(visits),
    }


@router.get("/visitor-summary")
def admin_visitor_summary(days: int = 30, db: Session = Depends(get_db), _=Depends(verify_admin)):
    """Daily unique visitors, total page views, avg session length."""
    rows = db.execute(text("""
        SELECT
            DATE(visited_at) AS day,
            COUNT(DISTINCT session_id) AS unique_sessions,
            COUNT(DISTINCT user_email) FILTER (WHERE user_email IS NOT NULL) AS unique_users,
            COUNT(*) AS page_views,
            ROUND(AVG(time_on_page) FILTER (WHERE time_on_page IS NOT NULL AND time_on_page > 0)) AS avg_page_seconds
        FROM page_visits
        WHERE visited_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY DATE(visited_at)
        ORDER BY day DESC
        LIMIT :days
    """), {"days": days}).mappings().all()

    top_pages = db.execute(text("""
        SELECT page, COUNT(*) AS views
        FROM page_visits
        WHERE visited_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY page
        ORDER BY views DESC
        LIMIT 10
    """), {"days": days}).mappings().all()

    top_users = db.execute(text("""
        SELECT
            user_email,
            COUNT(*) AS page_views,
            COUNT(DISTINCT session_id) AS sessions,
            MAX(visited_at) AS last_seen
        FROM page_visits
        WHERE user_email IS NOT NULL AND visited_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY user_email
        ORDER BY page_views DESC
        LIMIT 10
    """), {"days": days}).mappings().all()

    return {
        "daily": [dict(r) for r in rows],
        "top_pages": [dict(r) for r in top_pages],
        "top_users": [dict(r) for r in top_users],
    }


# ── DB Migration: add new columns to page_visits if not present ───────────────
def migrate_page_visits(db: Session):
    existing = db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'page_visits'
    """)).scalars().all()
    adds = []
    if "user_email"   not in existing: adds.append("ADD COLUMN user_email   VARCHAR(150)")
    if "session_id"   not in existing: adds.append("ADD COLUMN session_id   VARCHAR(64)")
    if "time_on_page" not in existing: adds.append("ADD COLUMN time_on_page INTEGER")
    if "user_agent"   not in existing: adds.append("ADD COLUMN user_agent   VARCHAR(300)")
    if "ip_address"   not in existing: adds.append("ADD COLUMN ip_address   VARCHAR(60)")
    if adds:
        db.execute(text(f"ALTER TABLE page_visits {', '.join(adds)}"))
        db.commit()
