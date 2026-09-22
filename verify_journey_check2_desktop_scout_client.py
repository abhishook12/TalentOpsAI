import sys
import os
import json
import time
from datetime import datetime, timezone

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from PySide6.QtWidgets import QApplication
qt_app = QApplication.instance() or QApplication(sys.argv)

from backend.app.database import SessionLocal
from backend.app.models.update_models import ScoutRelease, ScoutFleetBroadcast, ScoutInstallation
from backend.app.services.scout_node_service import record_scout_heartbeat, invalidate_active_broadcast_cache
from scout_desktop.version import __version__
from scout_desktop.ui.components import TopBar
from scout_desktop.ui.main_window import MainWindow
from scout_desktop.ui.notifications_window import UpdateCenterDialog, NotificationsDialog

print("=== CHECK 2: DESKTOP SCOUT CLIENT RUNTIME & FLEET BROADCAST TEST ===")

db = SessionLocal()

try:
    # 1. Dispatch a Fleet Update Broadcast from Backend
    print("1. Creating Active Fleet Broadcast in Backend (v2.9.4):")
    # Deactivate older broadcasts
    db.query(ScoutFleetBroadcast).filter(ScoutFleetBroadcast.is_active == True).update(
        {"is_active": False}, synchronize_session=False
    )
    db.commit()

    bc_id = f"BCST-TEST-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    broadcast = ScoutFleetBroadcast(
        broadcast_id=bc_id,
        target_version="2.9.4",
        cohort="ALL_ACTIVE",
        is_mandatory=False,
        title="TalentOps Scout v2.9.4 Fleet Update Ready",
        message="Enhanced AI OCR extractor and instant notification sync is available.",
        release_notes="Edge-accelerated semantic factorizer and real-time review queue feedback.",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(broadcast)
    db.commit()
    invalidate_active_broadcast_cache()
    print(f"   ✓ Fleet broadcast {bc_id} registered and cached in backend.")

    # 2. Simulate Desktop Scout Node #483 Heartbeat Ping
    print("\n2. Simulating Scout Desktop Node #483 Heartbeat Ingestion:")
    hb_metrics = {
        "version": __version__,
        "status": "ONLINE",
        "active_window": "LinkedIn Recruiter - Google Chrome",
        "cpu_percent": 12.4,
        "memory_mb": 145.2,
        "load_level": "OPTIMAL",
        "device_name": "Desktop Scout Node #483"
    }
    from backend.app.models.auth_models import User
    normal_user = db.query(User).filter(User.email == "abhishekjadon706@gmail.com").first()
    assert normal_user is not None, "Normal user not found"

    hb_resp = record_scout_heartbeat(
        db=db,
        user_id=normal_user.id,
        device_id="desktop-node-483",
        page_url="https://www.linkedin.com/in/test-recruiter",
        client_metrics=hb_metrics
    )
    print(f"   • Heartbeat result: status={hb_resp.get('status')}")
    notif_payload = hb_resp.get("update_notification")
    assert notif_payload is not None, "Heartbeat failed to deliver active fleet update notification!"
    print(f"   ✓ Delivered update notification: title='{notif_payload.get('title')}', target='v{notif_payload.get('target_version')}'")
    assert notif_payload.get("target_version") == "2.9.4"
    assert notif_payload.get("broadcast_id") == bc_id

    # 3. Simulate Scout Desktop UI Response
    print("\n3. Testing Scout Desktop UI Runtime & Component Responses:")
    main_win = MainWindow()
    top_bar = main_win.top_bar

    # Initial state
    assert f"v{__version__}" in top_bar.btn_version_chip.text()
    assert top_bar.btn_notifications.text() == "🔔"
    print(f"   • Initial TopBar: Version='{top_bar.btn_version_chip.text()}', Bell='{top_bar.btn_notifications.text()}'")

    # Apply fleet notification
    target_ver = notif_payload.get("target_version", "2.9.4")
    top_bar.set_update_available(target_ver)
    top_bar.set_notification_badge(True)
    if hasattr(main_win, "update_banner"):
        main_win.update_banner.show_downloading(target_ver)

    # Verify updated UI state
    print(f"   • Updated TopBar: Version='{top_bar.btn_version_chip.text()}', Bell='{top_bar.btn_notifications.text()}'")
    assert "UPDATE" in top_bar.btn_version_chip.text()
    assert target_ver in top_bar.btn_version_chip.toolTip()
    assert "•" in top_bar.btn_notifications.text()
    assert main_win.update_banner.isHidden() == False
    print(f"   ✓ TopBar version pill transformed to emerald update badge.")
    print(f"   ✓ Notification bell transformed to amber unread dot.")
    print(f"   ✓ UpdateBanner is active and rendering target version v{target_ver}.")

    # 4. Test UpdateCenterDialog with Manifest Update
    print("\n4. Testing UpdateCenterDialog Modal Execution:")
    update_dlg = UpdateCenterDialog(parent=main_win)
    manifest_data = {
        "version": target_ver,
        "latest_version": target_ver,
        "download_url": "https://talent-ops-ai.vercel.app/download-scout",
        "release_notes": "Official release notes for v2.9.4: Added interactive version renewing and notifications."
    }
    update_dlg._apply_manifest_result(manifest_data)
    assert update_dlg.btn_update.isEnabled() == True
    assert target_ver in update_dlg.btn_update.text()
    assert target_ver in update_dlg.lbl_status.text()
    assert "v2.9.4" in update_dlg.lbl_notes.text()
    print(f"   ✓ UpdateCenterDialog status: '{update_dlg.lbl_status.text()}'")
    print(f"   ✓ Update action button enabled: '{update_dlg.btn_update.text()}'")

    # 5. Test NotificationsDialog with Live Fleet Broadcasts
    print("\n5. Testing NotificationsDialog Modal Execution:")
    notif_dlg = NotificationsDialog(parent=main_win)
    test_notifs = [
        {
            "id": 101,
            "title": "Platform Release v2.9.3 Synchronized",
            "type": "UPDATE",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": "Desktop Scout v2.9.3 is live with real-time notifications.",
            "read": False
        },
        {
            "id": 102,
            "title": "Staged Discovery Approved",
            "type": "SUCCESS",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": "Your observed candidate at OpenAI was approved and promoted.",
            "read": False
        }
    ]
    notif_dlg._render_notifications(test_notifs)
    assert len(notif_dlg.notifications) == 2
    print(f"   ✓ NotificationsDialog rendered {len(notif_dlg.notifications)} active cards.")
    
    # Simulate user clicking Mark Read
    top_bar.set_notification_badge(False)
    assert top_bar.btn_notifications.text() == "🔔"
    print("   ✓ Unread badge cleared upon user acknowledgement.")

    print("\n>>> CHECK 2 PASSED: Desktop Scout Client Runtime & Fleet Broadcast Verified!")

finally:
    # Cleanup broadcast
    db.query(ScoutFleetBroadcast).filter(ScoutFleetBroadcast.broadcast_id == bc_id).delete()
    db.commit()
    invalidate_active_broadcast_cache()
    db.close()
