import sys
import os
import json
import urllib.request
import urllib.error

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.auth_models import User, Session as DBSession, TrustedDevice
from app.services.auth_service import create_access_token

db = SessionLocal()
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
trusted_dev = db.query(TrustedDevice).filter(TrustedDevice.user_id == admin_user.id, TrustedDevice.status == "Trusted").first()

session = db.query(DBSession).filter(DBSession.user_id == admin_user.id, DBSession.trusted_device_id == trusted_dev.id).first()
if not session:
    session = DBSession(user_id=admin_user.id, is_active=True, device="Automated Test Suite", trusted_device_id=trusted_dev.id)
    db.add(session)
    db.commit()

token = create_access_token(data={"sub": str(admin_user.id), "session_id": str(session.id)})
db.close()

headers = {
    "Authorization": f"Bearer {token}",
    "X-Session-ID": str(session.id),
    "User-Agent": "TalentOps-TestSuite/1.0"
}

base = "http://127.0.0.1:8000"

endpoints = [
    ("GET", "/health", False),
    ("GET", "/health/store", False),
    ("GET", "/version", False),
    ("GET", "/auth/me", True),
    ("GET", "/analytics/dashboard", True),
    ("GET", "/analytics/data-quality", True),
    ("GET", "/analytics/companies-search?limit=10&min_recruiters=1", True),
    ("GET", "/analytics/company-states?company_key=161735", True),
    ("GET", "/recruiters/?limit=10&skip=0", True),
    ("GET", "/companies/?limit=10&skip=0", True),
    ("GET", "/campaigns/", True),
    ("GET", "/admin/stats", True),
    ("GET", "/admin/intelligence-stats", True),
    ("GET", "/sentinel/dashboard", True),
]

print("=" * 80)
print("EXHAUSTIVE LOCAL API ENDPOINT SUITE EXECUTION")
print("=" * 80)

passed = 0
failed = 0

for method, path, needs_auth in endpoints:
    url = base + path
    req = urllib.request.Request(url, headers=headers if needs_auth else {"User-Agent": "TalentOps/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status = r.status
            content = r.read().decode('utf-8')
            try:
                data = json.loads(content)
                summary = f"JSON {type(data).__name__} with {len(data) if isinstance(data, (list, dict)) else 1} items"
            except Exception:
                summary = f"Raw text {len(content)} bytes"
            print(f"  [PASS] {method:4s} {path:60s} -> HTTP {status} ({summary})")
            passed += 1
    except urllib.error.HTTPError as e:
        print(f"  [FAIL] {method:4s} {path:60s} -> HTTP {e.code}: {e.read().decode('utf-8')[:200]}")
        failed += 1
    except Exception as e:
        print(f"  [FAIL] {method:4s} {path:60s} -> Error: {e}")
        failed += 1

print("\n" + "=" * 80)
print(f"FINAL RESULT: {passed} PASSED, {failed} FAILED (Total: {len(endpoints)})")
print("=" * 80)
