import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import requests

from ..database import SessionLocal
from ..models.campaigns import Campaign, CampaignStatus, CampaignRecruiter, CampaignRecruiterStatus, EmailLog, EmailLogStatus
from .personalization import interpolate_variables

logger = logging.getLogger(__name__)

# Constants
BRIDGE_URL = "http://127.0.0.1:1337"
MIN_DELAY_SECONDS = 15
MAX_DELAY_SECONDS = 60

async def process_campaign_queue(campaign_id: int):
    """Background task to process a campaign's email queue."""
    logger.info(f"Starting queue processor for campaign {campaign_id}")
    
    # 1. Pre-flight check Outlook Bridge
    try:
        health = requests.get(f"{BRIDGE_URL}/health", timeout=5).json()
        if health.get("status") != "healthy":
            logger.error(f"Cannot start campaign {campaign_id}: Bridge unhealthy: {health.get('error')}")
            _set_campaign_status(campaign_id, CampaignStatus.failed.value)
            return
    except Exception as e:
        logger.error(f"Cannot start campaign {campaign_id}: Bridge unreachable: {e}")
        _set_campaign_status(campaign_id, CampaignStatus.failed.value)
        return

    while True:
        with SessionLocal() as db:
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found.")
                return
                
            if campaign.status != CampaignStatus.active.value:
                logger.info(f"Campaign {campaign_id} status is {campaign.status}. Stopping processor.")
                return
                
            # Get next pending or retrying recipient
            recipient = db.query(CampaignRecruiter).filter(
                CampaignRecruiter.campaign_id == campaign_id,
                CampaignRecruiter.status.in_([CampaignRecruiterStatus.pending.value, CampaignRecruiterStatus.failed.value])
            ).order_by(
                CampaignRecruiter.queue_position.asc(), 
                CampaignRecruiter.campaign_recruiter_id.asc()
            ).first()
            
            if not recipient:
                logger.info(f"Campaign {campaign_id} has no more pending recipients. Marking complete.")
                campaign.status = CampaignStatus.completed.value
                db.commit()
                return
                
            # Create EmailLog entry
            log = EmailLog(
                campaign_id=campaign_id,
                campaign_recruiter_id=recipient.campaign_recruiter_id,
                recipient_email=recipient.recruiter.email if recipient.recruiter else "unknown",
                recipient_name=recipient.recruiter.recruiter_name if recipient.recruiter else None,
                status=EmailLogStatus.sending.value,
                attempt_number=recipient.retry_count + 1,
                sending_at=datetime.now(timezone.utc),
                sent_via="outlook_bridge"
            )
            db.add(log)
            
            # Prepare email content
            subject_template = ""
            body_template = ""
            if campaign.sequence_steps:
                step = campaign.sequence_steps[0]
                if step.template:
                    subject_template = step.template.subject
                    body_template = step.template.body
            elif recipient.current_step and recipient.current_step.template:
                subject_template = recipient.current_step.template.subject
                body_template = recipient.current_step.template.body
            
            # Fallback if templates are missing but we need to send
            if not subject_template and not body_template:
                # Assuming draft might have set them directly on campaign?
                subject_template = campaign.name
            
            subject = interpolate_variables(subject_template, recipient.recruiter, recipient.recruiter.company if recipient.recruiter else None)
            body = interpolate_variables(body_template, recipient.recruiter, recipient.recruiter.company if recipient.recruiter else None)
            
            log.subject = subject
            log.body_preview = body[:200] if body else ""
            db.commit()
            
            rec_id = recipient.campaign_recruiter_id
            rec_email = recipient.recruiter.email
            
        # Send via Outlook Bridge (outside DB transaction)
        start_time = time.time()
        payload = {
            "to": rec_email,
            "subject": subject,
            "body": body,
            "from_email": campaign.from_email
        }
        
        success = False
        error_msg = None
        try:
            resp = requests.post(f"{BRIDGE_URL}/send-one", json=payload, timeout=30)
            result = resp.json()
            if result.get("success"):
                success = True
            else:
                error_msg = result.get("error")
        except Exception as e:
            error_msg = str(e)
            
        duration = int((time.time() - start_time) * 1000)
        
        # Update DB based on result
        with SessionLocal() as db:
            recipient = db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_recruiter_id == rec_id).first()
            log = db.query(EmailLog).filter(EmailLog.log_id == log.log_id).first()
            
            log.duration_ms = duration
            recipient.sent_via = "outlook_bridge"
            
            if success:
                log.status = EmailLogStatus.delivered.value
                log.delivered_at = datetime.now(timezone.utc)
                log.outlook_accepted = True
                
                recipient.status = CampaignRecruiterStatus.sent.value
                recipient.last_sent_at = datetime.now(timezone.utc)
                recipient.sent_count += 1
            else:
                log.status = EmailLogStatus.failed.value
                log.failed_at = datetime.now(timezone.utc)
                log.error_message = error_msg
                log.outlook_accepted = False
                
                recipient.retry_count += 1
                recipient.last_error = error_msg
                if recipient.retry_count >= recipient.max_retries:
                    recipient.status = CampaignRecruiterStatus.failed.value
                else:
                    recipient.status = CampaignRecruiterStatus.pending.value # Keep pending for retry
                    
            db.commit()

        # Random delay to mimic human (only if we have more to send and are still active)
        with SessionLocal() as db:
            campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
            if campaign and campaign.status == CampaignStatus.active.value:
                delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                logger.info(f"Waiting {delay} seconds before next email...")
                await asyncio.sleep(delay)

def _set_campaign_status(campaign_id: int, status: str):
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if campaign:
            campaign.status = status
            db.commit()

async def start_campaign(campaign_id: int):
    """Set campaign to active and start background processor."""
    _set_campaign_status(campaign_id, CampaignStatus.active.value)
    asyncio.create_task(process_campaign_queue(campaign_id))

def pause_campaign(campaign_id: int):
    """Set campaign to paused. The processor loop will exit after current email."""
    _set_campaign_status(campaign_id, CampaignStatus.paused.value)

async def resume_campaign(campaign_id: int):
    """Resume a paused campaign."""
    await start_campaign(campaign_id)
