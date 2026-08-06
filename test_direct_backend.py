import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.database import SessionLocal
from app.models.auth_models import User
from app.models.campaigns import Campaign, EmailTemplate, SequenceStep
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth_service import create_access_token

def run_test(iteration):
    print(f"\n--- ATTEMPT {iteration} ---")
    
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "admin@talentops.com").first()
        if not user:
            print("Admin user not found")
            return False

        # Create Campaign
        campaign = Campaign(
            name=f"Direct Test Campaign {iteration} {uuid.uuid4().hex[:6]}",
            user_id=user.id,
            status="draft"
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        # Add Template
        template = EmailTemplate(
            campaign_id=campaign.campaign_id,
            name=f"Test Template {iteration}",
            subject=f"Test Subject {iteration}",
            body="Test Body"
        )
        db.add(template)
        db.commit()
        user_id = user.id
        campaign_id = campaign.campaign_id
        
    client = TestClient(app)
    token = create_access_token(data={"sub": str(user_id)})
    
    print(f"Sending request to /campaigns/{campaign_id}/prepare-preview...")
    res = client.post(
        f"/campaigns/{campaign_id}/prepare-preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"Test {iteration}",
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "admin@talentops.com",
            "recipients": []
        }
    )
    
    if res.status_code == 200:
        print(f"SUCCESS: Campaign {campaign_id} generated preview successfully.")
        return True
    else:
        print(f"FAILED: Status {res.status_code} - {res.text}")
        return False

if __name__ == "__main__":
    print("RUNNING 3-PASS VERIFICATION OF CAMPAIGN PREVIEW FIX...")
    success = 0
    for i in range(1, 4):
        if run_test(i):
            success += 1
            
    print(f"\nFINAL RESULT: {success}/3 Passes completed successfully.")
    if success == 3:
        print("3-PASS VERIFICATION SUCCESSFUL")
    else:
        print("3-PASS VERIFICATION FAILED")
        sys.exit(1)
