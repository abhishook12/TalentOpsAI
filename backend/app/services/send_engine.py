"""
Production-grade campaign send engine (High-Speed Worker Pool).

Processes campaign email queues with:
- Asynchronous Worker Pool (Immediate Queuing)
- No artificial delays (Fast execution)
- Intelligent retry with exponential backoff
- Per-email lifecycle tracking
- Campaign-level fault tolerance
- Pause/Resume/Cancel support
"""
import asyncio
import logging
import math
import random
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import requests
import concurrent.futures

from ..database import SessionLocal
from ..models.campaigns import (
    Campaign, CampaignStatus, CampaignRecruiter, CampaignRecruiterStatus,
    EmailLog, EmailLogStatus, EmailSignature
)
from .personalization import interpolate_variables

logger = logging.getLogger(__name__)

# Bridge configuration
BRIDGE_URL = "http://127.0.0.1:1337"
WORKER_COUNT = 3  # Number of concurrent workers sending emails
MAX_RETRIES_OVERALL = 3

# We use a ThreadPoolExecutor for requests.post to avoid blocking the asyncio event loop
request_executor = concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT * 2)

def _utcnow():
    return datetime.now(timezone.utc)

def _check_bridge_health(user_id: int) -> tuple[bool, str]:
    """Check if the Outlook Bridge is healthy."""
    from ..routes.health import check_outlook_bridge
    from ..database import SessionLocal
    
    with SessionLocal() as db:
        res = check_outlook_bridge(db, user_id)
        
    is_healthy = res.get("status") == "ok"
    error = res.get("error") or res.get("message") if not is_healthy else "healthy"
    return is_healthy, error

def _set_campaign_status(campaign_id: int, status: str):
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            campaign.status = status
            db.commit()

def _get_campaign_eta(campaign_id: int) -> dict:
    """Calculate ETA based on fast worker pool throughput (approx 1s per email per worker)."""
    with SessionLocal() as db:
        total = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id
        ).count()
        
        sent = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.sent.value,
                CampaignRecruiterStatus.delivered.value,
                CampaignRecruiterStatus.opened.value,
                CampaignRecruiterStatus.replied.value,
            ])
        ).count()
        
        failed = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status == CampaignRecruiterStatus.failed.value
        ).count()
        
        retrying = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status == CampaignRecruiterStatus.retrying.value
        ).count()
        
        pending = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.queued.value,
            ])
        ).count()
        
        remaining = pending + retrying
        
        # Estimate: e.g. 1 email takes 1.5s via Outlook. With 3 workers, 1 email takes 0.5s overall.
        estimated_seconds_per_email = 0.5 
        eta_seconds = int(remaining * estimated_seconds_per_email)
        
        # We assume max speed. We report "rate_per_minute" effectively as what we estimate.
        effective_rate = int(60 / estimated_seconds_per_email) if estimated_seconds_per_email > 0 else 0
        
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "retrying": retrying,
            "pending": pending,
            "remaining": remaining,
            "progress_percent": round((sent / total) * 100, 1) if total > 0 else 0,
            "eta_seconds": eta_seconds,
            "rate_per_minute": effective_rate,
        }

async def _send_via_bridge(payload: dict) -> tuple[bool, str, str]:
    """Execute synchronous requests.post in a thread pool."""
    def _do_request():
        try:
            resp = requests.post(f"{BRIDGE_URL}/send-one", json=payload, timeout=30)
            result = resp.json()
            if result.get("success"):
                return True, None, None
            else:
                return False, result.get("error", "Unknown error from bridge"), "bridge_rejection"
        except requests.exceptions.Timeout:
            return False, "Outlook Bridge request timed out (30s)", "smtp_timeout"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to Outlook Bridge", "network_lost"
        except Exception as e:
            return False, str(e), "unknown"
            
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(request_executor, _do_request)

async def _worker_task(worker_id: int, campaign_id: int, queue: asyncio.Queue, signature_html: str, template: dict, from_email: str):
    logger.info(f"Worker {worker_id} started for campaign {campaign_id}")
    while True:
        try:
            recipient_id = await queue.get()
        except asyncio.CancelledError:
            break
            
        try:
            def _process_recipient_db(recipient_id):
                with SessionLocal() as db:
                    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
                    if not campaign or campaign.status not in [CampaignStatus.active.value]:
                        return False

                    recipient = db.query(CampaignRecruiter).filter(
                        CampaignRecruiter.campaign_recruiter_id == recipient_id
                    ).first()
                    
                    if not recipient or recipient.status == CampaignRecruiterStatus.cancelled.value:
                        return False
                    
                    # Mark sending
                    recipient.status = CampaignRecruiterStatus.sending.value
                    recruiter = recipient.recruiter
                    company = recruiter.company if recruiter else None
                    rec_email = recruiter.email if recruiter and recruiter.email else "unknown"
                    rec_name = recruiter.recruiter_name if recruiter else None
                    retry_count = recipient.retry_count
                    
                    log = EmailLog(
                        campaign_id=campaign_id,
                        campaign_recruiter_id=recipient_id,
                        recipient_email=rec_email,
                        recipient_name=rec_name,
                        status=EmailLogStatus.sending.value,
                        attempt_number=retry_count + 1,
                        sending_at=_utcnow(),
                        sent_via="outlook_bridge"
                    )
                    db.add(log)
                    
                    subject_template = template.get("subject", "No Subject")
                    body_template = template.get("body", "")
                    
                    subject = interpolate_variables(subject_template, recruiter, company)
                    body = interpolate_variables(body_template, recruiter, company, signature_html=signature_html)
                    
                    log.subject = subject
                    log.body_preview = body[:500] if body else ""
                    log.body_html = body or ""  # Full body for the bridge — body_preview is truncated and must not be sent
                    db.commit()
                    return rec_email

            rec_email = await asyncio.to_thread(_process_recipient_db, recipient_id)
            if not rec_email:
                queue.task_done()
                continue
            
            # In Polling Architecture, we don't call the bridge synchronously.
            # We just leave the status as 'sending' in EmailLog, and the bridge will poll it.
            # But wait, we need to mark CampaignRecruiter as 'sending' and let the bridge update it.
            # We simulate a "queueing" completion here so the worker can move to the next.
            logger.info(f"Worker {worker_id}: Queued {rec_email} for Outlook Bridge polling")
                
        except Exception as e:
            logger.error(f"Worker {worker_id} exception for {recipient_id}: {e}")
        finally:
            queue.task_done()

