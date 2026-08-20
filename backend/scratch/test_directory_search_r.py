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
            device="Directory Verifier",
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

r = requests.get("http://localhost:8000/analytics/companies-search?q=r&limit=199&min_recruiters=1", headers=headers)
print("Status:", r.status_code)
rows = r.json()
print("Total companies returned:", len(rows))

seen_domains = {}
duplicates = []

for row in rows:
    dom = (row.get('logo_domain') or row.get('email_pattern') or '').lower().strip()
    name = row.get('company_name')
    count = row.get('recruiter_count')
    cid = row.get('company_key')
    
    if dom and dom not in ('n/a', 'none', ''):
        if dom in seen_domains:
            duplicates.append((dom, seen_domains[dom], (name, count, cid)))
        else:
            seen_domains[dom] = (name, count, cid)

print(f"\n--- DUPLICATE DOMAIN CHECK ---")
print(f"Total Unique Domains: {len(seen_domains)}")
print(f"Duplicate Domain Cards Found: {len(duplicates)} (Must be 0)")
for d in duplicates:
    print("  -> DUPLICATE DOMAIN:", d)

# Print top 20
print("\n--- TOP 20 DIRECTORY COMPANIES FOR 'r' ---")
for i, row in enumerate(rows[:20], 1):
    print(f"  {i:2}. {str(row.get('company_name'))[:30]:30} | {str(row.get('logo_domain') or 'N/A')[:20]:20} | {row.get('recruiter_count', 0):8,} recruiters | Key: {row.get('company_key')}")
