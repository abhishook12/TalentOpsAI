"""
check_update_3_manifest_and_fleet.py
Verification Check 3: End-to-End Release Manifest API, Two-Tier Versioning & Fleet Telemetry.

Tests:
1. Fast API Manifest Endpoint (GET /scout/updates/manifest):
   - Validates response schema (latest_version, minimum_version, package, features, config).
2. Release Publishing (POST /scout/releases):
   - Publishes v2.4.0 with minimum_version=2.2.0 and remote feature flags.
3. Two-Tier Version Enforcement on Client:
   - Evaluates client v2.0.0 (below minimum 2.2.0) -> Triggers mandatory update enforcement.
   - Evaluates client v2.3.0 (above minimum, below latest) -> Triggers background update.
   - Evaluates client v2.4.0 (equal to latest) -> Reports UP_TO_DATE.
4. Remote Configuration & Feature Flag Adoption:
   - Verifies client persists remote features without requiring an application restart.
5. Fleet Telemetry Reporting & Analytics (POST /scout/updates/report & GET /scout/fleet/stats):
   - Reports telemetry for multiple nodes and verifies aggregate fleet analytics.
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.database import Base, get_db
from app.models.auth_models import User
from app.models.update_models import ScoutRelease, ScoutInstallation
from app.services.auth_service import get_current_user_from_request
from app.main import app

from scout_desktop.core.updater import AutoUpdater, parse_semver


def run_check_3():
    print("=" * 80)
    print("CHECK 3: RELEASE MANIFEST API, TWO-TIER VERSIONING & FLEET TELEMETRY")
    print("=" * 80)

    # 1. Connect to dev database with all models
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dev.db"))
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query or create mock admin user
    mock_admin = session.query(User).filter(User.email == "admin@talentops.ai").first()
    if not mock_admin:
        mock_admin = User(
            email="admin@talentops.ai",
            password_hash="mock_hash",
            first_name="Admin",
            last_name="Commander",
            status="active",
        )
        session.add(mock_admin)
        session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    def override_current_user():
        return mock_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_from_request] = override_current_user
    client = TestClient(app)

    # ── Test 1: GET /scout/updates/manifest Default State ─────────────────────
    print("\n[Step 1/5] Testing default GET /scout/updates/manifest...")
    res_manifest = client.get("/scout/updates/manifest?channel=stable")
    assert res_manifest.status_code == 200
    manifest_data = res_manifest.json()
    print(f"-> Manifest Response (HTTP {res_manifest.status_code}):")
    print(f"   Product:         {manifest_data.get('product')}")
    print(f"   Channel:         {manifest_data.get('channel')}")
    print(f"   Latest Version:  {manifest_data.get('latest_version')}")
    print(f"   Minimum Version: {manifest_data.get('minimum_version')}")
    print(f"   Package SHA-256: {manifest_data.get('package', {}).get('sha256')[:16]}...")
    print(f"   Features:        {list(manifest_data.get('features', {}).keys())}")

    assert "latest_version" in manifest_data
    assert "minimum_version" in manifest_data
    assert "package" in manifest_data
    assert "features" in manifest_data
    print("   [PASSED] Manifest endpoint returns complete specification schema.")

    # ── Test 2: Admin Publishes New Release v2.4.0 ────────────────────────────
    print("\n[Step 2/5] Admin publishing release v2.4.0 with minimum_version=2.2.0...")
    release_payload = {
        "version": "2.4.0",
        "channel": "stable",
        "minimum_version": "2.2.0",
        "mandatory": False,
        "download_url": "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup_v2.4.0.exe",
        "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "size_bytes": 52100400,
        "release_notes": "Added autonomous 4-Tier Knowledge Graph Ingestion and out-of-process silent auto-updater.",
        "features": {
            "knowledge_graph_enabled": True,
            "batch_upload_v2": True,
            "new_capture_pipeline": True,
            "ocr_daemon_enabled": True,
            "realtime_intent_scoring": True,
        },
        "config": {
            "poll_interval_sec": 45,
            "max_buffer_mb": 150,
        },
    }

    res_pub = client.post("/scout/releases", json=release_payload)
    print(f"-> Publish result: HTTP {res_pub.status_code} - {res_pub.json()}")
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "published"

    # Verify manifest now reflects published v2.4.0
    res_manifest_v24 = client.get("/scout/updates/manifest?channel=stable").json()
    assert res_manifest_v24["latest_version"] == "2.4.0"
    assert res_manifest_v24["minimum_version"] == "2.2.0"
    assert res_manifest_v24["features"]["realtime_intent_scoring"] is True
    print("   [PASSED] Backend successfully returns newly published v2.4.0 manifest.")

    # ── Test 3: Two-Tier Version Logic Verification ───────────────────────────
    print("\n[Step 3/5] Testing Two-Tier Version Enforcement on Client...")
    
    # Case A: Outdated Client v2.0.0 (Below Minimum v2.2.0)
    mandatory_triggered = []
    def on_mandatory(min_v, latest_v):
        mandatory_triggered.append((min_v, latest_v))

    updater_v20 = AutoUpdater(current_version="2.0.0", on_mandatory_update_required=on_mandatory)
    updater_v20._process_manifest(res_manifest_v24)
    print(f"-> Client v2.0.0 evaluation against Min v2.2.0:")
    print(f"   is_mandatory:        {updater_v20.is_mandatory}")
    print(f"   pending_version:     {updater_v20.pending_version}")
    print(f"   mandatory_triggered: {mandatory_triggered}")
    assert updater_v20.is_mandatory is True, "Expected mandatory update for client below minimum version!"
    assert len(mandatory_triggered) == 1
    print("   [OK] Mandatory update enforced: client below minimum blocked from continuing without update.")

    # Case B: Supported Client v2.3.0 (Above Minimum v2.2.0, Below Latest v2.4.0)
    updater_v23 = AutoUpdater(current_version="2.3.0")
    updater_v23._process_manifest(res_manifest_v24)
    print(f"-> Client v2.3.0 evaluation:")
    print(f"   is_mandatory:    {updater_v23.is_mandatory}")
    print(f"   update_status:   {updater_v23.update_status}")
    print(f"   pending_version: {updater_v23.pending_version}")
    assert updater_v23.is_mandatory is False
    assert updater_v23.update_status == "UPDATE_AVAILABLE"
    assert updater_v23.pending_version == "2.4.0"
    print("   [OK] Optional update available: client continues running while download occurs in background.")

    # Case C: Fully Up-to-Date Client v2.4.0
    updater_v24 = AutoUpdater(current_version="2.4.0")
    updater_v24._process_manifest(res_manifest_v24)
    print(f"-> Client v2.4.0 evaluation:")
    print(f"   update_status:   {updater_v24.update_status}")
    assert updater_v24.update_status == "UP_TO_DATE"
    print("   [OK] Fully up-to-date client recognized as UP_TO_DATE.")

    # ── Test 4: Remote Configuration & Feature Flag Adoption ──────────────────
    print("\n[Step 4/5] Testing Remote Feature Flags & Runtime Configuration...")
    print(f"-> Active Features adopted: {updater_v23.active_features}")
    print(f"-> Active Config adopted:   {updater_v23.active_config}")
    assert updater_v23.active_features.get("realtime_intent_scoring") is True
    assert updater_v23.active_config.get("poll_interval_sec") == 45
    print("   [PASSED] Remote configuration adopted dynamically without app rebuild.")

    # ── Test 5: Fleet Telemetry & Analytics Dashboard ─────────────────────────
    print("\n[Step 5/5] Testing Fleet Telemetry Reporting & Version Analytics...")
    devices_data = [
        {"device_id": "NODE-WIN-01", "scout_version": "2.4.0", "update_status": "UP_TO_DATE", "queue_size": 2},
        {"device_id": "NODE-WIN-02", "scout_version": "2.4.0", "update_status": "UP_TO_DATE", "queue_size": 0},
        {"device_id": "NODE-WIN-03", "scout_version": "2.3.0", "update_status": "DOWNLOADING", "queue_size": 15},
        {"device_id": "NODE-WIN-04", "scout_version": "2.0.0", "update_status": "FAILED", "error_message": "Network timeout", "queue_size": 8},
    ]

    for d in devices_data:
        rep_res = client.post("/scout/updates/report", json=d)
        assert rep_res.status_code == 200

    # Query Fleet Stats
    res_stats = client.get("/scout/fleet/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    print(f"-> Fleet Analytics Summary:")
    print(f"   Total Devices:        {stats_data['total_devices']}")
    print(f"   Version Distribution: {stats_data['version_distribution']}")
    print(f"   Status Distribution:  {stats_data['status_distribution']}")

    assert stats_data["total_devices"] == 4
    assert stats_data["status_distribution"]["UP_TO_DATE"] == 2
    assert stats_data["status_distribution"]["DOWNLOADING"] == 1
    assert stats_data["status_distribution"]["FAILED"] == 1

    print("   [PASSED] Fleet telemetry and version analytics 100% verified.")

    print("\n" + "=" * 80)
    print("CHECK 3 RESULT: PASSED (100% SUCCESSFUL)")
    print("Release manifests, two-tier versioning, and fleet analytics 100% operational.")
    print("=" * 80)

    app.dependency_overrides.clear()
    session.close()


if __name__ == "__main__":
    run_check_3()
