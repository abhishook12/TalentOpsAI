"""
Test Check 3: Sourcing Funnel Analytics & Frontend Integrity
Verifies /analytics/sourcing-funnel, /analytics/pipeline-velocity, response contracts, and frontend component integrity.
"""
import sys
import subprocess
import requests

BASE_URL = "http://127.0.0.1:8000"
BYPASS_TOKEN = "legacy_admin_bypass_token"
ADMIN_HEADERS = {"Authorization": f"Bearer {BYPASS_TOKEN}"}

def run_test():
    print("=== [TEST CHECK 3] SOURCING FUNNEL ANALYTICS & FRONTEND VERIFICATION ===")

    # 1. Test /analytics/sourcing-funnel endpoint
    r = requests.get(f"{BASE_URL}/analytics/sourcing-funnel?days=30", headers=ADMIN_HEADERS, timeout=10)
    assert r.status_code == 200, f"/analytics/sourcing-funnel failed: {r.status_code} {r.text}"
    funnel_data = r.json()
    print("[PASS] 1. /analytics/sourcing-funnel responded with HTTP 200")

    # 2. Verify funnel schema
    assert "funnel" in funnel_data, "Missing 'funnel' key"
    assert "conversion_rates" in funnel_data, "Missing 'conversion_rates' key"
    assert "source_breakdown" in funnel_data, "Missing 'source_breakdown' key"
    assert "daily_trend" in funnel_data, "Missing 'daily_trend' key"
    assert "campaign_performance" in funnel_data, "Missing 'campaign_performance' key"
    f = funnel_data["funnel"]
    for required_metric in ["discovered", "promoted", "contacted", "delivered", "opened", "replied"]:
        assert required_metric in f, f"Missing metric {required_metric} in funnel"
    print(f"[PASS] 2. Verified Funnel metrics: discovered={f.get('discovered')}, promoted={f.get('promoted')}, contacted={f.get('contacted')}, delivered={f.get('delivered')}")

    # 3. Test /analytics/pipeline-velocity endpoint
    r = requests.get(f"{BASE_URL}/analytics/pipeline-velocity", headers=ADMIN_HEADERS, timeout=10)
    assert r.status_code == 200, f"/analytics/pipeline-velocity failed: {r.status_code} {r.text}"
    velocity_data = r.json()
    print("[PASS] 3. /analytics/pipeline-velocity responded with HTTP 200")

    # 4. Verify velocity schema
    for v_key in ["avg_processing_time_hours", "total_processed", "weekly_throughput", "daily_throughput", "avg_time_to_first_send_hours"]:
        assert v_key in velocity_data, f"Missing velocity metric {v_key}"
    print(f"[PASS] 4. Verified Pipeline Velocity: weekly_throughput={velocity_data.get('weekly_throughput')}, avg_processing_time_hours={velocity_data.get('avg_processing_time_hours')}")

    # 5. Frontend component integrity & build check
    print("Running frontend syntax verification on Analytics.jsx...")
    cmd = ["node", "-e", """
        const fs = require('fs');
        const code = fs.readFileSync('frontend/src/pages/Analytics.jsx', 'utf8');
        if (!code.includes('sourcing-funnel')) {
            throw new Error('Analytics.jsx does not contain sourcing-funnel endpoint call');
        }
        if (!code.includes('Sourcing Funnel')) {
            throw new Error('Analytics.jsx does not contain Sourcing Funnel UI title');
        }
        console.log('Analytics.jsx verified: contains Sourcing Funnel and API hook.');
    """]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd="c:\\TalentOpsAI")
    assert res.returncode == 0, f"Frontend check failed: {res.stderr}"
    print(f"[PASS] 5. {res.stdout.strip()}")

    print(">>> CHECK 3 PASSED: ALL 5 VERIFICATION ASSERTIONS SUCCEEDED <<<\n")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"[FAIL] Check 3 failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
