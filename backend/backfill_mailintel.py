import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Add backend to path
sys.path.insert(0, os.path.abspath('C:\\TalentOpsAI\\backend'))

from app.database import SessionLocal
from app.models.campaigns import EmailLog, EmailLogStatus, CampaignRecruiter, CampaignRecruiterStatus
from app.models.models import RecruiterEmail
from app.services.mailintel_engine import process_delivery_event

def run_backfill():
    db = SessionLocal()
    print("Starting MAILINTEL historical backfill...")
    
    # 1. Process all EmailLogs that are Delivered or Failed
    logs = db.query(EmailLog).filter(
        or_(
            EmailLog.status == EmailLogStatus.delivered.value,
            EmailLog.status == EmailLogStatus.failed.value
        )
    ).all()
    
    processed = 0
    print(f"Found {len(logs)} terminal email logs to process.")
    for log in logs:
        if not log.recipient_email:
            continue
            
        event_type = None
        reason = None
        if log.status == EmailLogStatus.delivered.value:
            event_type = 'delivered'
        elif log.status == EmailLogStatus.failed.value:
            # check if it's a hard bounce vs soft
            err = (log.error_message or "").lower()
            if "permanent" in err or "550" in err or "not found" in err or "rejected" in err:
                event_type = 'hard_bounce'
            else:
                event_type = 'soft_bounce'
            reason = log.error_message
            
        if event_type:
            try:
                process_delivery_event(db, log.recipient_email, event_type, log.campaign_id, reason)
                processed += 1
            except Exception as e:
                print(f"Error processing log {log.log_id}: {e}")

    # 2. Process all CampaignRecruiters that have Bounced or Replied
    crs = db.query(CampaignRecruiter).filter(
        or_(
            CampaignRecruiter.status == CampaignRecruiterStatus.bounced.value,
            CampaignRecruiter.status == CampaignRecruiterStatus.replied.value
        )
    ).all()
    
    print(f"Found {len(crs)} historical recruiter states to process.")
    for cr in crs:
        # We need the recipient email. It's on RecruiterEmail via recruiter_id, but the user might have multiple.
        # We'll just look up the primary email or the one they sent to in EmailLog.
        log = db.query(EmailLog).filter(EmailLog.campaign_recruiter_id == cr.campaign_recruiter_id).first()
        if not log or not log.recipient_email:
            # Fallback to fetching recruiter's primary email
            rec_email = db.query(RecruiterEmail).filter(RecruiterEmail.recruiter_id == cr.recruiter_id).first()
            if rec_email:
                email = rec_email.email
            else:
                continue
        else:
            email = log.recipient_email
            
        event_type = None
        if cr.status == CampaignRecruiterStatus.replied.value:
            event_type = 'replied'
        elif cr.status == CampaignRecruiterStatus.bounced.value:
            event_type = 'hard_bounce'
            
        if event_type:
            try:
                process_delivery_event(db, email, event_type, cr.campaign_id, "Historical Sync")
                processed += 1
            except Exception as e:
                print(f"Error processing cr {cr.campaign_recruiter_id}: {e}")
                
    print(f"Backfill complete! Processed {processed} historical events.")

if __name__ == "__main__":
    run_backfill()
