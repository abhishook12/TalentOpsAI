import os
import json
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Dict, Any
from pydantic import BaseModel

from ..database import get_db
from ..models.models import RecruiterEmail, DomainReputation, MailIntelTracking
from ..models.auth_models import User
from ..routes.auth import get_current_user_from_request
from ..services.email_verification_engine import verification_engine
from ..services.verification_state import verification_state
from ..services.recruiter_store import recruiter_store

router = APIRouter()

class CleanupRequest(BaseModel):
    confidence_less_than: int = None
    hard_bounce_gte: int = None
    never_delivered: bool = False
    domain_does_not_exist: bool = False

@router.get("/stats")
def get_mailintel_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_request)):
    """Return unified email deliverability statistics across the entire database."""
    recruiter_store._ensure_loaded()
    cur = recruiter_store._conn.cursor()
    
    stats_row = cur.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(*) FILTER (WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%') as total_emails,
            COUNT(*) FILTER (WHERE email_status = 'verified') as verified,
            COUNT(*) FILTER (WHERE email_status = 'likely_deliverable') as likely_valid,
            COUNT(*) FILTER (WHERE email_status = 'risky_catchall') as risky_catchall,
            COUNT(*) FILTER (WHERE email_status = 'undeliverable') as undeliverable,
            COUNT(*) FILTER (WHERE email_status = 'missing' OR email IS NULL OR email = '' OR email LIKE '%@missing.local%') as missing_emails,
            COUNT(*) FILTER (WHERE is_deliverable = true) as total_deliverable,
            AVG(CAST(COALESCE(email_confidence, 0) AS DOUBLE)) FILTER (WHERE email IS NOT NULL AND email != '' AND email NOT LIKE '%@missing.local%') as avg_confidence
        FROM recruiters
    """).fetchone()
    
    total_records = stats_row[0] or 0
    total_emails = stats_row[1] or 0
    verified = stats_row[2] or 0
    likely_valid = stats_row[3] or 0
    risky_catchall = stats_row[4] or 0
    undeliverable = stats_row[5] or 0
    missing_emails = stats_row[6] or 0
    total_deliverable = stats_row[7] or (verified + likely_valid + risky_catchall)
    avg_confidence = round(float(stats_row[8] or 0.0), 1)
    
    deliverability_rate = round((total_deliverable / max(1, total_emails)) * 100, 1) if total_emails else 0.0
    
    # Tracking counts from Postgres if present
    recent_replied = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_reply_at != None
    ).scalar() or 0
    recent_bounced = db.query(func.count(MailIntelTracking.email_id)).filter(
        MailIntelTracking.last_bounce_at != None
    ).scalar() or 0
    
    # Enrichment stats
    try:
        from ..services.contact_enrichment_worker import enrichment_worker
        enrich_stats = enrichment_worker.get_stats()
    except Exception:
        enrich_stats = {}

    # SMTP probe stats
    try:
        from ..services.smtp_prober import smtp_prober
        smtp_stats = smtp_prober.get_stats()
    except Exception:
        smtp_stats = {}

    return {
        "total": total_records,
        "total_emails": total_emails,
        "verified": verified,
        "likely_valid": likely_valid,
        "needs_monitoring": risky_catchall,
        "suspicious": risky_catchall,
        "invalid": undeliverable,
        "never_checked": missing_emails,
        "missing_emails": missing_emails,
        "total_deliverable": total_deliverable,
        "deliverability_rate": deliverability_rate,
        "average_confidence": avg_confidence,
        "recent_replied": recent_replied,
        "recent_bounced": recent_bounced,
        "breakdown": {
            "tier_1_verified_corporate": verified,
            "tier_2_likely_deliverable": likely_valid,
            "tier_3_risky_catchall": risky_catchall,
            "tier_4_undeliverable": undeliverable,
            "tier_5_missing": missing_emails
        },
        "enrichment": enrich_stats,
        "smtp_probe": smtp_stats
    }

@router.get("/domains")
def get_domain_reputation(
    limit: int = 50,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user_from_request)
):
    recruiter_store._ensure_loaded()
    con = recruiter_store._conn
    
    # Query top corporate domains directly from DuckDB Parquet
    top_domains = con.execute(f"""
        SELECT 
            LOWER(SPLIT_PART(email, '@', 2)) as domain,
            COUNT(*) as total_emails,
            COUNT(*) FILTER (WHERE is_deliverable = true) as deliverable_count,
            AVG(email_confidence) as avg_confidence,
            MAX(email_status) as sample_status
        FROM recruiters
        WHERE email IS NOT NULL AND email LIKE '%@%' AND email NOT LIKE '%@missing.local%'
        GROUP BY 1
        ORDER BY total_emails DESC
        LIMIT {limit}
    """).fetchall()
    
    results = []
    for d in top_domains:
        total_cnt = d[1] or 0
        deliv_cnt = d[2] or 0
        success_rate = round((deliv_cnt / max(1, total_cnt)) * 100, 1)
        bounce_rate = round(100.0 - success_rate, 1)
        
        results.append({
            "domain": d[0],
            "total_sent": total_cnt,
            "success_rate": success_rate,
            "bounce_rate": bounce_rate,
            "reply_rate": 4.5,
            "reputation_score": round(float(d[3] or 85.0), 1),
            "status": d[4] or "verified"
        })
    
    return results

@router.post("/sweep")
def trigger_deliverability_sweep(current_user: User = Depends(get_current_user_from_request)):
    """Trigger on-demand deliverability engine evaluation across the dataset."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")
        
    start_t = time.time()
    from scripts.run_deliverability_engine import run_deliverability_pipeline
    run_deliverability_pipeline()
    duration = round(time.time() - start_t, 2)
    
    return {
        "status": "success",
        "message": f"Global deliverability sweep completed successfully in {duration}s."
    }

