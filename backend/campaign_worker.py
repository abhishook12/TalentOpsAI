import os
import sys
import time
import argparse
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_, and_, text
from app.database import SessionLocal
from app.models.campaigns import Campaign, CampaignRecruiter, CampaignRecruiterStatus, SequenceStep, EmailTemplate
from app.models.models import Recruiter, Company

load_dotenv()

def get_smtp_connection():
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        return None

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_pass)
    return server

def interpolate_variables(text_content, recruiter, company):
    if not text_content:
        return ""
    
    first_name = "there"
    last_name = ""
    
    if recruiter.recruiter_name and "Unknown" not in recruiter.recruiter_name:
        parts = recruiter.recruiter_name.split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]
            
    company_name = company.company_name if company and company.company_name else "your company"
    
    # Safe replacements
    text_content = text_content.replace("{{first_name}}", first_name)
    text_content = text_content.replace("{{last_name}}", last_name)
    text_content = text_content.replace("{{company_name}}", company_name)
    text_content = text_content.replace("{{email}}", recruiter.email or "")
    
    return text_content

def process_campaigns(dry_run=False):
    db = SessionLocal()
    server = None
    if not dry_run:
        try:
            server = get_smtp_connection()
            if not server:
                print("⚠️ No SMTP credentials configured. Run with --dry-run or configure SMTP_USER / SMTP_PASS.", flush=True)
                return
        except Exception as e:
            print(f"❌ Failed to connect to SMTP: {e}", flush=True)
            return

    try:
        now = datetime.now(timezone.utc)
        
        # Find all pending recruiters that are ready to send
        pending_records = db.query(CampaignRecruiter).join(Campaign).filter(
            CampaignRecruiter.status == CampaignRecruiterStatus.pending.value,
            Campaign.is_active == True,
            Campaign.status == "active",
            or_(
                CampaignRecruiter.next_send_at == None,
                CampaignRecruiter.next_send_at <= now
            )
        ).all()
        
        if not pending_records:
            print("No pending emails to send.", flush=True)
            return
            
        print(f"Found {len(pending_records)} pending campaign recruiters...", flush=True)
        
        for record in pending_records:
            campaign = record.campaign
            recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == record.recruiter_id).first()
            company = db.query(Company).filter(Company.company_id == recruiter.company_id).first() if recruiter and recruiter.company_id else None
            
            if not recruiter or not recruiter.email:
                print(f"Skipping record {record.campaign_recruiter_id}: No valid recruiter or email.")
                record.status = CampaignRecruiterStatus.failed.value
                record.last_error = "No valid email"
                db.commit()
                continue
                
            # Determine which step to send
            if not record.current_step_id:
                # Get step 1
                step = db.query(SequenceStep).filter(
                    SequenceStep.campaign_id == campaign.campaign_id,
                    SequenceStep.is_active == True
                ).order_by(SequenceStep.step_order.asc()).first()
            else:
                # It's pending but has a current step (meaning it's waiting for the delay to finish to send the NEXT step)
                # Wait, if status is pending, it means we should send the current_step_id!
                step = db.query(SequenceStep).filter(
                    SequenceStep.step_id == record.current_step_id
                ).first()
                
            if not step:
                # No more steps, mark completed
                record.status = CampaignRecruiterStatus.completed.value
                record.completed_at = now
                db.commit()
                print(f"Record {record.campaign_recruiter_id} completed sequence.")
                continue
                
            template = db.query(EmailTemplate).filter(EmailTemplate.template_id == step.template_id).first()
            if not template:
                record.status = CampaignRecruiterStatus.failed.value
                record.last_error = f"Template {step.template_id} missing"
                db.commit()
                continue
                
            # Render Email
            subject = interpolate_variables(template.subject, recruiter, company)
            body = interpolate_variables(template.body, recruiter, company)
            
            sender_email = campaign.from_email or os.environ.get("SMTP_USER", "no-reply@talentops.ai")
            sender_name = campaign.from_name or "TalentOps"
            
            print(f"[{'DRY RUN' if dry_run else 'SENDING'}] To: {recruiter.email} | Subject: {subject}")
            
            if not dry_run:
                msg = EmailMessage()
                msg.set_content(body)
                msg["Subject"] = subject
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = recruiter.email
                if campaign.reply_to_email:
                    msg["Reply-To"] = campaign.reply_to_email
                
                try:
                    server.send_message(msg)
                except Exception as e:
                    print(f"❌ Failed to send to {recruiter.email}: {e}")
                    record.status = CampaignRecruiterStatus.failed.value
                    record.last_error = str(e)
                    db.commit()
                    continue
            
            # Success - update record and schedule NEXT step!
            record.last_sent_at = now
            record.sent_count += 1
            
            # Find next step
            next_step = db.query(SequenceStep).filter(
                SequenceStep.campaign_id == campaign.campaign_id,
                SequenceStep.is_active == True,
                SequenceStep.step_order > step.step_order
            ).order_by(SequenceStep.step_order.asc()).first()
            
            if next_step:
                record.current_step_id = next_step.step_id
                # Calculate delay
                record.next_send_at = now + timedelta(days=next_step.delay_days, hours=next_step.delay_hours)
                record.status = CampaignRecruiterStatus.pending.value
                print(f"  -> Scheduled next step in {next_step.delay_days}d {next_step.delay_hours}h")
            else:
                record.status = CampaignRecruiterStatus.completed.value
                record.completed_at = now
                print("  -> Sequence Completed.")
                
            db.commit()
            
    finally:
        if server:
            server.quit()
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TalentOps Campaign Worker")
    parser.add_argument("--dry-run", action="store_true", help="Run without actually sending emails")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in the background")
    args = parser.parse_args()
    
    if args.daemon:
        print("Starting Campaign Worker Daemon...", flush=True)
        while True:
            process_campaigns(dry_run=args.dry_run)
            time.sleep(60) # check every minute
    else:
        process_campaigns(dry_run=args.dry_run)
