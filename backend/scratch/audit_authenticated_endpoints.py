import os
import sys
import requests
import json
import time

sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))

from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import create_access_token
from app.models.auth_models import Session as DBSession

BASE_URL = "http://localhost:8000"

def get_auth_token():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == 'admin@talentops.ai').first()
        if not user:
            user = db.query(User).first()
        if not user:
            print("No user found in database for auth testing")
            return None
            
        import hashlib
        # Pre-generate token
        token_id_val = f"audit_token_{int(time.time()*1000)}"
        token_hash_val = hashlib.sha256(token_id_val.encode('utf-8')).hexdigest()
        
        from datetime import datetime, timedelta
        from app.models.auth_models import TrustedDevice
        
        # Ensure a trusted device exists
        t_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id, TrustedDevice.status == 'Trusted').first()
        if not t_dev:
            t_dev = TrustedDevice(
                user_id=user.id,
                device_id_hash=f"fp_{int(time.time())}_{user.id}",
                device_name="Automated Audit Console",
                browser="Chrome / Automated",
                os="Windows 11",
                ip_address="127.0.0.1",
                status="Trusted",
                risk_level="low",
                risk_score=0
            )
            db.add(t_dev)
            db.commit()
            db.refresh(t_dev)
            
        # Create an active session record
        db_sess = DBSession(
            user_id=user.id,
            token_hash=token_hash_val,
            trusted_device_id=t_dev.id,
            is_active=True,
            expires_at=datetime.now() + timedelta(days=30),
            device="Automated Auditor Device",
            ip_address="127.0.0.1"
        )
        db.add(db_sess)
        db.commit()
        db.refresh(db_sess)
        
        token = create_access_token({"sub": str(user.id), "session_id": db_sess.id})
        return token
    finally:
        db.close()

def audit_authenticated_endpoints():
    print("=================================================================")
    print("=== TALENTOPSAI AUTHENTICATED ENDPOINTS AUDIT ===")
    print("=================================================================")
    
    token = get_auth_token()
    if not token:
        print("[FAIL] Could not generate auth token")
        return False
        
    headers = {"Authorization": f"Bearer {token}"}
    cookies = {"access_token": token}
    
    endpoints = [
        ("GET", "/analytics/dashboard", 200),
        ("GET", "/analytics/recruiters-by-state", 200),
        ("GET", "/analytics/data-quality", 200),
        ("GET", "/analytics/companies-search?query=bridgecross", 200),
        ("GET", "/companies/search?query=aerotek", 200),
        ("GET", "/companies/", 200),
        ("GET", "/recruiters/?limit=10", 200),
        ("GET", "/recruiters/metro-hubs", 200),
        ("GET", "/recruiters/search?q=alex", 200),
        ("GET", "/campaigns/", 200),
        ("GET", "/candidates/", 200),
        ("GET", "/submissions/", 200),
        ("GET", "/vendors/", 200),
        ("GET", "/accounts/", 200),
        ("GET", "/auth/me", 200),
        ("GET", "/system/enricher/status", 200),
        ("GET", "/analytics/enrichment-feed", 200),
    ]
    
    pass_count = 0
    fail_count = 0
    
    for method, path, exp_status in endpoints:
        url = f"{BASE_URL}{path}"
        try:
            t0 = time.time()
            if method == "GET":
                r = requests.get(url, headers=headers, cookies=cookies, timeout=5)
            elif method == "POST":
                r = requests.post(url, headers=headers, cookies=cookies, json={}, timeout=5)
            latency = (time.time() - t0) * 1000
            
            allowed = exp_status if isinstance(exp_status, tuple) else (exp_status,)
            if r.status_code in allowed:
                print(f"  [PASS] {method:4} {path:45} -> {r.status_code} ({latency:.1f}ms)", flush=True)
                pass_count += 1
            else:
                print(f"  [FAIL] {method:4} {path:45} -> {r.status_code} (Expected {exp_status}) ({latency:.1f}ms)", flush=True)
                print(f"         Response: {r.text[:200]}", flush=True)
                fail_count += 1
        except Exception as e:
            print(f"  [ERR]  {method:4} {path:45} -> Exception: {e}", flush=True)
            fail_count += 1
            
    print("\n=================================================================")
    print(f"AUTHENTICATED AUDIT: {pass_count} Passed | {fail_count} Failed")
    print("=================================================================")
    return fail_count == 0

if __name__ == "__main__":
    success = audit_authenticated_endpoints()
    if not success:
        sys.exit(1)
