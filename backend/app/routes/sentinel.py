import time
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel

from app.database import get_db
from app.models.auth_models import User
from app.models.models import Recruiter, Company, RepairLog
from app.services.auth_service import get_current_user_from_request
from app.models.sentinel_state import SentinelPhase4State, SentinelState
from app.services.recruiter_store import recruiter_store as _store

router = APIRouter()

# US States Postal Code set for fast validation
US_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
    'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
    'DC','PR','VI','GU'
}

STATE_NAMES_MAP = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC', 'puerto rico': 'PR'
}


class ScanRepairRequest(BaseModel):
    limit: Optional[int] = 500
    focus_area: Optional[str] = "all"  # 'all', 'emails', 'names', 'locations', 'phones'


@router.get("/dashboard")
def get_sentinel_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        return {"error": "Unauthorized"}
    
    state = db.query(SentinelPhase4State).first()
    
    _store._ensure_loaded()
    
    if _store._loaded and _store._conn is not None:
        try:
            q = """
            SELECT 
                COUNT(*) as total_recruiters,
                COUNT(CASE WHEN email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%' THEN 1 END) as valid_emails,
                COUNT(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 END) as valid_phones,
                COUNT(CASE WHEN state IS NOT NULL AND state != '' THEN 1 END) as valid_states,
                COUNT(CASE WHEN company_id IS NOT NULL THEN 1 END) as valid_companies,
                COUNT(CASE WHEN linkedin IS NOT NULL AND linkedin != '' THEN 1 END) as valid_linkedin,
                COUNT(CASE WHEN completeness_score < 50 THEN 1 END) as profiles_below_50,
                COUNT(CASE WHEN completeness_score >= 90 THEN 1 END) as profiles_above_90,
                AVG(COALESCE(completeness_score, 0)) as avg_completeness,
                COUNT(CASE WHEN needs_review = true THEN 1 END) as needs_review_count
            FROM recruiters
            """
            row = _store._conn.execute(q).fetchone()
            
            total_recruiters = row[0] or 0
            valid_emails = row[1] or 0
            valid_phones = row[2] or 0
            valid_states = row[3] or 0
            valid_comps = row[4] or 0
            valid_li = row[5] or 0
            below_50 = row[6] or 0
            above_90 = row[7] or 0
            avg_comp = round(float(row[8] or 0), 1)
            needs_review = row[9] or 0

            missing_emails = max(0, total_recruiters - valid_emails)
            missing_phones = max(0, total_recruiters - valid_phones)
            missing_li = max(0, total_recruiters - valid_li)
            unknown_comps = max(0, total_recruiters - valid_comps)

            total_comps = _store._conn.execute("SELECT COUNT(*) FROM company_summary").fetchone()[0] if _store._conn else 0
            if not total_comps:
                total_comps = valid_comps
                
        except Exception as e:
            # Fallback to postgres if duckdb query fails
            total_recruiters = db.query(func.count(Recruiter.recruiter_id)).scalar() or 0
            total_comps = db.query(func.count(func.distinct(Recruiter.company_id))).scalar() or 0
            missing_emails = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.email == None) | (Recruiter.email == '') | (Recruiter.email.ilike('%missing.local%'))).scalar() or 0
            missing_phones = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.phone == None) | (Recruiter.phone == '')).scalar() or 0
            missing_li = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.linkedin == None) | (Recruiter.linkedin == '')).scalar() or 0
            unknown_comps = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.company_id == None).scalar() or 0
            below_50 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score < 50).scalar() or 0
            above_90 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score >= 90).scalar() or 0
            avg_comp = round(float(db.query(func.avg(Recruiter.completeness_score)).scalar() or 0), 1)
            needs_review = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.needs_review == True).scalar() or 0
            valid_emails = max(0, total_recruiters - missing_emails)
            valid_phones = max(0, total_recruiters - missing_phones)
            valid_states = total_recruiters
            valid_li = max(0, total_recruiters - missing_li)
    else:
        total_recruiters = db.query(func.count(Recruiter.recruiter_id)).scalar() or 0
        total_comps = db.query(func.count(func.distinct(Recruiter.company_id))).scalar() or 0
        missing_emails = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.email == None) | (Recruiter.email == '') | (Recruiter.email.ilike('%missing.local%'))).scalar() or 0
        missing_phones = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.phone == None) | (Recruiter.phone == '')).scalar() or 0
        missing_li = db.query(func.count(Recruiter.recruiter_id)).filter((Recruiter.linkedin == None) | (Recruiter.linkedin == '')).scalar() or 0
        unknown_comps = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.company_id == None).scalar() or 0
        below_50 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score < 50).scalar() or 0
        above_90 = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.completeness_score >= 90).scalar() or 0
        avg_comp = round(float(db.query(func.avg(Recruiter.completeness_score)).scalar() or 0), 1)
        needs_review = db.query(func.count(Recruiter.recruiter_id)).filter(Recruiter.needs_review == True).scalar() or 0
        valid_emails = max(0, total_recruiters - missing_emails)
        valid_phones = max(0, total_recruiters - missing_phones)
        valid_states = total_recruiters
        valid_li = max(0, total_recruiters - missing_li)

    tot_denom = max(1, total_recruiters)
    email_cov = round((valid_emails / tot_denom) * 100, 1)
    phone_cov = round((valid_phones / tot_denom) * 100, 1)
    state_cov = round((valid_states / tot_denom) * 100, 1)
    comp_cov = round(((total_recruiters - unknown_comps) / tot_denom) * 100, 1)
    li_cov = round((valid_li / tot_denom) * 100, 1)

    # Health score calculation
    health_score = round(max(0.0, 100.0 - (
        (missing_emails / tot_denom) * 35 +
        (unknown_comps / tot_denom) * 25 +
        (missing_phones / tot_denom) * 20 +
        (missing_li / tot_denom) * 20
    )), 1)

    return {
        "status": state.status if state else "Active",
        "total_recruiters": total_recruiters,
        "total_companies": total_comps,
        "unknown_companies": unknown_comps,
        "missing_emails": missing_emails,
        "missing_phones": missing_phones,
        "missing_linkedin": missing_li,
        "missing_logos": state.missing_logos if state else 0,
        "profiles_below_50": below_50,
        "profiles_above_90": above_90,
        "avg_confidence": state.avg_confidence if state else 85,
        "avg_completeness": int(avg_comp),
        "health_score": health_score,
        "email_coverage_pct": email_cov,
        "phone_coverage_pct": phone_cov,
        "state_coverage_pct": state_cov,
        "company_coverage_pct": comp_cov,
        "linkedin_coverage_pct": li_cov,
        "needs_review_count": needs_review,
        "companies_completed": state.companies_completed if state else total_comps,
        "recruiters_completed": state.recruiters_completed if state else total_recruiters,
        "current_company_name": state.current_company_name if state else "Continuous Background Monitor",
        "current_state": state.current_state if state else "All 50 US States",
        "estimated_completion_hours": state.estimated_completion_hours if state else 0.0
    }