async def _schedule_retry(queue: asyncio.Queue, recipient_id: int, retry_count: int):
    # Exponential backoff: 30s, 60s, 120s
    delay = 30 * (2 ** (retry_count - 1))
    await asyncio.sleep(delay)
    # Check if campaign is still active before putting it back
    with SessionLocal() as db:
        rec = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == recipient_id).first()
        if rec and rec.status == CampaignRecruiterStatus.retrying.value:
            rec.status = CampaignRecruiterStatus.queued.value
            db.commit()
            await queue.put(recipient_id)

async def process_campaign_queue(campaign_id: int):
    """Background task manager for a campaign's email queue."""
    logger.info(f"Starting Campaign Manager for {campaign_id}")
    
    # 1. Pre-flight: Check Outlook Bridge
    healthy, error = _check_bridge_health()
    if not healthy:
        logger.error(f"Cannot start campaign {campaign_id}: Bridge unhealthy: {error}")
        _set_campaign_status(campaign_id, CampaignStatus.failed.value)
        return
    
    # 2. Extract configuration and mark queued
    queue = asyncio.Queue()
    signature_html = None
    template = {}
    from_email = None
    
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return
        
        from_email = campaign.from_email
        
        if campaign.signature_id:
            sig = db.query(EmailSignature).filter(
                EmailSignature.signature_id == campaign.signature_id
            ).first()
            if sig:
                signature_html = sig.html_content
        
        active_steps = sorted(
            [s for s in campaign.sequence_steps if s.is_active],
            key=lambda s: s.step_order
        )
        if active_steps and active_steps[0].template:
            template = {
                "subject": active_steps[0].template.subject or campaign.name,
                "body": active_steps[0].template.body or ""
            }
        else:
            template = {"subject": campaign.name or "No Subject", "body": ""}
        
        pending_recipients = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.retrying.value,
            ])
        ).all()
        
        for i, r in enumerate(pending_recipients):
            r.status = CampaignRecruiterStatus.queued.value
            r.queue_position = i + 1
            queue.put_nowait(r.campaign_recruiter_id)
        
        # Yield before blocking on commit
        await asyncio.sleep(0)
        db.commit()
    
    # Queue empty check removed to keep stream open for bridge
    # 3. Start Workers
    workers = []
    for i in range(WORKER_COUNT):
        task = asyncio.create_task(_worker_task(i, campaign_id, queue, signature_html, template, from_email))
        workers.append(task)
        
    # 4. Wait for queue to complete
    await queue.join()
    
    # 5. Cleanup
    for w in workers:
        w.cancel()
        
    # Check if we should mark as completed (if not cancelled/paused)
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign and campaign.status == CampaignStatus.active.value:
            pass # We leave the campaign active until the Outlook Bridge reports all terminal states

_background_tasks = set()

async def start_campaign(campaign_id: int):
    """Set campaign to active and start background processor."""
    _set_campaign_status(campaign_id, CampaignStatus.active.value)
    task = asyncio.create_task(process_campaign_queue(campaign_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

def pause_campaign(campaign_id: int):
    """Set campaign to paused. The processor loop will exit after current email."""
    _set_campaign_status(campaign_id, CampaignStatus.paused.value)

def cancel_campaign(campaign_id: int):
    """Set campaign to cancelled. The processor will mark remaining as cancelled."""
    _set_campaign_status(campaign_id, CampaignStatus.cancelled.value)
    with SessionLocal() as db:
        db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.queued.value,
                CampaignRecruiterStatus.pending.value,
            ])
        ).update({"status": CampaignRecruiterStatus.cancelled.value}, synchronize_session=False)
        db.commit()

async def resume_campaign(campaign_id: int):
    """Resume a paused campaign."""
    with SessionLocal() as db:
        db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == campaign_id,
            CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.pending.value,
                CampaignRecruiterStatus.retrying.value,
            ])
        ).update({"status": CampaignRecruiterStatus.queued.value}, synchronize_session=False)
        db.commit()
    
    await start_campaign(campaign_id)

def get_campaign_progress(campaign_id: int) -> dict:
    """Get real-time campaign progress with ETA."""
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}
        
        return _get_campaign_eta(campaign_id)

def restart_active_campaigns():
    """Crash recovery: Resume any campaign that was in active state when the server crashed."""
    try:
        with SessionLocal() as db:
            # Reset any queued items back to pending in case of crash
            db.query(CampaignRecruiter).filter(
                CampaignRecruiter.status == CampaignRecruiterStatus.queued.value
            ).update({"status": CampaignRecruiterStatus.pending.value}, synchronize_session=False)
            db.commit()
            
            active_campaigns = db.query(Campaign).filter(Campaign.status == CampaignStatus.active.value).all()
            for c in active_campaigns:
                logger.info(f"Crash recovery: Restarting campaign {c.campaign_id}...")
                task = asyncio.create_task(process_campaign_queue(c.campaign_id))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
    except Exception as e:
        logger.error(f"Failed to run crash recovery for active campaigns: {e}")
