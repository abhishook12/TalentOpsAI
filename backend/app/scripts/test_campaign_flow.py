import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, CampaignStatus, CampaignRecruiter
from app.routes.campaigns import enroll_emails, EnrollEmailsRequest, RecipientData, api_validate_before_send
from app.services.send_engine import start_campaign, _active_campaign_managers
import asyncio

def test_campaign_flow():
    db = SessionLocal()
    # 1. Setup user
    user = db.query(User).first()
    if not user:
        user = User(email="test@example.com", auth_provider="local", auth_provider_id="1")
        db.add(user)
        db.commit()
    
    # 2. Setup Campaign
    campaign = Campaign(user_id=user.id, name="Test Campaign Flow", status=CampaignStatus.draft.value)
    db.add(campaign)
    db.commit()
    
    # Needs a sequence step
    from app.models.campaigns import SequenceStep, EmailTemplate
    template = EmailTemplate(user_id=user.id, campaign_id=campaign.campaign_id, name="Test Template", subject="Test", body="Test Body")
    db.add(template)
    db.commit()
    
    step = SequenceStep(campaign_id=campaign.campaign_id, step_order=1, template_id=template.template_id)
    db.add(step)
    db.commit()
    
    # 3. Test duplicate enrollment (Check 1)
    payload = EnrollEmailsRequest(recipients=[
        RecipientData(email="dup@test.com", name="Dup", role="SE"),
        RecipientData(email="DUP@test.com", name="Dup", role="SE"), # Duplicate
        RecipientData(email="unique@test.com", name="Unique", role="SE")
    ])
    
    res = enroll_emails(campaign.campaign_id, payload, db=db, current_user=user)
    print(f"[Check 1] Enrolled: {res['enrolled_count']} (Expected: 2)")
    assert res['enrolled_count'] == 2, "Duplicate emails not filtered out properly"
    
    # 4. Test Offline Bridge Warning (Check 2)
    # Ensure bridge offline warning is surfaced
    from fastapi.responses import JSONResponse
    val_res = api_validate_before_send(campaign.campaign_id, db=db, current_user=user)
    
    errors = val_res['errors']
    offline_warns = [e for e in errors if e['code'] == 'BRIDGE_OFFLINE']
    print(f"[Check 2] Offline Warnings: {len(offline_warns)}")
    assert len(offline_warns) > 0, "Bridge offline warning not found in preflight"
    
    # 5. Test Double-start Prevention (Check 3)
    # Mock _active_campaign_managers
    _active_campaign_managers.add(campaign.campaign_id)
    
    async def run_start():
        await start_campaign(campaign.campaign_id)
        
    asyncio.run(run_start())
    
    db.refresh(campaign)
    print(f"[Check 3] Campaign Status after blocked start: {campaign.status}")
    assert campaign.status == CampaignStatus.draft.value, "Campaign double-started despite being active in manager"
    
    print("ALL 3 CHECKS PASSED SUCCESSFULLY.")
    
if __name__ == "__main__":
    test_campaign_flow()

# Let's see if we can just test the DB logic and python router logic directly using pytest or custom script.
# Actually it's easier to write a pytest file and run it inside the backend.
