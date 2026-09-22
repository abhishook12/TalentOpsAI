import sys
import os
import json
import uuid
from datetime import datetime, timezone

# Ensure path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.models import Notification
from backend.app.models.auth_models import User
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.services.auth_service import create_access_token

print("=== CHECK 1: MULTI-ROLE NOTIFICATION & REVIEW QUEUE LIFECYCLE TEST ===")

client = TestClient(app)
db = SessionLocal()

try:
    # 1. Fetch Admin and User accounts
    admin_user = db.query(User).filter(User.email == "abhishekjadon824@gmail.com").first()
    normal_user = db.query(User).filter(User.email == "abhishekjadon706@gmail.com").first()
    other_user = db.query(User).filter(User.email == "normal_user@talentops.com").first()

    assert admin_user is not None, "Admin user not found"
    assert normal_user is not None, "Normal user not found"
    assert other_user is not None, "Other user not found"

    print(f"1. Test Accounts Verified:")
    print(f"   • Admin: {admin_user.email} (ID: {admin_user.id})")
    print(f"   • User A (Target): {normal_user.email} (ID: {normal_user.id})")
    print(f"   • User B (Isolation Check): {other_user.email} (ID: {other_user.id})")

    admin_token = create_access_token({"sub": str(admin_user.id)})
    user_token = create_access_token({"sub": str(normal_user.id)})
    other_token = create_access_token({"sub": str(other_user.id)})

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {user_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # 2. Test Admin Creating Global System Broadcast
    print("\n2. Admin Dispatching Global Fleet Broadcast:")
    bc_payload = {
        "title": "Platform Release v2.9.3 Synchronized",
        "message": "Desktop Scout v2.9.3 is live across all fleet nodes with real-time notifications.",
        "type": "update",
        "user_id": None  # Global
    }
    res_bc = client.post("/notifications/", json=bc_payload, headers=admin_headers)
    assert res_bc.status_code == 200, f"Failed to create broadcast: {res_bc.text}"
    global_notif_id = res_bc.json()["notification"]["id"]
    print(f"   ✓ Global broadcast created (ID: {global_notif_id})")

    # 3. Test Admin Creating Targeted Review Notification for User A
    print("\n3. Admin Dispatching Targeted User Review Notification:")
    user_payload = {
        "title": "Review Queue Update: Profile Verified",
        "message": "Your observed candidate lead at Google has been approved by engineering review.",
        "type": "success",
        "user_id": normal_user.id
    }
    res_target = client.post("/notifications/", json=user_payload, headers=admin_headers)
    assert res_target.status_code == 200, f"Failed to create targeted notification: {res_target.text}"
    targeted_notif_id = res_target.json()["notification"]["id"]
    print(f"   ✓ Targeted notification created for {normal_user.email} (ID: {targeted_notif_id})")

    # 4. Test Unauthenticated / Desktop Scout Telemetry Access (Public/Global Broadcasts)
    print("\n4. Testing Unauthenticated / Desktop Telemetry Access:")
    res_unauth = client.get("/notifications/")
    assert res_unauth.status_code == 200, f"Expected 200 for unauth, got {res_unauth.status_code}"
    unauth_notifs = res_unauth.json()
    unauth_ids = [n["id"] for n in unauth_notifs]
    assert global_notif_id in unauth_ids, "Global broadcast missing from unauthenticated feed"
    assert targeted_notif_id not in unauth_ids, "Targeted user notification leaked to unauthenticated feed!"
    print(f"   ✓ Desktop Scout / unauthenticated client received global broadcast safely without 401.")

    # 5. Test User A Access (Target User)
    print("\n5. Testing Target User Receiving Notifications:")
    res_user = client.get("/notifications/", headers=user_headers)
    assert res_user.status_code == 200
    user_notifs = res_user.json()
    user_ids = [n["id"] for n in user_notifs]
    assert global_notif_id in user_ids, "Target user did not receive global broadcast"
    assert targeted_notif_id in user_ids, "Target user did not receive their targeted notification"
    print(f"   ✓ Target user received both global broadcast and targeted review notification.")

    # 6. Test User B Isolation (Should NOT see User A's targeted notification)
    print("\n6. Testing Multi-Tenant Data Isolation (User B):")
    res_other = client.get("/notifications/", headers=other_headers)
    assert res_other.status_code == 200
    other_notifs = res_other.json()
    other_ids = [n["id"] for n in other_notifs]
    assert global_notif_id in other_ids, "Other user did not receive global broadcast"
    assert targeted_notif_id not in other_ids, "Data leak! Other user received User A's private notification!"
    print(f"   ✓ Data isolation verified: User B cannot see User A's notifications.")

    # 7. Test Staging Pipeline Review Approval with Automated Notification
    print("\n7. Testing Staging Pipeline Review Action & Auto-Notification:")
    unique_run = uuid.uuid4().hex[:8]
    staging_item = DiscoveryStaging(
        batch_id=f"batch_{unique_run}",
        discovery_id=f"disc_{unique_run}",
        device_id="desktop-node-483",
        owner_user_id=normal_user.id,
        raw_name=f"Alex Tester {unique_run}",
        raw_title="Principal Engineer",
        raw_company="OpenAI",
        raw_location="San Francisco, CA",
        processing_status="pending",
        visual_change_score="0.85",
        dom_confidence=92
    )
    db.add(staging_item)
    db.commit()
    db.refresh(staging_item)
    print(f"   • Created staged candidate record (ID: {staging_item.id}) for {normal_user.email}")

    # Admin approves review item
    res_approve = client.post(f"/staging/review/{staging_item.id}/approve", headers=admin_headers)
    assert res_approve.status_code == 200, f"Approval failed: {res_approve.text}"
    print(f"   • Admin approved staging record {staging_item.id}: decision={res_approve.json().get('decision')}")

    # Verify automated notification was created for normal_user
    auto_notif = db.query(Notification).filter(
        Notification.user_id == normal_user.id,
        Notification.title == "Staged Discovery Approved"
    ).order_by(Notification.id.desc()).first()
    assert auto_notif is not None, "Automated review approval notification was not dispatched to owner!"
    assert f"Alex Tester {unique_run}" in auto_notif.message
    print(f"   ✓ Automated review approval notification verified: '{auto_notif.title}' -> '{auto_notif.message}'")

    # 8. Test Marking All as Read
    print("\n8. Testing Mark All as Read Action:")
    res_read = client.post("/notifications/read", headers=user_headers)
    assert res_read.status_code == 200
    res_after = client.get("/notifications/", headers=user_headers)
    unread_count = sum(1 for n in res_after.json() if not n.get("read"))
    print(f"   • Remaining unread count for target user: {unread_count}")
    assert unread_count == 0, "Not all notifications were marked as read!"
    print("   ✓ Mark all as read action verified flawlessly.")

    print("\n>>> CHECK 1 PASSED: Full-Lifecycle Multi-Role Notification & Review System Verified!")

finally:
    db.close()
