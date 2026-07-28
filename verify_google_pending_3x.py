import sys
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
from app.main import app
from app.database import SessionLocal, get_db
from app.models.auth_models import User

client = TestClient(app)

def run_checks():
    success_count = 0
    for i in range(1, 4):
        print(f"\n--- Check {i} ---")
        
        test_email = f"google_test_{i}@example.com"
        
        # Mock Google's ID token verification
        mock_idinfo = {
            "email": test_email,
            "given_name": f"Test{i}",
            "family_name": "User",
            "sub": f"mock_google_sub_{i}",
            "picture": "https://example.com/pic.png"
        }
        
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_idinfo), \
             patch("app.routes.auth.DEV_AUTO_VERIFY", False), \
             patch("os.environ.get", side_effect=lambda k, d="": "mock_client_id" if k == "GOOGLE_CLIENT_ID" else d):
            
            response = client.post("/auth/google", json={"credential": "dummy_id_token"})
            
            if response.status_code == 202:
                print(f"PASS: Google login correctly returned 202 Accepted. Status Code: {response.status_code}")
                data = response.json()
                print(f"   Response Payload: {data}")
                
                if data.get('status') == 'pending_approval' and 'device_id' in data:
                    print(f"PASS: Payload successfully indicated pending_approval with device_id {data.get('device_id')}")
                else:
                    print(f"FAIL: Payload incorrect: {data}")
                
                # Verify DB status
                db = SessionLocal()
                user = db.query(User).filter(User.email == test_email).first()
                if user and user.status == "Pending Verification":
                    print(f"PASS: DB Status verified: user.status = '{user.status}'")
                    
                    # Verify Trusted Device was created
                    from app.models.auth_models import TrustedDevice
                    device = db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id).first()
                    if device and device.status == 'Pending':
                        print(f"PASS: Identity-First Device creation verified. Device Status: '{device.status}'")
                        success_count += 1
                    else:
                        print(f"FAIL: Trusted Device missing or incorrect status: {device}")
                else:
                    print(f"FAIL: DB Status failed: user is '{user.status if user else 'None'}'")
                
                # Cleanup user and device for future tests
                if user:
                    if device:
                        db.delete(device)
                    db.delete(user)
                    db.commit()
                db.close()
            else:
                print(f"FAIL: Check {i} failed! Expected 202, got {response.status_code}")
                print(f"   Response: {response.text}")
                
    print(f"\nTotal successful checks: {success_count} / 3")

if __name__ == "__main__":
    run_checks()
