import sys
import json
import uuid
from app.database import SessionLocal
from app.models.auth_models import User
from app.models.extension_models import ExtensionActivationCode, ExtensionDevice, ExtensionHeartbeat, ExtensionSubmissionLog
from app.models.models import Recruiter, Company
from app.routes.extension import (
    auto_activate_extension,
    activate_extension,
    ingest_extension_batch,
    extension_heartbeat,
    extension_report,
    get_live_extension_feed,
    get_live_extension_summary,
    create_activation_code,
    ActivationRequest,
    BatchRequest,
    ExtensionContact,
    HeartbeatRequest,
    CreateCodeRequest,
)
from fastapi import Request
from starlette.requests import Request as StarletteRequest

db = SessionLocal()

print("=== EXTENSION SUITE INTEGRATION TEST ===")

# 1. Fetch admin user
admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
if not admin_user:
    admin_user = db.query(User).filter(User.id == 56).first()
if not admin_user:
    admin_user = db.query(User).first()
print(f"Using Admin User: id={admin_user.id}, email={admin_user.email}")

# 2. Test Zero-Touch Auto-Activation
auto_dev = f"test-auto-{uuid.uuid4().hex[:8]}"
auto_res = auto_activate_extension(req={"device_id": auto_dev}, db=db)
assert "access_token" in auto_res, f"Auto-activate failed: {auto_res}"
print(f"[OK] Auto-Activation succeeded for device {auto_dev}")

# 3. Create Activation Code
create_req = CreateCodeRequest(label="Automated QA Test Code", max_uses=5)
code_res = create_activation_code(req=create_req, db=db, current_user=admin_user)
code = code_res["code"]
print(f"[OK] Generated Activation Code: {code}")

# 4. Activate Extension Device
device_id = f"test-ext-{uuid.uuid4().hex[:12]}"
act_req = ActivationRequest(activation_code=code, device_id=device_id, user_agent="Mozilla/5.0 Test Chrome/120.0")
act_res = activate_extension(req=act_req, db=db)
token = act_res["access_token"]
print(f"[OK] Extension Activated for device {device_id}. Received JWT.")

# 5. Ingest Batch of Profiles
mock_contacts = [
    ExtensionContact(
        recruiter_name="Sarah Jenkins",
        email=f"sjenkins_{uuid.uuid4().hex[:6]}@apexsystems.com",
        phone="512-555-0199",
        title="Senior Technical Recruiter",
        company_name="Apex Systems",
        linkedin_url=f"https://www.linkedin.com/in/sarah-jenkins-{uuid.uuid4().hex[:6]}/",
        location="Austin, TX",
        source="linkedin_profile",
        source_url="https://www.linkedin.com/in/sarah-jenkins/",
        source_page_title="Sarah Jenkins | LinkedIn"
    ),
    ExtensionContact(
        recruiter_name="Michael Chang",
        email=f"mchang_{uuid.uuid4().hex[:6]}@insightglobal.com",
        phone="404-555-0144",
        title="Talent Acquisition Lead",
        company_name="Insight Global",
        linkedin_url=f"https://www.linkedin.com/in/michael-chang-{uuid.uuid4().hex[:6]}/",
        location="Atlanta, GA",
        source="gmail_signature",
        source_url="https://mail.google.com/mail/u/0/#inbox/18b",
        source_page_title="Re: Senior DevOps Role - Insight Global"
    ),
    ExtensionContact(
        recruiter_name="Amanda Cruz",
        email=f"acruz_{uuid.uuid4().hex[:6]}@teksystems.com",
        title="Staffing Specialist",
        company_name="TEKsystems",
        location="Dallas, TX",
        source="indeed_job_posting",
        source_url="https://www.indeed.com/viewjob?jk=123",
        source_page_title="TEKsystems - Cloud Engineer Job in Dallas"
    )
]

batch_req = BatchRequest(contacts=mock_contacts, device_id=device_id)

# Create a mock starlette request
scope = {"type": "http", "method": "POST", "path": "/recruiters/extension/batch", "headers": []}
mock_req = StarletteRequest(scope)

batch_res = ingest_extension_batch(
    req=batch_req,
    request=mock_req,
    db=db,
    current_user=admin_user,
    x_device_id=device_id,
    x_extension_version="2.0.0"
)
print(f"[OK] Ingested batch: accepted={batch_res['accepted']}, duplicates={batch_res['duplicates']}")
assert batch_res['accepted'] == 3, f"Expected 3 accepted, got {batch_res['accepted']}"

# 6. Ingest Duplicate to test deduplication & enhancement
dup_contacts = [
    ExtensionContact(
        recruiter_name="Sarah Jenkins",
        email=mock_contacts[0].email,
        phone="512-555-9999", # updated phone
        title="Senior Technical Recruiter",
        company_name="Apex Systems",
        linkedin_url=mock_contacts[0].linkedin_url,
        location="Austin, TX",
        source="linkedin_search"
    )
]
dup_req = BatchRequest(contacts=dup_contacts, device_id=device_id)
dup_res = ingest_extension_batch(
    req=dup_req,
    request=mock_req,
    db=db,
    current_user=admin_user,
    x_device_id=device_id,
    x_extension_version="2.0.0"
)
print(f"[OK] Deduplication test: accepted={dup_res['accepted']}, duplicates={dup_res['duplicates']}")
assert dup_res['duplicates'] == 1, f"Expected 1 duplicate, got {dup_res['duplicates']}"

# 7. Heartbeat Ping
hb_req = HeartbeatRequest(
    device_id=device_id,
    session_captured=4,
    session_sent=3,
    session_duplicates=1,
    queue_pending=0,
    total_ever_sent=3,
    extension_version="2.0.0"
)
hb_res = extension_heartbeat(req=hb_req, db=db, current_user=admin_user)
print(f"[OK] Heartbeat ping response: {hb_res}")
assert hb_res["ok"] == True

# 8. Test Live Feed & Live Summary
feed_res = get_live_extension_feed(limit=5, db=db, current_user=admin_user)
assert "feed" in feed_res and len(feed_res["feed"]) > 0
print(f"[OK] Live feed retrieved: {len(feed_res['feed'])} recent items")

summary_res = get_live_extension_summary(db=db, current_user=admin_user)
assert summary_res["total_recruiters"] > 0
print(f"[OK] Live summary retrieved: {summary_res['total_recruiters']} recruiters, {summary_res['active_scouts']} active scouts")

# 9. Admin Report
report_res = extension_report(days=7, db=db, current_user=admin_user)
print(f"[OK] Admin report retrieved successfully.")
print(f"     Total accepted in period: {report_res['totals']['accepted']}")
print(f"     Total active devices: {len(report_res['devices'])}")
print(f"     Daily summary rows: {len(report_res['daily_summary'])}")
assert report_res['totals']['accepted'] >= 3, "Report totals did not reflect ingested contacts"

print("\n=== ALL EXTENSION SUITE INTEGRATION TESTS PASSED ===")
