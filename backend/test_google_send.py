import os
import sys
import base64
import requests
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.database import SessionLocal
from app.models.auth_models import ConnectedEmailAccount
from app.services.send_engine import _refresh_google_token
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_gmail():
    with SessionLocal() as db:
        accounts = db.query(ConnectedEmailAccount).filter(ConnectedEmailAccount.provider == "google").all()
        if not accounts:
            print("No Google accounts found in DB.")
            return

        print(f"Found {len(accounts)} Google accounts.")
        for acc in accounts:
            print(f"Testing account: {acc.email_address} (ID: {acc.account_id})")
            
            # Print scopes if available? (Scopes aren't stored in DB directly, but we can verify token)
            print(f"  Access token length: {len(acc.access_token) if acc.access_token else 0}")
            print(f"  Refresh token length: {len(acc.refresh_token) if acc.refresh_token else 0}")
            
            msg = MIMEMultipart()
            msg['From'] = acc.email_address
            msg['To'] = acc.email_address
            msg['Subject'] = "Test Gmail API"
            msg.attach(MIMEText("This is a test from the backend.", 'html'))
            
            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            headers = {
                "Authorization": f"Bearer {acc.access_token}",
                "Content-Type": "application/json"
            }
            
            # Send using the exact endpoint from send_engine.py
            print("  Sending via POST https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send...")
            resp = requests.post("https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send", headers=headers, json={"raw": raw_msg}, timeout=10)
            print(f"  Response Code: {resp.status_code}")
            print(f"  Response Body: {resp.text}")
            
            if resp.status_code == 401:
                print("  Token expired. Refreshing...")
                new_token = _refresh_google_token(acc)
                if new_token:
                    print("  Token refreshed successfully. Retrying...")
                    headers["Authorization"] = f"Bearer {acc.access_token}"
                    resp = requests.post("https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send", headers=headers, json={"raw": raw_msg}, timeout=10)
                    print(f"  Retry Response Code: {resp.status_code}")
                    print(f"  Retry Response Body: {resp.text}")
                else:
                    print("  Failed to refresh token.")

if __name__ == "__main__":
    test_gmail()
