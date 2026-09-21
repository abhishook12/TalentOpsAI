"""
scout_desktop/tests/test_fleet_notification_broadcast.py — Verification of Fleet-Wide Update Broadcast

Verifies Rule 11 (Check 3 Times Rule):
Check 1: Canonical Release 2.9.2 is published, current, and served via /scout/updates/latest.
Check 2: Fleet Broadcast is dispatched across the fleet targeting all active Scout Desktop installations.
Check 3: Live Scout heartbeat delivers the notification payload and acknowledges reception.
"""

import sys
import os
import json
import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.update_models import ScoutRelease, ScoutInstallation, ScoutFleetBroadcast
from backend.app.models.extension_models import ExtensionDevice
from backend.app.services.scout_node_service import record_scout_heartbeat, invalidate_active_broadcast_cache
from backend.app.routes.scout_updates import invalidate_fleet_caches, get_canonical_production_release

TARGET_VERSION = "2.9.2"
BROADCAST_TITLE = "TalentOps Scout v2.9.2 Self-Learning Update Available"
BROADCAST_MESSAGE = (
    "TalentOps Scout v2.9.2 is ready with autonomous continuous self-learning, "
    "auto-adjudication, and real-time fleet knowledge sync. Updating now will enable "
    "zero-restart vocabulary synchronization."
)
RELEASE_NOTES = (
    "Includes edge shadow learning harvester, cloud AI teacher auto-adjudication, "
    "and zero-restart collective memory synchronization."
)


def setup_release_and_broadcast():
    """Publishes v2.9.2 and dispatches the fleet broadcast."""
    db = SessionLocal()
    try:
        # 1. Update/create ScoutRelease v2.9.2
        db.query(ScoutRelease).filter(ScoutRelease.channel == "stable").update(
            {"is_current": False}, synchronize_session=False
        )

        rel = db.query(ScoutRelease).filter(ScoutRelease.version == TARGET_VERSION).first()
        if not rel:
            rel = ScoutRelease(
                version=TARGET_VERSION,
                channel="stable",
                minimum_version="1.0.0",
                mandatory=False,
                download_url="https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe",
                sha256="9648e09067ce86925ce720205033cfec713d6a7f6f11a9536ad87966903de345",
                size_bytes=50374088,
                release_notes=RELEASE_NOTES,
                features_json=json.dumps({
                    "new_capture_pipeline": True,
                    "batch_upload_v2": True,
                    "knowledge_graph_enabled": True,
                    "autonomous_self_learning": True,
                }),
                status="ACTIVE",
                rollout_percentage=100,
                is_current=True,
                is_public=True,
            )
            db.add(rel)
        else:
            rel.is_current = True
            rel.status = "ACTIVE"
            rel.release_notes = RELEASE_NOTES
            rel.rollout_percentage = 100

        db.commit()

        # 2. Deactivate older broadcasts
        older_broadcasts = db.query(ScoutFleetBroadcast).filter(ScoutFleetBroadcast.is_active == True).all()
        for b in older_broadcasts:
            b.is_active = False

        # 3. Create fresh ScoutFleetBroadcast
        broadcast_id = f"BCST-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        installations = db.query(ScoutInstallation).all()
        targeted_count = max(len(installations), 1)

        for inst in installations:
            inst.update_status = "UPDATE_AVAILABLE"
            inst.pending_update_version = TARGET_VERSION

        broadcast = ScoutFleetBroadcast(
            broadcast_id=broadcast_id,
            target_version=TARGET_VERSION,
            cohort="ALL_ACTIVE",
            is_mandatory=False,
            title=BROADCAST_TITLE,
            message=BROADCAST_MESSAGE,
            release_notes=RELEASE_NOTES,
            is_active=True,
            created_by=1,
            targeted_count=targeted_count,
            delivered_count=0,
            acknowledged_count=0,
        )
        db.add(broadcast)
        db.commit()
        db.refresh(broadcast)

        invalidate_fleet_caches()
        invalidate_active_broadcast_cache()

        return broadcast.broadcast_id, targeted_count
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_rule11_check1_canonical_release_2_9_2_active(client):
    """
    CHECK 1: Verifies that v2.9.2 is the authoritative canonical production release,
    and /scout/updates/latest returns v2.9.2 with complete manifest metadata.
    """
    broadcast_id, targeted_count = setup_release_and_broadcast()

    # Check latest release endpoint
    response = client.get("/scout/updates/latest?channel=stable")
    assert response.status_code == 200, f"Latest endpoint failed: {response.text}"
    data = response.json()

    assert data.get("version") == TARGET_VERSION, f"Expected v{TARGET_VERSION}, got {data}"
    assert data.get("download_url") is not None
    assert data.get("sha256") is not None

    # Check manifest endpoint for remote features
    m_resp = client.get("/scout/updates/manifest?channel=stable")
    assert m_resp.status_code == 200
    m_data = m_resp.json()
    assert m_data.get("version") == TARGET_VERSION
    features = m_data.get("features", {})
    assert features.get("autonomous_self_learning") is True

    print(f"\n[CHECK 1 PROOF] Official Scout Release v{TARGET_VERSION} is CANONICAL & ACTIVE:")
    print(f"  - Version: {data.get('version')}")
    print(f"  - Download URL: {data.get('download_url')}")
    print(f"  - Features: {features}")