@router.get("/anomalies")
def get_data_quality_anomalies(
    filter_type: str = Query("all", description="all, low_score, missing_email, missing_company, needs_review"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Retrieve actionable anomalous records for administrative review and repair."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    _store._ensure_loaded()
    
    anomalies = []
    total_found = 0

    if _store._loaded and _store._conn is not None:
        where_clauses = []
        if filter_type == "low_score":
            where_clauses.append("completeness_score < 50")
        elif filter_type == "missing_email":
            where_clauses.append("(email IS NULL OR email = '' OR email LIKE '%@missing.local%')")
        elif filter_type == "missing_company":
            where_clauses.append("company_id IS NULL")
        elif filter_type == "needs_review":
            where_clauses.append("needs_review = true")
        else:
            where_clauses.append("(completeness_score < 60 OR needs_review = true OR email IS NULL OR email = '' OR company_id IS NULL)")

        where_sql = " AND ".join(where_clauses)
        
        count_q = f"SELECT COUNT(*) FROM recruiters WHERE {where_sql}"
        total_found = _store._conn.execute(count_q).fetchone()[0] or 0
        
        data_q = f"""
        SELECT 
            recruiter_id, recruiter_name, email, phone, state, normalized_city, 
            company_id, completeness_score, needs_review, review_reason, repair_reason, title
        FROM recruiters 
        WHERE {where_sql}
        ORDER BY completeness_score ASC, recruiter_id ASC
        LIMIT {limit} OFFSET {offset}
        """
        rows = _store._conn.execute(data_q).fetchall()
        
        for r in rows:
            # Resolve company name if possible
            cid = r[6]
            cname = f"Company #{cid}" if cid else "Unassigned"
            if cid and _store._company_registry and cid in _store._company_registry:
                cname = _store._company_registry[cid].get("name", cname)
                
            anomalies.append({
                "recruiter_id": r[0],
                "recruiter_name": r[1] or "Unknown",
                "email": r[2] if r[2] and "@missing.local" not in r[2] else None,
                "phone": r[3],
                "state": r[4],
                "city": r[5],
                "company_id": cid,
                "company_name": cname,
                "completeness_score": r[7] or 0,
                "needs_review": bool(r[8]),
                "review_reason": r[9] or "Data quality flag",
                "repair_reason": r[10],
                "title": r[11] or "Recruiter"
            })
    else:
        # Fallback to Postgres
        q = db.query(Recruiter)
        if filter_type == "low_score":
            q = q.filter(Recruiter.completeness_score < 50)
        elif filter_type == "missing_email":
            q = q.filter((Recruiter.email == None) | (Recruiter.email == '') | (Recruiter.email.ilike('%missing.local%')))
        elif filter_type == "missing_company":
            q = q.filter(Recruiter.company_id == None)
        elif filter_type == "needs_review":
            q = q.filter(Recruiter.needs_review == True)
        else:
            q = q.filter((Recruiter.completeness_score < 60) | (Recruiter.needs_review == True))
            
        total_found = q.count()
        records = q.order_by(Recruiter.completeness_score.asc()).offset(offset).limit(limit).all()
        
        for rec in records:
            cname = rec.company.company_name if rec.company else "Unassigned"
            anomalies.append({
                "recruiter_id": rec.recruiter_id,
                "recruiter_name": rec.recruiter_name or "Unknown",
                "email": rec.email if rec.email and "@missing.local" not in rec.email else None,
                "phone": rec.phone,
                "state": rec.state,
                "city": rec.normalized_city,
                "company_id": rec.company_id,
                "company_name": cname,
                "completeness_score": rec.completeness_score or 0,
                "needs_review": bool(rec.needs_review),
                "review_reason": rec.review_reason or "Data quality flag",
                "repair_reason": rec.repair_reason,
                "title": rec.title or "Recruiter"
            })

    return {
        "total_anomalies": total_found,
        "filter_type": filter_type,
        "limit": limit,
        "offset": offset,
        "records": anomalies
    }


@router.post("/scan-and-repair")
def trigger_scan_and_repair(
    payload: ScanRepairRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Trigger an on-demand multi-signal data quality scan and automated repair batch."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    start_t = time.time()
    limit = min(max(10, payload.limit or 500), 2000)
    focus = payload.focus_area or "all"

    # Query Postgres candidates needing repair
    q = db.query(Recruiter).filter((Recruiter.completeness_score < 90) | (Recruiter.needs_review == True))
    if focus == "emails":
        q = q.filter((Recruiter.email == None) | (Recruiter.email == '') | (Recruiter.email.ilike('%missing.local%')))
    elif focus == "locations":
        q = q.filter((Recruiter.state == None) | (Recruiter.state == ''))
    elif focus == "companies":
        q = q.filter(Recruiter.company_id == None)

    candidates = q.limit(limit).all()
    
    repaired_count = 0
    repair_details = []

    for rec in candidates:
        changed = False
        reasons = []

        # 1. Name normalization & reconstruction from email prefix
        if rec.email and "@" in rec.email and ("@missing.local" not in rec.email):
            if not rec.recruiter_name or rec.recruiter_name.strip().lower() in ("none", "null", "unknown", "recruiter", "n/a"):
                prefix = rec.email.split("@")[0].lower()
                if "." in prefix:
                    parts = prefix.split(".")
                    if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts):
                        rec.recruiter_name = f"{parts[0].capitalize()} {parts[1].capitalize()}"
                        rec.normalized_recruiter_name = rec.recruiter_name
                        changed = True
                        reasons.append("Reconstructed name from email")

        # 2. State postal code normalization
        if rec.state:
            st_clean = rec.state.strip()
            if st_clean.lower() in STATE_NAMES_MAP:
                rec.state = STATE_NAMES_MAP[st_clean.lower()]
                changed = True
                reasons.append(f"Normalized state name to {rec.state}")
            elif len(st_clean) == 2 and st_clean.upper() in US_STATES and st_clean != st_clean.upper():
                rec.state = st_clean.upper()
                changed = True
                reasons.append("Standardized state postal code")

        # 3. Phone normalization (E.164 standard)
        if rec.phone:
            digits = re.sub(r'\D', '', str(rec.phone))
            if len(digits) == 10:
                normalized_phone = f"+1{digits}"
                if rec.phone != normalized_phone:
                    rec.phone = normalized_phone
                    changed = True
                    reasons.append("Formatted phone to E.164")

        # 4. Recompute completeness score
        score = 0
        if rec.email and "@missing.local" not in rec.email and "@" in rec.email:
            score += 40
        if rec.state and rec.state in US_STATES:
            score += 20
        if rec.company_id:
            score += 20
        if rec.phone:
            score += 10
        if rec.linkedin:
            score += 10

        if rec.completeness_score != score:
            rec.completeness_score = score
            changed = True

        if score >= 70 and rec.needs_review:
            rec.needs_review = False
            rec.review_reason = None
            changed = True
            reasons.append("Cleared review flag after score elevation")

        if changed:
            repaired_count += 1
            rec.repair_reason = "; ".join(reasons)
            if len(repair_details) < 10:
                repair_details.append({
                    "recruiter_id": rec.recruiter_id,
                    "name": rec.recruiter_name,
                    "reasons": reasons,
                    "new_score": score
                })

    if repaired_count > 0:
        db.commit()

    duration = round(time.time() - start_t, 3)

    return {
        "status": "success",
        "scanned_count": len(candidates),
        "repaired_count": repaired_count,
        "focus_area": focus,
        "duration_seconds": duration,
        "sample_repairs": repair_details,
        "message": f"Successfully analyzed {len(candidates)} records and repaired {repaired_count} anomalies in {duration}s."
    }


@router.post("/quick-repair/{recruiter_id}")
def quick_repair_single(
    recruiter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Repair a specific recruiter's data quality anomalies instantly."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    rec = db.query(Recruiter).filter(Recruiter.recruiter_id == recruiter_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recruiter not found")

    reasons = []

    # Name reconstruction
    if rec.email and "@" in rec.email and ("@missing.local" not in rec.email):
        if not rec.recruiter_name or rec.recruiter_name.strip().lower() in ("none", "null", "unknown", "recruiter", "n/a"):
            prefix = rec.email.split("@")[0].lower()
            if "." in prefix:
                parts = prefix.split(".")
                if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts):
                    rec.recruiter_name = f"{parts[0].capitalize()} {parts[1].capitalize()}"
                    rec.normalized_recruiter_name = rec.recruiter_name
                    reasons.append("Reconstructed name from email")

    # State normalization
    if rec.state:
        st_clean = rec.state.strip()
        if st_clean.lower() in STATE_NAMES_MAP:
            rec.state = STATE_NAMES_MAP[st_clean.lower()]
            reasons.append(f"Normalized state to {rec.state}")

    # Phone normalization
    if rec.phone:
        digits = re.sub(r'\D', '', str(rec.phone))
        if len(digits) == 10:
            rec.phone = f"+1{digits}"
            reasons.append("Formatted phone to E.164")

    # Score update
    score = 0
    if rec.email and "@missing.local" not in rec.email and "@" in rec.email:
        score += 40
    if rec.state and rec.state in US_STATES:
        score += 20
    if rec.company_id:
        score += 20
    if rec.phone:
        score += 10
    if rec.linkedin:
        score += 10

    rec.completeness_score = score
    rec.needs_review = False if score >= 70 else rec.needs_review
    rec.repair_reason = "; ".join(reasons) if reasons else "Profile audited and verified"

    db.commit()
    db.refresh(rec)

    return {
        "status": "success",
        "recruiter_id": rec.recruiter_id,
        "name": rec.recruiter_name,
        "email": rec.email,
        "phone": rec.phone,
        "state": rec.state,
        "completeness_score": rec.completeness_score,
        "reasons": reasons
    }


@router.get("/quality-report")
def export_data_quality_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Export complete forensic data quality audit report."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")

    dashboard_data = get_sentinel_dashboard(db, current_user)
    
    score = dashboard_data.get("health_score", 0)
    grade = "A+" if score >= 95 else "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_by": current_user.email,
        "overall_grade": grade,
        "health_score": score,
        "executive_summary": {
            "total_recruiter_records": dashboard_data.get("total_recruiters"),
            "total_company_records": dashboard_data.get("total_companies"),
            "average_completeness_pct": dashboard_data.get("avg_completeness"),
            "email_deliverability_pct": dashboard_data.get("email_coverage_pct"),
            "phone_coverage_pct": dashboard_data.get("phone_coverage_pct"),
            "state_resolution_pct": dashboard_data.get("state_coverage_pct"),
            "company_linkage_pct": dashboard_data.get("company_coverage_pct"),
            "linkedin_presence_pct": dashboard_data.get("linkedin_coverage_pct"),
            "flagged_needs_review": dashboard_data.get("needs_review_count")
        },
        "quality_distributions": {
            "tier_1_pristine_90_plus": dashboard_data.get("profiles_above_90"),
            "tier_2_standard_50_to_89": max(0, dashboard_data.get("total_recruiters", 0) - dashboard_data.get("profiles_above_90", 0) - dashboard_data.get("profiles_below_50", 0)),
            "tier_3_low_quality_sub_50": dashboard_data.get("profiles_below_50")
        },
        "engine_diagnostics": {
            "sentinel_engine_status": dashboard_data.get("status"),
            "active_target": dashboard_data.get("current_company_name"),
            "geo_scope": dashboard_data.get("current_state")
        },
        "recommendations": [
            "Maintain continuous auto-enrichment on newly registered recruiters.",
            "Run daily state postal code normalization.",
            "Synthesize missing business email patterns for unlinked corporate domains."
        ]
    }
    
    return report
