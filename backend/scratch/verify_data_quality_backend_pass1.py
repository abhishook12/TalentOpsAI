import sys
import os
import json
import time

sys.path.insert(0, r"C:\TalentOpsAI\backend")
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.auth_models import User, Role
from app.models.models import Recruiter, Company
from app.services.auth_service import create_access_token

def run_pass1_backend_verification():
    print("=" * 80)
    print("CHECK 1 (PASS 1): BACKEND DATA QUALITY & SENTINEL API SUITE FORENSIC AUDIT")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()

    # Ensure admin user and token
    admin_user = db.query(User).filter(User.email == "admin@talentops.com").first()
    if not admin_user:
        admin_role = db.query(Role).filter(Role.name == "superadmin").first()
        if not admin_role:
            admin_role = Role(name="superadmin", description="Superadmin Role")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        admin_user = User(email="admin@talentops.com", role_id=admin_role.id, is_active=True, is_verified=True)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

    token = create_access_token({"sub": str(admin_user.id), "role": "superadmin"})
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[*] Superadmin JWT generated: {token[:20]}...")

    # 1. Test /sentinel/dashboard
    print("\n[1.1] Testing GET /sentinel/dashboard ...")
    t0 = time.time()
    res1 = client.get("/sentinel/dashboard", headers=headers)
    t1 = time.time()
    assert res1.status_code == 200, f"Dashboard failed with {res1.status_code}: {res1.text}"
    d1 = res1.json()
    print(f"      Latency: {round((t1-t0)*1000, 2)}ms")
    print(f"      Total Recruiters: {d1.get('total_recruiters'):,}")
    print(f"      Health Score: {d1.get('health_score')}%")
    print(f"      Email Coverage: {d1.get('email_coverage_pct')}%")
    print(f"      State Coverage: {d1.get('state_coverage_pct')}%")
    print(f"      Company Coverage: {d1.get('company_coverage_pct')}%")
    assert d1.get("total_recruiters") > 0, "Expected non-zero total recruiters"
    assert "health_score" in d1, "health_score field missing"
    print("      [PASS 1.1] /sentinel/dashboard verified successfully!")

    # 2. Test /sentinel/anomalies (all & filtered)
    print("\n[1.2] Testing GET /sentinel/anomalies ...")
    res2 = client.get("/sentinel/anomalies?filter_type=all&limit=5", headers=headers)
    assert res2.status_code == 200, f"Anomalies failed with {res2.status_code}: {res2.text}"
    d2 = res2.json()
    print(f"      Total Anomalies Found: {d2.get('total_anomalies'):,}")
    print(f"      Returned Records Count: {len(d2.get('records', []))}")
    if d2.get("records"):
        sample = d2["records"][0]
        print(f"      Sample Record: ID={sample['recruiter_id']}, Name={sample['recruiter_name']}, Score={sample['completeness_score']}%")
    assert "records" in d2, "records list missing from anomalies response"
    print("      [PASS 1.2] /sentinel/anomalies verified successfully!")

    # 3. Test POST /sentinel/scan-and-repair
    print("\n[1.3] Testing POST /sentinel/scan-and-repair ...")
    res3 = client.post("/sentinel/scan-and-repair", json={"limit": 50, "focus_area": "all"}, headers=headers)
    assert res3.status_code == 200, f"Scan-and-repair failed with {res3.status_code}: {res3.text}"
    d3 = res3.json()
    print(f"      Scanned Count: {d3.get('scanned_count')}")
    print(f"      Repaired Count: {d3.get('repaired_count')}")
    print(f"      Duration: {d3.get('duration_seconds')}s")
    print(f"      Message: {d3.get('message')}")
    assert d3.get("status") == "success", "Scan status was not success"
    print("      [PASS 1.3] /sentinel/scan-and-repair verified successfully!")

    # 4. Test GET /sentinel/quality-report
    print("\n[1.4] Testing GET /sentinel/quality-report ...")
    res4 = client.get("/sentinel/quality-report", headers=headers)
    assert res4.status_code == 200, f"Quality-report failed with {res4.status_code}: {res4.text}"
    d4 = res4.json()
    print(f"      Overall Grade: {d4.get('overall_grade')}")
    print(f"      Health Score: {d4.get('health_score')}%")
    print(f"      Executive Summary Keys: {list(d4.get('executive_summary', {}).keys())}")
    assert "overall_grade" in d4, "overall_grade missing from report"
    assert "recommendations" in d4, "recommendations missing from report"
    print("      [PASS 1.4] /sentinel/quality-report verified successfully!")

    # 5. Test Admin endpoints for parity
    print("\n[1.5] Testing GET /admin/data-quality and /admin/intelligence-stats ...")
    res5a = client.get("/admin/data-quality", headers=headers)
    assert res5a.status_code == 200, f"Admin data quality failed with {res5a.status_code}: {res5a.text}"
    d5a = res5a.json()
    print(f"      Admin Quality Score: {d5a.get('quality_score')}% (Total: {d5a.get('total_recruiters'):,})")

    res5b = client.get("/admin/intelligence-stats", headers=headers)
    assert res5b.status_code == 200, f"Intelligence stats failed with {res5b.status_code}: {res5b.text}"
    d5b = res5b.json()
    print(f"      Admin Intelligence Avg Completeness: {d5b['metrics']['average_completeness']}%")
    print("      [PASS 1.5] Admin quality endpoints verified successfully!")

    db.close()
    print("\n" + "=" * 80)
    print("CHECK 1 (PASS 1) RESULT: ALL 5 BACKEND DATA QUALITY ENDPOINTS 100% OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    run_pass1_backend_verification()
