import requests
import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

db = SessionLocal()
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()
session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
db.close()

headers = {"Authorization": f"Bearer {token}", "X-Session-ID": str(session.id)}
BACKEND_URL = "http://127.0.0.1:8000"

print("--- Testing 1: Company Directory Search for BridgeCross ---")
r_comp = requests.get(f"{BACKEND_URL}/analytics/companies-search?q=bridgecross&limit=5", headers=headers)
print("Status:", r_comp.status_code)
assert r_comp.status_code == 200
comp_data = r_comp.json()
print(f"Found {len(comp_data)} company matches:")
for c in comp_data:
    print(f"  - Company: {c.get('company_name')} | Key: {c.get('company_key')} | Domain: {c.get('logo_domain')} | Count: {c.get('recruiter_count')}")

print("\n--- Testing 2: Recruiter Search for BridgeCross ---")
r_rec = requests.get(f"{BACKEND_URL}/recruiters/search?q=bridgecross&limit=20", headers=headers)
print("Status:", r_rec.status_code)
assert r_rec.status_code == 200
rec_data = r_rec.json()
print(f"Found {len(rec_data)} recruiters for BridgeCross:")
for r in rec_data:
    print(f"  - {r.get('recruiter_name')} | {r.get('email')} | Position: {r.get('specialization')} | Company: {r.get('company_name')}")

assert len(rec_data) >= 15
print("\n>>> ALL 15 BRIDGECROSS CONTACTS VERIFIED AS LIVE IN TALENTOPS DATABASE!")
