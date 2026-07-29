import time
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, CampaignRecruiter, EmailLog, EmailLogStatus, CampaignStatus, CampaignRecruiterStatus
import datetime

def run_checks():
    db = SessionLocal()
    try:
        email = "abhishek.jadon@technovion.com"
        user = db.query(User).filter(User.email == email).first()
        
        print("Waiting 15 seconds to allow the bridge to authenticate...")
        time.sleep(15)

        for i in range(1, 4):
            print(f"--- Running Check {i} ---")
            
            campaign = Campaign(
                user_id=user.id,
                name=f"Automated Test Check {i}",
                status=CampaignStatus.active.value,
                created_at=datetime.datetime.utcnow()
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)

            from app.models.models import Recruiter
            recruiter_email = f"test_{i}_{email}"
            recruiter_obj = db.query(Recruiter).filter(Recruiter.email == recruiter_email).first()
            if not recruiter_obj:
                recruiter_obj = Recruiter(
                    user_id=user.id,
                    email=recruiter_email,
                    recruiter_name=f"Abhishek Test {i}"
                )
                db.add(recruiter_obj)
                db.commit()
                db.refresh(recruiter_obj)
            
            campaign_recruiter = CampaignRecruiter(
                campaign_id=campaign.campaign_id,
                recruiter_id=recruiter_obj.recruiter_id,
                status=CampaignRecruiterStatus.pending.value
            )
            db.add(campaign_recruiter)
            db.commit()
            db.refresh(campaign_recruiter)

            log = EmailLog(
                campaign_id=campaign.campaign_id,
                campaign_recruiter_id=campaign_recruiter.campaign_recruiter_id,
                recipient_email=email,
                subject=f"Rule 11 Verification Check {i}",
                body_html=f"<h1>Rule 11 Check {i}</h1><p>If you are reading this, the strict Isolation Guard bridge verification passed.</p>",
                status=EmailLogStatus.sending.value,
                sent_via="outlook_bridge",
                queued_at=datetime.datetime.utcnow()
            )
            db.add(log)
            db.commit()
            print(f"Check {i} queued in DB. Waiting 15 seconds for Bridge to pick it up...")
            
            time.sleep(15)
            
            db.refresh(log)
            if log.status == EmailLogStatus.delivered.value:
                print(f"[SUCCESS] Check {i} PASSED. Bridge reported delivery.")
            elif log.status == EmailLogStatus.failed.value:
                print(f"[FAILED] Check {i} FAILED. Error: {log.error_message}")
            else:
                print(f"[TIMEOUT] Check {i} TIMEOUT. Status is still: {log.status}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_checks()