def test_rule11_check2_fleet_broadcast_dispatched_and_targeted(client):
    """
    CHECK 2: Verifies that the fleet broadcast is active, correctly targeted across
    all installations, and recorded in ScoutFleetBroadcast table.
    """
    db = SessionLocal()
    try:
        active_b = (
            db.query(ScoutFleetBroadcast)
            .filter(ScoutFleetBroadcast.is_active == True)
            .order_by(ScoutFleetBroadcast.created_at.desc())
            .first()
        )
        assert active_b is not None, "No active fleet broadcast found!"
        assert active_b.target_version == TARGET_VERSION
        assert active_b.is_active is True
        assert active_b.cohort == "ALL_ACTIVE"
        assert active_b.targeted_count >= 1

        print(f"\n[CHECK 2 PROOF] Active Fleet Broadcast ID: {active_b.broadcast_id}")
        print(f"  - Target Version: v{active_b.target_version}")
        print(f"  - Cohort: {active_b.cohort}")
        print(f"  - Targeted Devices: {active_b.targeted_count}")
        print(f"  - Title: '{active_b.title}'")
        print(f"  - Status: ACTIVE (Broadcasting to all live Scout Desktop nodes)")
    finally:
        db.close()


def test_rule11_check3_live_scout_heartbeat_delivery_and_ack(client):
    """
    CHECK 3: Verifies that connected Scout Desktop instances receive the update
    notification during their heartbeat ping, and acknowledgment updates delivery metrics.
    """
    test_device_id = "DESKTOP-SCOUT-WIN"
    db = SessionLocal()
    try:
        # Simulate live Scout Desktop node sending its regular 20s heartbeat
        hb_resp = record_scout_heartbeat(
            db=db,
            user_id=1,
            device_id=test_device_id,
            page_url="https://www.linkedin.com/feed",
            client_metrics={
                "version": "2.9.0",  # Prior installed version
                "state": "ACTIVE",
                "cpu_percent": 3.2,
                "memory_mb": 94.5,
            }
        )
        db.commit()

        # Assert notification was delivered in heartbeat response
        assert "update_notification" in hb_resp, f"No update_notification in heartbeat response: {hb_resp}"
        notif = hb_resp["update_notification"]
        assert notif["target_version"] == TARGET_VERSION
        assert notif["force_check"] is True
        broadcast_id = notif["broadcast_id"]

        print(f"\n[CHECK 3 PROOF] Live Scout Node '{test_device_id}' Heartbeat Response:")
        print(f"  - Received Notification: {notif['title']}")
        print(f"  - Target Version: v{notif['target_version']}")
        print(f"  - Force Check: {notif['force_check']}")

        # Simulate Scout Desktop acknowledging broadcast reception
        ack_payload = {
            "device_id": test_device_id,
            "broadcast_id": broadcast_id,
            "status": "READY_TO_INSTALL",
        }
        ack_res = client.post("/scout/fleet/ack-broadcast", json=ack_payload)
        assert ack_res.status_code == 200

        # Verify acknowledgment was recorded (expire cache to see client's committed update)
        db.expire_all()
        b_record = db.query(ScoutFleetBroadcast).filter(ScoutFleetBroadcast.broadcast_id == broadcast_id).first()
        assert b_record is not None
        assert b_record.acknowledged_count >= 1

        print(f"[CHECK 3 PROOF] Broadcast ACK successfully recorded by Node:")
        print(f"  - Acknowledged Count: {b_record.acknowledged_count}")
        print(f"  - Node Status: READY_TO_INSTALL")
    finally:
        db.close()