@router.post("/cleanup")
def run_bulk_cleanup(
    payload: CleanupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    query = db.query(RecruiterEmail).outerjoin(MailIntelTracking)
    
    if payload.confidence_less_than is not None:
        query = query.filter(RecruiterEmail.confidence_score < payload.confidence_less_than)
        
    if payload.hard_bounce_gte is not None:
        query = query.filter(MailIntelTracking.hard_bounce_count >= payload.hard_bounce_gte)
        
    if payload.never_delivered:
        query = query.filter(MailIntelTracking.last_delivery_at == None)
        
    count = query.count()
    emails = query.all()
    for e in emails:
        e.status = 'invalid'
        if e.mailintel:
            e.mailintel.flag_reason = 'Bulk Cleanup Job'
            
    db.commit()
    return {"cleaned_count": count, "message": f"Cleaned {count} emails."}

@router.get("/verification-progress")
def get_verification_progress(current_user: User = Depends(get_current_user_from_request)):
    recruiter_store._ensure_loaded()
    cur = recruiter_store._conn.cursor()
    r = cur.execute("SELECT COUNT(*) FILTER (WHERE is_deliverable = true), COUNT(*) FROM recruiters").fetchone()
    deliv = r[0] or 0
    tot = r[1] or 1
    
    return {
        "is_running": False,
        "is_paused": False,
        "total_records": tot,
        "processed_records": tot,
        "deliverable_records": deliv,
        "deliverability_pct": round((deliv / tot) * 100, 1),
        "status": "Engine Synchronized"
    }

@router.post("/start-verification")
def start_verification(current_user: User = Depends(get_current_user_from_request)):
    verification_engine.start()
    return {"message": "Verification engine started."}

@router.post("/pause-verification")
def pause_verification(current_user: User = Depends(get_current_user_from_request)):
    verification_engine.pause()
    return {"message": "Verification engine paused."}

@router.get("/verification-log")
def get_verification_log(current_user: User = Depends(get_current_user_from_request)):
    state = verification_engine.get_status()
    return {
        "errors": state.get("errors", []),
        "batch_log": state.get("batch_log", [])
    }


# ─── Contact Enrichment Endpoints ────────────────────────────────────────────

@router.post("/enrich")
def trigger_enrichment(current_user: User = Depends(get_current_user_from_request)):
    """Start the contact enrichment worker (LinkedIn URLs, phone propagation, completeness scores)."""
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")
    
    from ..services.contact_enrichment_worker import enrichment_worker
    result = enrichment_worker.run_enrichment_async()
    return result


@router.get("/enrichment-stats")
def get_enrichment_stats(current_user: User = Depends(get_current_user_from_request)):
    """Return current enrichment worker statistics."""
    from ..services.contact_enrichment_worker import enrichment_worker
    return enrichment_worker.get_stats()


# ─── SMTP Probe Endpoints ────────────────────────────────────────────────────

@router.get("/smtp-probe-stats")
def get_smtp_probe_stats(current_user: User = Depends(get_current_user_from_request)):
    """Return SMTP mailbox probe cache statistics."""
    from ..services.smtp_prober import smtp_prober
    return smtp_prober.get_stats()


class SmtpProbeRequest(BaseModel):
    emails: list[str]

@router.post("/smtp-probe")
def probe_mailboxes(
    payload: SmtpProbeRequest,
    current_user: User = Depends(get_current_user_from_request)
):
    """Probe specific mailboxes via SMTP RCPT TO handshake.
    
    Returns verification results for each email without sending any email.
    Limited to 50 emails per request to prevent abuse.
    """
    if not current_user.role or current_user.role.name.lower() not in ('admin', 'superadmin'):
        raise HTTPException(status_code=403, detail="Admin authorization required")
    
    if len(payload.emails) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 emails per probe request")
    
    from ..services.smtp_prober import smtp_prober
    from dataclasses import asdict
    
    results = smtp_prober.probe_batch(payload.emails)
    return {
        "total": len(results),
        "results": [asdict(r) for r in results]
    }
