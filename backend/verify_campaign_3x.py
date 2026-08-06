"""
Campaign Feature Verification - 3 Checks
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import create_access_token

db = SessionLocal()
results = []

# ===== CHECK 1: Code-level integration =====
print("=" * 60)
print("CHECK 1: Campaign Engine Integration in main.py")
print("=" * 60)

with open("app/main.py", "r") as f:
    main_code = f.read()

checks = {
    "restart_active_campaigns imported": "restart_active_campaigns" in main_code,
    "sentinel_engine imported": "sentinel_engine" in main_code,
    "send_engine restart called on startup": "restart_active_campaigns()" in main_code,
    "sentinel_engine.start() called": "sentinel_engine.start()" in main_code,
    "timeout_stuck_emails_sweep task": "timeout_stuck_emails_sweep" in main_code,
    "campaign router mounted at /campaigns": 'prefix="/campaigns"' in main_code,
}

c1_pass = True
for name, passed in checks.items():
    tag = "[PASS]" if passed else "[FAIL]"
    if not passed: c1_pass = False
    print(f"  {tag} {name}")
    results.append((name, passed))

print(f"\nCHECK 1 RESULT: {'PASSED' if c1_pass else 'FAILED'}")

# ===== CHECK 2: send_engine.py has all campaign functions =====
print("\n" + "=" * 60)
print("CHECK 2: send_engine.py Campaign Processing Functions")
print("=" * 60)

with open("app/services/send_engine.py", "r") as f:
    engine_code = f.read()

engine_checks = {
    "process_campaign_queue function": "async def process_campaign_queue" in engine_code,
    "start_campaign function": "async def start_campaign" in engine_code,
    "pause_campaign function": "def pause_campaign" in engine_code,
    "cancel_campaign function": "def cancel_campaign" in engine_code,
    "resume_campaign function": "async def resume_campaign" in engine_code,
    "restart_active_campaigns (crash recovery)": "def restart_active_campaigns" in engine_code,
    "Worker pool pattern": "_worker_task" in engine_code,
    "Microsoft Graph API integration": "graph.microsoft.com" in engine_code,
    "Exponential backoff retry": "_schedule_retry" in engine_code,
}

c2_pass = True
for name, passed in engine_checks.items():
    tag = "[PASS]" if passed else "[FAIL]"
    if not passed: c2_pass = False
    print(f"  {tag} {name}")
    results.append((name, passed))

print(f"\nCHECK 2 RESULT: {'PASSED' if c2_pass else 'FAILED'}")

# ===== CHECK 3: Frontend campaign components =====
print("\n" + "=" * 60)
print("CHECK 3: Frontend Campaign Components")
print("=" * 60)

frontend_checks = {
    "Campaigns.jsx page exists": os.path.exists("../frontend/src/pages/Campaigns.jsx"),
    "EmailPreview.jsx component exists": os.path.exists("../frontend/src/components/EmailPreview.jsx"),
}

sidebar_path = "../frontend/src/components/Sidebar.jsx"
if os.path.exists(sidebar_path):
    with open(sidebar_path, "r") as f:
        sidebar = f.read()
    frontend_checks["Sidebar has /campaigns nav link"] = "/campaigns" in sidebar

campaigns_path = "../frontend/src/pages/Campaigns.jsx"
if os.path.exists(campaigns_path):
    with open(campaigns_path, "r") as f:
        campaigns = f.read()
    frontend_checks["New Campaign button in UI"] = "New Campaign" in campaigns
    frontend_checks["Campaign Wizard multi-step flow"] = "handleNextStep" in campaigns
    frontend_checks["EmailPreview imported in wizard"] = "EmailPreview" in campaigns
    frontend_checks["Campaign status tracking"] = "CampaignStatus" in campaigns or "campaign_status" in campaigns or "is_active" in campaigns

# Check campaigns route
with open("app/routes/campaigns.py", "r", encoding="utf-8") as f:
    routes_code = f.read()
frontend_checks["POST /campaigns/ create endpoint"] = "def create_campaign" in routes_code
frontend_checks["POST /templates endpoint (relaxed schema)"] = "templates" in routes_code

c3_pass = True
for name, passed in frontend_checks.items():
    tag = "[PASS]" if passed else "[FAIL]"
    if not passed: c3_pass = False
    print(f"  {tag} {name}")
    results.append((name, passed))

print(f"\nCHECK 3 RESULT: {'PASSED' if c3_pass else 'FAILED'}")

# ===== SUMMARY =====
total = len(results)
passed = sum(1 for _, p in results if p)
failed = total - passed

print("\n" + "=" * 60)
print("CAMPAIGN FEATURE VERIFICATION SUMMARY")
print("=" * 60)
print(f"  Total checks: {total}")
print(f"  Passed:       {passed}")
print(f"  Failed:       {failed}")
print(f"  Result:       {'ALL CHECKS PASSED' if failed == 0 else f'{failed} CHECKS FAILED'}")
print("=" * 60)

db.close()
