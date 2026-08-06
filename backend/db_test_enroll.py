import time
import random
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, SequenceStep, CampaignRecruiter, CampaignRecruiterStatus
from app.models.models import Recruiter
from app.routes.campaigns import EnrollEmailsRequest, RecipientData, enroll_emails
from sqlalchemy.sql import func
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

def main():
    db = SessionLocal()
    # 1. Get a user
    user = db.query(User).filter(User.email == "admin@talentops.com").first()
    if not user:
        print("User not found.")
        return
        
    # 2. Create Campaign and Sequence Step
    campaign = Campaign(user_id=user.id, name=f"Bulk Test {int(time.time())}")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    from app.models.campaigns import EmailTemplate
    template = EmailTemplate(user_id=user.id, campaign_id=campaign.campaign_id, name="Test Template", subject="Test", body="Test body")
    db.add(template)
    db.commit()
    db.refresh(template)
    
    step = SequenceStep(
        campaign_id=campaign.campaign_id,
        step_order=1,
        delay_days=0,
        template_id=template.template_id
    )
    db.add(step)
    db.commit()
    
    # 3. Simulate 3 checks of 5000 enrollments
    for check in range(1, 4):
        print(f"\n--- Check {check} ---")
        recipients = []
        for i in range(5000):
            recipients.append(RecipientData(
                email=f"dummy{i}_{int(time.time())}_{check}@example.com",
                name=f"Dummy {i}",
                company="Acme Corp",
                role="Engineer"
            ))
            
        payload = EnrollEmailsRequest(recipients=recipients)
        
        print(f"Enrolling 5000 dummy recipients to campaign {campaign.campaign_id}...")
        start_time = time.time()
        
        # We simulate what the endpoint does by running the exact code logic.
        # But wait, the function enroll_emails is an API endpoint.
        # We can just call it directly!
        try:
            result = enroll_emails(campaign.campaign_id, payload, db=db, current_user=user)
            enrolled = result["enrolled_count"]
            print(f"Successfully enrolled {enrolled} recipients.")
        except Exception as e:
            print(f"Failed: {e}")
            
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"Execution time: {elapsed:.3f} seconds!")
        
    db.close()

if __name__ == "__main__":
    main()
