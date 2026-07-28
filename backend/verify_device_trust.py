import requests
import time
import os

BASE_URL = "http://localhost:8000/auth"
# Assumes there is a user we can test with. Let's create one or use a dummy.
# Wait, we can just hit the API. If we don't know the password, we can create a dummy user in the db first.

from app.database import SessionLocal
from app.models.auth_models import User, TrustedDevice, Session
from app.services.auth_service import get_password_hash
import uuid

def run_test():
    db = SessionLocal()
    
    # 1. Setup a test user
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_pass = "TestPassword123!"
    
    print(f"Creating test user {test_email}...")
    user = User(
        email=test_email,
        password_hash=get_password_hash(test_pass),
        first_name="Test",
        last_name="User",
        status="Active",
        auth_provider="local"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # We will use requests Session to keep cookies
    client = requests.Session()
    
    print("\n[CHECK 1] Attempting to login from a new (unapproved) device...")
    login_data = {"email": test_email, "password": test_pass, "remember_me": False}
    resp = client.post(f"{BASE_URL}/login", json=login_data)
    
    if resp.status_code == 403 and "Access Restricted" in resp.json().get('detail', ''):
        print("SUCCESS: Device blocked with 403 Access Restricted.")
    else:
        print(f"FAIL: Expected 403 Access Restricted, got {resp.status_code} - {resp.text}")
        return False
        
    # The device_id cookie should have been set
    device_id = client.cookies.get("device_id")
    if not device_id:
        print("FAIL: device_id cookie was not set.")
        return False
    print(f"SUCCESS: device_id cookie is present: {device_id[:10]}...")
    
    # 2. Admin approves the device
    print("\n[CHECK 2] Admin approves the device...")
    import hashlib
    device_hash = hashlib.sha256(device_id.encode()).hexdigest()
    
    device = db.query(TrustedDevice).filter(TrustedDevice.device_id_hash == device_hash).first()
    if not device:
        print("FAIL: TrustedDevice record not found in DB.")
        return False
    
    if device.status != 'Pending':
        print(f"FAIL: Expected status Pending, got {device.status}")
        return False
        
    device.status = 'Trusted'
    db.commit()
    print("SUCCESS: Device status manually set to Trusted in DB.")
    
    # 3. Attempt login again from the same client (device)
    print("\n[CHECK 3] Attempting login again from the approved device...")
    resp2 = client.post(f"{BASE_URL}/login", json=login_data)
    if resp2.status_code == 200:
        print("SUCCESS: Login succeeded!")
        print(f"Token: {resp2.json().get('token')[:20]}...")
    else:
        print(f"FAIL: Expected 200 OK, got {resp2.status_code} - {resp2.text}")
        return False
        
    return True

if __name__ == "__main__":
    if run_test():
        print("\nAll checks passed successfully! Rule of 3 satisfied.")
    else:
        print("\nVerification failed.")
