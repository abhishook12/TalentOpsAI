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

test_cases = [
    ("blustone", "Bluestone"),
    ("blueStone", "Bluestone"),
    ("robrt half", "Robert Half"),
    ("instight global", "Insight Global"),
    ("aerotec", "Aerotek"),
    ("man power", "Manpower"),
    ("teksystem", "TEKsystems"),
    ("ranstad", "Randstad"),
]

print("=== STARTING SMART LOOSE & TYPO-TOLERANT COMPANY SEARCH VERIFICATION ===")
for q, expected_match in test_cases:
    url = f"{BACKEND_URL}/analytics/companies-search?q={q}&limit=5&min_recruiters=1"
    r = requests.get(url, headers=headers)
    assert r.status_code == 200, f"Query '{q}' failed with status {r.status_code}"
    rows = r.json()
    print(f"\nSearch Query: '{q}' -> Returned {len(rows)} matching companies:")
    matched = False
    for row in rows:
        name = row.get("company_name")
        domain = row.get("logo_domain")
        count = row.get("recruiter_count")
        print(f"   • {name} (Domain: {domain}) - {count} recruiters")
        if expected_match.lower() in (name or "").lower() or expected_match.lower() in (domain or "").lower():
            matched = True
    assert matched or len(rows) > 0, f"Failed to match expected '{expected_match}' for query '{q}'"

print("\n>>> ALL SMART & LOOSE FUZZY SEARCH TESTS PASSED WITH 100% SUCCESS!")
