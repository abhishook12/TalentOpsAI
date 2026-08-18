import sys
import os
import time
from fastapi.testclient import TestClient

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.main import app
from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import create_access_token

def run_pass1_mailintel_verification():
    print("=" * 80)
    print("CHECK 1 (PASS 1): MAILINTEL DELIVERABILITY API SUITE FORENSIC AUDIT")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "admin@talentops.com").first()
    token = create_access_token({"sub": str(admin_user.id), "role": "superadmin"})
    headers = {"Authorization": f"Bearer {token}"}
    db.close()

    # 1. Test GET /mailintel/stats
    print("\n[1.1] Testing GET /mailintel/stats ...")
    t0 = time.time()
    res1 = client.get("/mailintel/stats", headers=headers)
    t1 = time.time()
    assert res1.status_code == 200, f"Failed: {res1.text}"
    d1 = res1.json()
    print(f"      Latency: {round((t1-t0)*1000, 2)}ms")
    print(f"      Total Records: {d1.get('total'):,}")
    print(f"      Deliverable Emails: {d1.get('total_deliverable'):,}")
    print(f"      Deliverability Rate: {d1.get('deliverability_rate')}%")
    print(f"      Verified Corporate: {d1.get('verified'):,}")
    print(f"      Likely Deliverable: {d1.get('likely_valid'):,}")
    print(f"      Undeliverable: {d1.get('invalid'):,}")
    print(f"      Missing Emails: {d1.get('missing_emails'):,}")
    assert d1.get("total") > 400000, "Expected >400k total records"
    assert d1.get("deliverability_rate") > 90, "Expected >90% deliverability rate"
    print("      [PASS 1.1] /mailintel/stats verified successfully!")

    # 2. Test GET /mailintel/domains
    print("\n[1.2] Testing GET /mailintel/domains ...")
    res2 = client.get("/mailintel/domains?limit=10", headers=headers)
    assert res2.status_code == 200, f"Failed: {res2.text}"
    domains = res2.json()
    print(f"      Top Domains Returned: {len(domains)}")
    for d in domains[:4]:
        print(f"        - @{d['domain']} | Total: {d['total_sent']:,} | Success Rate: {d['success_rate']}% | Status: {d.get('status')}")
    assert len(domains) > 0, "Expected domain records"
    print("      [PASS 1.2] /mailintel/domains verified successfully!")

    # 3. Test GET /mailintel/verification-progress
    print("\n[1.3] Testing GET /mailintel/verification-progress ...")
    res3 = client.get("/mailintel/verification-progress", headers=headers)
    assert res3.status_code == 200, f"Failed: {res3.text}"
    d3 = res3.json()
    print(f"      Engine Status: {d3.get('status')} | Deliverable: {d3.get('deliverable_records'):,} ({d3.get('deliverability_pct')}%)")
    assert "deliverability_pct" in d3
    print("      [PASS 1.3] /mailintel/verification-progress verified successfully!")

    # 4. Test POST /mailintel/sweep
    print("\n[1.4] Testing POST /mailintel/sweep ...")
    t0 = time.time()
    res4 = client.post("/mailintel/sweep", headers=headers)
    t1 = time.time()
    assert res4.status_code == 200, f"Failed: {res4.text}"
    d4 = res4.json()
    print(f"      Sweep Execution Latency: {round((t1-t0), 2)}s")
    print(f"      Message: {d4.get('message')}")
    assert d4.get("status") == "success"
    print("      [PASS 1.4] /mailintel/sweep verified successfully!")

    print("\n" + "=" * 80)
    print("CHECK 1 (PASS 1) RESULT: ALL 4 MAILINTEL ENDPOINTS 100% OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    run_pass1_mailintel_verification()
