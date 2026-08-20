import requests
import json
import sys
import os

sys.path.append('backend')
from app.database import SessionLocal
from app.models.auth_models import User, TrustedDevice, Session as DBSession
from app.services.auth_service import create_access_token

def get_auth_token():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == 'admin@talentops.ai').first() or db.query(User).first()
        t_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id, TrustedDevice.status == 'Trusted').first()
        import hashlib, time
        token_hash = hashlib.sha256(f"test_{time.time()}".encode('utf-8')).hexdigest()
        from datetime import datetime, timedelta
        db_sess = DBSession(
            user_id=user.id,
            token_hash=token_hash,
            trusted_device_id=t_dev.id,
            is_active=True,
            expires_at=datetime.now() + timedelta(days=30),
            device="Search Verifier",
            ip_address="127.0.0.1"
        )
        db.add(db_sess)
        db.commit()
        db.refresh(db_sess)
        return create_access_token({"sub": str(user.id), "session_id": db_sess.id})
    finally:
        db.close()

token = get_auth_token()
headers = {"Authorization": f"Bearer {token}"}

print("=== SEARCHING FOR 'r' IN COMPANY SEARCH ===")
r = requests.get("http://localhost:8000/analytics/companies-search?q=r&limit=50", headers=headers)
print("Status code:", r.status_code)
data = r.json()
print(f"Total results returned: {len(data)}")

# Check occurrences of RHT or rht.com
rht_results = [row for row in data if 'rht' in (row.get('company_name') or '').lower() or 'rht.com' in (row.get('primary_domain') or '').lower() or 'rht.com' in (row.get('dominant_domain') or '').lower()]
print(f"\nOccurrences of 'Rht'/'rht.com' in results: {len(rht_results)} (Expected: Exactly 1)")
for res in rht_results:
    count = res.get('recruiter_count') or res.get('total_recruiters') or 0
    domain = res.get('primary_domain') or res.get('dominant_domain') or 'N/A'
    print(f"  -> Name: {res.get('company_name')} | Domain: {domain} | Total Recruiters: {count:,}")

# Check top 15 results
print("\n--- TOP 15 SEARCH RESULTS FOR 'r' ---")
for i, res in enumerate(data[:15], 1):
    count = res.get('recruiter_count') or res.get('total_recruiters') or 0
    domain = res.get('primary_domain') or res.get('dominant_domain') or 'N/A'
    print(f"  {i:2}. {str(res.get('company_name')):35} | {domain:25} | {count:8,} recruiters")
