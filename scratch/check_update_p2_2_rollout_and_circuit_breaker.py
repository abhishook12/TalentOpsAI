"""
check_update_p2_2_rollout_and_circuit_breaker.py — Check 2: Staged Rollouts, Circuit Breaker & Node Health.

User Rule 11 Verification Suite — Test Tier 2.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.auth_models import User
from app.models.update_models import ScoutRelease, ScoutInstallation
from app.services.auth_service import get_current_user_from_request
from app.main import app

# 1. Connect to dev database with all models
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "dev.db"))
engine = create_engine(f"sqlite:///{db_path}")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
test_db = Session()

def override_get_db():
    try:
        yield test_db
    finally:
        pass

# Create mock admin user for authenticated endpoints
mock_admin = test_db.query(User).filter(User.email == "admin@talentops.ai").first()
if not mock_admin:
    mock_admin = User(
        email="admin@talentops.ai",
        password_hash="mock_hash",
        first_name="Admin",
        last_name="Commander",
        status="active",
    )
    test_db.add(mock_admin)
    test_db.commit()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_from_request] = lambda: mock_admin
client = TestClient(app)


def run_check():
    print("=" * 80)
    print("CHECK 2: STAGED ROLLOUT ENGINE, CIRCUIT BREAKER & NODE HEALTH MODEL")
    print("=" * 80)

    db = test_db
    try:
        # Clear existing test data in Scout tables
        db.query(ScoutInstallation).delete()
        db.query(ScoutRelease).delete()
        db.commit()

        # ---------------------------------------------------------------------
        # Step 2.1: Publish Baseline Stable Release (v2.5.0, 100% rollout)
        # ---------------------------------------------------------------------
        print("\n[Step 2.1] Publishing Baseline Stable Release v2.5.0 (100% Rollout)...")
        res = client.post("/scout/releases", json={
            "version": "2.5.0",
            "channel": "stable",
            "minimum_version": "2.2.0",
            "mandatory": False,
            "download_url": "https://cdn.talentops.ai/releases/TalentOpsScoutSetup_v2.5.0.exe",
            "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
            "rollout_percentage": 100,
            "failure_threshold_pct": 3.0,
            "release_notes": "Stable baseline release",
        })
        assert res.status_code == 200, f"Failed to publish v2.5.0: {res.text}"
        data = res.json()
        assert data["signature"] is not None, "Manifest was not automatically signed!"
        print(f"  [OK] v2.5.0 published with digital signature: {data['signature'][:20]}...")

        # ---------------------------------------------------------------------
        # Step 2.2: Staged Rollout Cohort Gating (v2.6.0 at 25% Rollout)
        # ---------------------------------------------------------------------
        print("\n[Step 2.2] Publishing Staged Release v2.6.0 (25% Rollout Cohort)...")
        res = client.post("/scout/releases", json={
            "version": "2.6.0",
            "channel": "stable",
            "minimum_version": "2.2.0",
            "mandatory": False,
            "download_url": "https://cdn.talentops.ai/releases/TalentOpsScoutSetup_v2.6.0.exe",
            "sha256": "2222222222222222222222222222222222222222222222222222222222222222",
            "rollout_percentage": 25,  # Gated to 25% of nodes
            "failure_threshold_pct": 3.0,
            "release_notes": "Staged 25% rollout for performance validation",
        })
        assert res.status_code == 200

        # Query manifest across 100 deterministic device IDs
        received_v26 = 0
        received_v25 = 0

        for i in range(100):
            dev_id = f"TEST-DEVICE-{i:03d}"
            r = client.get(f"/scout/updates/manifest?channel=stable&device_id={dev_id}")
            assert r.status_code == 200
            m = r.json()
            if m["latest_version"] == "2.6.0":
                received_v26 += 1
            elif m["latest_version"] == "2.5.0":
                received_v25 += 1

        print(f"  Rollout Evaluation over 100 test devices:")
        print(f"  -> v2.6.0 (Target Cohort 25%): {received_v26} devices ({received_v26}%)")
        print(f"  -> v2.5.0 (Fallback Cohort):  {received_v25} devices ({received_v25}%)")
        assert 15 <= received_v26 <= 35, f"Rollout gating out of expected range: {received_v26}%"
        print("  [OK] Staged rollout deterministic hashing verified within expected distribution.")

        # ---------------------------------------------------------------------
        # Step 2.3: Automated Rollout Circuit Breaker (>3% Failure Rate Trigger)
        # ---------------------------------------------------------------------
        print("\n[Step 2.3] Testing Automated Rollout Circuit Breaker (>3% Failure Rate)...")
        # Publish v2.7.0 with 3% failure threshold
        res = client.post("/scout/releases", json={
            "version": "2.7.0",
            "channel": "beta",
            "minimum_version": "2.2.0",
            "mandatory": False,
            "download_url": "https://cdn.talentops.ai/releases/TalentOpsScoutSetup_v2.7.0.exe",
            "sha256": "3333333333333333333333333333333333333333333333333333333333333333",
            "rollout_percentage": 100,
            "failure_threshold_pct": 3.0,
            "release_notes": "Beta release with circuit breaker test",
        })
        assert res.status_code == 200

        # Simulate 10 successful updates
        for i in range(10):
            client.post("/scout/updates/report", json={
                "device_id": f"DEV-BETA-OK-{i}",
                "scout_version": "2.7.0",
                "channel": "beta",
                "update_status": "SUCCESS",
                "target_version": "2.7.0",
            })

        # Check release stats: 10 successes, 0 failures -> failure_rate = 0.0%
        rel_27 = db.query(ScoutRelease).filter(ScoutRelease.version == "2.7.0").first()
        db.refresh(rel_27)
        assert rel_27.is_paused is False
        assert rel_27.failure_rate == 0.0
        print(f"  Reported 10 successful updates. Release v2.7.0 is_paused: {rel_27.is_paused} (Failure Rate: 0%)")

        # Now simulate 2 failures: total = 12, failures = 2 -> 2/12 = 16.7% (> 3.0% threshold)
        print("  Injecting 2 update failures (crashes during health check)...")
        for i in range(2):
            client.post("/scout/updates/report", json={
                "device_id": f"DEV-BETA-FAIL-{i}",
                "scout_version": "2.6.0",
                "channel": "beta",
                "update_status": "HEALTH_CHECK_FAILED",
                "error_message": "Process crashed on startup: missing DLL dependency",
                "target_version": "2.7.0",
            })

        # Refresh from DB
        db.refresh(rel_27)
        print(f"  Telemetry updated -> Successes: {rel_27.success_count}, Failures: {rel_27.failure_count}")
        print(f"  Computed Failure Rate: {rel_27.failure_rate}% (Safety Threshold: {rel_27.failure_threshold_pct}%)")
        print(f"  Release Status: {rel_27.status} | is_paused: {rel_27.is_paused}")

        assert rel_27.is_paused is True, "Circuit breaker failed to pause release!"
        assert rel_27.status == "CIRCUIT_TRIPPED", "Status not set to CIRCUIT_TRIPPED!"
        print("  [OK] Circuit breaker successfully tripped and automatically PAUSED rollout.")

        # Verify that subsequent manifest requests for beta channel now fallback because v2.7.0 is paused
        r_paused = client.get("/scout/updates/manifest?channel=beta&device_id=DEV-NEW-01")
        m_paused = r_paused.json()
        assert m_paused["latest_version"] != "2.7.0", "Paused release was served to clients!"
        print(f"  [OK] Client manifest query safely redirected to earlier release (Served: v{m_paused['latest_version']}).")

        # ---------------------------------------------------------------------
        # Step 2.4: Node Health Model Classification
        # ---------------------------------------------------------------------
        print("\n[Step 2.4] Testing Node Health Classification (Healthy, Stale, Failed, Offline)...")
        now = datetime.now(timezone.utc)

        # Clear and seed nodes with specific lifecycle states
        db.query(ScoutInstallation).delete()
        db.commit()

        # 1. Healthy Node (Recent heartbeat 2m ago, UP_TO_DATE)
        n_healthy = ScoutInstallation(
            device_id="NODE-HEALTHY-01",
            scout_version="2.5.0",
            channel="stable",
            update_status="UP_TO_DATE",
            health_status="HEALTHY",
            last_seen=now - timedelta(minutes=2),
            last_check_at=now - timedelta(minutes=2),
        )

        # 2. Stale Node (Heartbeat 25m ago)
        n_stale = ScoutInstallation(
            device_id="NODE-STALE-01",
            scout_version="2.5.0",
            channel="stable",
            update_status="UP_TO_DATE",
            health_status="STALE",
            last_seen=now - timedelta(minutes=25),
            last_check_at=now - timedelta(minutes=25),
        )

        # 3. Update Failed Node
        n_failed = ScoutInstallation(
            device_id="NODE-FAILED-01",
            scout_version="2.4.0",
            channel="stable",
            update_status="HEALTH_CHECK_FAILED",
            health_status="UPDATE_FAILED",
            last_error="Crash on boot",
            last_seen=now - timedelta(minutes=1),
            last_check_at=now - timedelta(minutes=1),
        )

        # 4. Offline Node (Heartbeat 3 days ago)
        n_offline = ScoutInstallation(
            device_id="NODE-OFFLINE-01",
            scout_version="2.0.0",
            channel="stable",
            update_status="UP_TO_DATE",
            health_status="OFFLINE",
            last_seen=now - timedelta(days=3),
            last_check_at=now - timedelta(days=3),
        )

        db.add_all([n_healthy, n_stale, n_failed, n_offline])
        db.commit()

        # Query GET /scout/fleet/stats
        stats_res = client.get("/scout/fleet/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()

        print("  Fleet Health Analytics Summary:")
        print(f"  -> Total Devices:    {stats['total_devices']}")
        print(f"  -> Healthy:          {stats['node_health']['healthy']}")
        print(f"  -> Stale:            {stats['node_health']['stale']}")
        print(f"  -> Failed:           {stats['node_health']['failed']}")
        print(f"  -> Offline:          {stats['node_health']['offline']}")
        print(f"  -> Update Required:  {stats['node_health']['update_required']} (v2.0.0 < min v2.2.0)")

        assert stats["total_devices"] == 4
        assert stats["node_health"]["healthy"] == 1
        assert stats["node_health"]["stale"] == 1
        assert stats["node_health"]["failed"] == 1
        assert stats["node_health"]["offline"] == 1
        assert stats["node_health"]["update_required"] == 1
        print("  [OK] Node health categorization (Healthy, Stale, Failed, Offline, Update Required) 100% verified.")

        # ---------------------------------------------------------------------
        # Step 2.5: Admin Manual Override & Rollout Promotion
        # ---------------------------------------------------------------------
        print("\n[Step 2.5] Testing Admin Manual Override & Rollout Promotion...")
        # Un-pause v2.7.0 and promote rollout to 100%
        res_ctrl = client.post("/scout/releases/2.7.0/rollout", json={
            "rollout_percentage": 100,
            "is_paused": False,
        })
        assert res_ctrl.status_code == 200
        ctrl_data = res_ctrl.json()
        assert ctrl_data["is_paused"] is False
        assert ctrl_data["rollout_percentage"] == 100
        assert ctrl_data["status"] == "ACTIVE"
        print(f"  [OK] Admin override successfully unpaused v2.7.0 and promoted rollout to 100%.")

        print("\n" + "=" * 80)
        print("CHECK 2 RESULT: PASSED (100% SUCCESSFUL)")
        print("Staged rollout cohorting, circuit breaker auto-pause, and node health verified.")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_check()
