import os
import time
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from app.database import SessionLocal
from app.models.auth_models import ConnectedEmailAccount, User
from app.models.campaigns import Campaign, CampaignRecruiter, CampaignRecruiterStatus

BASE_URL = "http://127.0.0.1:8000"

def test_google_campaign():
    with SessionLocal() as db:
        acc = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.provider == "google").first()
        if not acc:
            print("No Google account found.")
            return
        
        user = db.query(User).filter(User.id == acc.user_id).first()
        if not user:
            print("User not found.")
            return

    # Use the first user's JWT to authenticate
    print(f"Testing with user {user.email} and Google account {acc.email_address}")
    
    # Normally we would need the user's token. Let's just create a token for the user manually.
    from app.routes.auth import create_access_token
    token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Campaign
    c_resp = requests.post(f"{BASE_URL}/campaigns", headers=headers, json={
        "name": "Google 403 Test Campaign",
        "description": "Testing the 403 permanent failure logic"
    })
    if c_resp.status_code != 200:
        print(f"Failed to create campaign: {c_resp.status_code} - {c_resp.text}")
        return
    campaign_id = c_resp.json()["campaign_id"]
    print(f"Created Campaign {campaign_id}")
    
    # Enroll recipient and template
    requests.post(f"{BASE_URL}/campaigns/{campaign_id}/prepare-preview", headers=headers, json={
        "name": "E2E Test Campaign",
        "subject": "Test Subject",
        "body": "<p>Hello</p>",
        "recipients": [{"email": "target@example.com", "name": "Target Person", "role": "Engineer"}]
    })
    
    # Update Campaign with sender account (need to set from_email too)
    requests.put(f"{BASE_URL}/campaigns/{campaign_id}", headers=headers, json={
        "sender_account_id": acc.account_id,
        "from_email": acc.email_address
    })
    
    # Start Campaign
    start_resp = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start", headers=headers)
    print(f"Start response: {start_resp.status_code} - {start_resp.text}")
    
    # Poll status for up to 10 seconds
    for _ in range(5):
        time.sleep(2)
        stat = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/status", headers=headers).json()
        print(f"Status: {stat['status']} - Sent: {stat['sent']}, Failed: {stat['failed']}, Pending: {stat['pending']}, Retrying: {stat['retrying']}")
        print(f"Has Auth Error: {stat.get('has_auth_error', False)}")
        
        if stat["failed"] > 0 or stat["retrying"] > 0:
            with SessionLocal() as db2:
                rec = db2.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == campaign_id).first()
                if rec:
                    print(f"Last Error: {rec.last_error}")
            if stat["failed"] > 0:
                print("Campaign correctly failed the recipient immediately!")
                break
            
if __name__ == "__main__":
    test_google_campaign()
