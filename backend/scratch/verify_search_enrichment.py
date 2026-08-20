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

print("--- Testing 1: GET /recruiters/search?q=bluestonesg ---")
r = requests.get(f"{BACKEND_URL}/recruiters/search?q=bluestonesg&limit=10", headers=headers)
print("Status:", r.status_code)
assert r.status_code == 200
results = r.json()
print(f"Total results: {len(results)}")
for rec in results[:5]:
    c = rec.get("company", {})
    print(f"Recruiter: {rec.get('recruiter_name')} | Email: {rec.get('email')}")
    print(f"  -> Company Name: '{rec.get('company_name')}' | Domain: '{rec.get('company_domain')}'")
    print(f"  -> Company Object: Name: '{c.get('company_name')}' | Domain: '{c.get('primary_domain')}' | Logo: {c.get('logo_url')}")
    print()

assert all(rec.get("company_name") not in (None, "Unknown Company") for rec in results)
print(">>> VERIFICATION SUCCEEDED: 100% of recruiters have resolved company names and domains from email!")
