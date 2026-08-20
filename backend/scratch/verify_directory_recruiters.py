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

print("--- Testing 1: GET /analytics/company-states ---")
r_states = requests.get(f"{BACKEND_URL}/analytics/company-states?company_id=161735&company_key=161735", headers=headers)
print("States status:", r_states.status_code)
states = r_states.json()
print("Total mapped states for Robert Half:", len(states))
fl_state = next((s for s in states if s.get("state") == "FL"), None)
print("FL state info:", fl_state)
assert r_states.status_code == 200

print("\n--- Testing 2: GET /recruiters/ (with trailing slash) ---")
r_rec1 = requests.get(f"{BACKEND_URL}/recruiters/?company_id=161735&company_key=161735&state=FL&limit=10", headers=headers)
print("Recruiters with slash status:", r_rec1.status_code)
assert r_rec1.status_code == 200
data1 = r_rec1.json()
print(f"Total recruiters returned: {len(data1.get('results', []))} | Total count: {data1.get('total_count')}")
for rec in data1.get('results', [])[:3]:
    print(f"  - {rec.get('recruiter_name')} | {rec.get('email')} | State: {rec.get('state')} | Company: {rec.get('company_name')}")

print("\n--- Testing 3: GET /recruiters (WITHOUT trailing slash - direct 200, no redirect) ---")
r_rec2 = requests.get(f"{BACKEND_URL}/recruiters?company_id=161735&company_key=161735&state=FL&limit=10", headers=headers, allow_redirects=False)
print("Recruiters without slash status (allow_redirects=False):", r_rec2.status_code)
assert r_rec2.status_code == 200, f"Expected 200 without redirect, got {r_rec2.status_code}"

print("\n>>> ALL DIRECTORY & RECRUITER ENDPOINT CHECKS PASSED WITH 100% SUCCESS!")
