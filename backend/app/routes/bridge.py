from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import time
import os
import json
from ..database import get_db
from ..models.campaigns import EmailLog, EmailLogStatus

router = APIRouter()

class BridgeResult(BaseModel):
    log_id: int
    success: bool
    error: str = None

class BridgeResultsPayload(BaseModel):
    results: List[BridgeResult]

HEARTBEAT_FILE = "/tmp/bridge_heartbeat.txt"
if os.name == 'nt':
    HEARTBEAT_FILE = "C:\\Windows\\Temp\\bridge_heartbeat.txt"

@router.post("/heartbeat")
def bridge_heartbeat():
    """Register that the bridge is alive."""
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            f.write(str(time.time()))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/tasks")
def get_bridge_tasks(db: Session = Depends(get_db)):
    """Fetch pending emails for the bridge."""
    # We find emails that are 'sending' and assigned to 'outlook_bridge'
    # Wait, the send_engine creates EmailLog and sets status='sending' right before sending.
    logs = db.query(EmailLog).filter(
        EmailLog.status == EmailLogStatus.sending,
        EmailLog.sent_via == "outlook_bridge",
        EmailLog.outlook_accepted == None # Not processed yet
    ).order_by(EmailLog.log_id.asc()).limit(25).all()

    tasks = []
    for log in logs:
        # Prevent re-fetching the same task repeatedly if bridge crashes
        # We'll rely on the bridge to update outlook_accepted
        # Reset the timeout clock on dispatch so the sweep measures bridge time, not queue wait
        log.sending_at = _utcnow()
        tasks.append({
            "log_id": log.log_id,
            "to_email": log.recipient_email,
            "subject": log.subject,
            "html_body": log.body_html or log.body_preview
        })
    db.commit()
    return {"tasks": tasks}

from ..models.campaigns import EmailLog, EmailLogStatus, CampaignRecruiter, CampaignRecruiterStatus
from datetime import datetime

def _utcnow():
    return datetime.utcnow()

@router.post("/results")
def post_bridge_results(payload: BridgeResultsPayload, db: Session = Depends(get_db)):
    """Receive results from the bridge."""
    campaign_ids_to_check = set()
    for res in payload.results:
        log = db.query(EmailLog).filter(EmailLog.log_id == res.log_id).first()
        if log:
            campaign_ids_to_check.add(log.campaign_id)
            log.body_html = None  # Free the full-body payload once terminal (Supabase 500MB free tier)
            recipient = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == log.campaign_recruiter_id).first()
            if res.success:
                log.outlook_accepted = True
                log.status = EmailLogStatus.delivered.value
                log.delivered_at = _utcnow()
                if recipient:
                    recipient.status = CampaignRecruiterStatus.sent.value
                    recipient.last_sent_at = _utcnow()
                    recipient.sent_count += 1
            else:
                log.outlook_accepted = False
                log.status = EmailLogStatus.failed.value
                log.error_message = res.error
                log.failed_at = _utcnow()
                if recipient:
                    recipient.retry_count += 1
                    recipient.last_error = res.error
                    if recipient.retry_count >= recipient.max_retries:
                        recipient.status = CampaignRecruiterStatus.failed.value
                    else:
                        recipient.status = CampaignRecruiterStatus.retrying.value
    db.commit()
    
    from ..models.campaigns import Campaign, CampaignStatus
    for cid in campaign_ids_to_check:
        non_terminal = db.query(CampaignRecruiter).filter(
            CampaignRecruiter.campaign_id == cid,
            ~CampaignRecruiter.status.in_([
                CampaignRecruiterStatus.sent.value,
                CampaignRecruiterStatus.failed.value,
                CampaignRecruiterStatus.cancelled.value,
                CampaignRecruiterStatus.delivered.value,
                CampaignRecruiterStatus.opened.value,
                CampaignRecruiterStatus.replied.value,
                CampaignRecruiterStatus.bounced.value
            ])
        ).count()
        if non_terminal == 0:
            campaign = db.query(Campaign).filter(Campaign.campaign_id == cid).first()
            if campaign and campaign.status == CampaignStatus.active.value:
                campaign.status = CampaignStatus.completed.value
    db.commit()

    return {"status": "ok"}

