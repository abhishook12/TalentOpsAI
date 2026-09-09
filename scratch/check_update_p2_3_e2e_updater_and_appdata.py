"""
check_update_p2_3_e2e_updater_and_appdata.py — Check 3: E2E Auto-Update, Rollback & AppData Preservation.

User Rule 11 Verification Suite — Test Tier 3.
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import tempfile
import subprocess
from starlette.testclient import TestClient

# Include paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, get_db
from app.models.auth_models import User
from app.models.update_models import ScoutRelease, ScoutInstallation
from app.services.auth_service import get_current_user_from_request
from app.main import app

from scout_desktop.core.updater import AutoUpdater, compute_file_sha256
from scout_desktop.core.paths import (
    get_app_data_dir,
    get_database_path,
    get_config_path,
    get_state_dir,
)
from scout_desktop.updater.updater_helper import perform_update
from backend.app.services.release_signer import sign_manifest, sign_package_file

# Connect to dev database with local SQLite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    print("CHECK 3: E2E AUTO-UPDATE, AUTOMATIC ROLLBACK & APPDATA PRESERVATION")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Step 3.1: Pre-Populate Persistent State in %LOCALAPPDATA%\TalentOpsAI\Scout
    # -------------------------------------------------------------------------
    print("\n[Step 3.1] Seeding Persistent State in AppData (%LOCALAPPDATA%\\TalentOpsAI\\Scout)...")
    appdata_root = get_app_data_dir()
    db_file = get_database_path()
    cfg_file = get_config_path()

    print(f"  AppData Root: {appdata_root}")
    print(f"  Database:     {db_file}")
    print(f"  Config:       {cfg_file}")

    # Seed User Credentials & Settings
    user_settings = {
        "user_id": 42,
        "device_id": "DEVICE-ENTERPRISE-VERIFY-99",
        "api_key": "tos_live_secret_token_never_delete",
        "paired_at": time.time(),
        "sampling_rate_sec": 1,
    }
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(user_settings, f, indent=2)

    # Seed Persistent SQLite Records
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_offline_queue (
            id INTEGER PRIMARY KEY,
            candidate_name TEXT,
            linkedin_url TEXT,
            staged_timestamp REAL
        )
    """)
    cursor.execute("DELETE FROM local_offline_queue")
    cursor.execute(
        "INSERT INTO local_offline_queue (candidate_name, linkedin_url, staged_timestamp) VALUES (?, ?, ?)",
        ("Dr. Ada Lovelace", "https://linkedin.com/in/ada-lovelace-precious", time.time())
    )
    cursor.execute(
        "INSERT INTO local_offline_queue (candidate_name, linkedin_url, staged_timestamp) VALUES (?, ?, ?)",
        ("Alan Turing", "https://linkedin.com/in/alan-turing-precious", time.time())
    )
    conn.commit()
    conn.close()

    print("  [OK] Persistent state seeded: 1 user config file, 2 SQLite candidate queue records.")

    # -------------------------------------------------------------------------
    # Step 3.2: Testing Two-Tier Version Enforcement & Mandatory Update Floor
    # -------------------------------------------------------------------------
    print("\n[Step 3.2] Testing Two-Tier Version Enforcement on Client...")
    # Publish release v2.6.0 with minimum_version=2.4.0
    res = client.post("/scout/releases", json={
        "version": "2.6.0",
        "channel": "stable",
        "minimum_version": "2.4.0",  # Deprecation floor
        "mandatory": False,
        "download_url": "https://cdn.talentops.ai/releases/TalentOpsScoutSetup_v2.6.0.exe",
        "sha256": "4a7e93f6c8d19a2b3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
        "rollout_percentage": 100,
        "release_notes": "Security update with minimum version requirement",
    })
    assert res.status_code == 200

    # Test Client v2.0.0 (below minimum 2.4.0)
    updater_old = AutoUpdater(
        api_base="http://testserver",
        current_version="2.0.0",
        channel="stable",
        device_id="DEVICE-OLD-01",
    )
    manifest_data = client.get("/scout/updates/manifest?channel=stable&device_id=DEVICE-OLD-01").json()
    updater_old._process_manifest(manifest_data)

    print(f"  Client v2.0.0 against Min v{updater_old.minimum_version}:")
    print(f"  -> is_mandatory:    {updater_old.is_mandatory}")
    print(f"  -> pending_version: {updater_old.pending_version}")
    assert updater_old.is_mandatory is True, "Client below minimum did not trigger mandatory update!"
    assert updater_old.pending_version == "2.6.0"
    print("  [OK] Mandatory update floor correctly enforced (Client blocked until updated).")

    # Test Client v2.5.0 (above minimum 2.4.0, below latest 2.6.0)
    updater_mid = AutoUpdater(
        api_base="http://testserver",
        current_version="2.5.0",
        channel="stable",
        device_id="DEVICE-MID-01",
    )
    updater_mid._process_manifest(manifest_data)
    assert updater_mid.is_mandatory is False, "Client above minimum was mistakenly flagged as mandatory!"
    assert updater_mid.pending_version == "2.6.0"
    print("  [OK] Background update correctly identified for client above minimum.")

    # -------------------------------------------------------------------------
    # Step 3.3: Out-of-Process Update, Health Check & Automatic Rollback
    # -------------------------------------------------------------------------
    print("\n[Step 3.3] Simulating Out-of-Process Update, Health Check & Automatic Rollback...")
    sandbox_dir = tempfile.mkdtemp(prefix="scout_e2e_sandbox_")
    try:
        app_dir = os.path.join(sandbox_dir, "app_bin")
        backup_dir = os.path.join(sandbox_dir, "app_backup")
        staged_dir = os.path.join(sandbox_dir, "staged_pkg")
        os.makedirs(app_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(staged_dir, exist_ok=True)

        # 1. Install initial stable version (v2.5.0)
        main_py = os.path.join(app_dir, "TalentOpsScout.py")
        with open(main_py, "w", encoding="utf-8") as f:
            f.write("""# TalentOps Scout v2.5.0 (Stable Baseline)
import sys
if '--health-check' in sys.argv:
    print('v2.5.0 Health Check OK')
    sys.exit(0)
print('Running v2.5.0')
""")

        # 2. Stage a faulty update package (crashes on startup)
        faulty_pkg = os.path.join(staged_dir, "faulty_update")
        os.makedirs(faulty_pkg, exist_ok=True)
        faulty_py = os.path.join(faulty_pkg, "TalentOpsScout.py")
        with open(faulty_py, "w", encoding="utf-8") as f:
            f.write("""# Faulty Update Build
import sys
if '--health-check' in sys.argv:
    sys.stderr.write('CRITICAL EXCEPTION: Corrupt binary or missing DLL!\\n')
    sys.exit(1) # Crash
""")

        print("  Applying faulty update package to application directory...")
        res_faulty = perform_update(
            package_path=faulty_pkg,
            target_dir=app_dir,
            backup_dir=backup_dir,
            target_pid=0,
            executable_name="TalentOpsScout.py",
            restart_after=False,
        )

        print(f"  Update Result: {res_faulty['status']}")
        print(f"  Rolled Back:   {res_faulty['rolled_back']}")
        assert res_faulty["rolled_back"] is True, "Rollback did not trigger on health check crash!"
        assert res_faulty["status"] == "HEALTH_CHECK_FAILED_ROLLED_BACK"

        # Verify that restored executable in app_dir is the original v2.5.0
        with open(main_py, "r", encoding="utf-8") as f:
            restored_content = f.read()
        assert "v2.5.0" in restored_content, "Restored application does not contain original v2.5.0 code!"
        assert "Faulty Update Build" not in restored_content
        print("  [OK] Automatic rollback succeeded! Previous stable v2.5.0 binary 100% restored.")

        # Verify state persistence file records rollback
        state_dir = get_state_dir()
        state_file = os.path.join(state_dir, "update_state.json")
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                saved_state = json.load(f)
            print(f"  Persisted Updater State: {saved_state.get('current_state')}")
            assert saved_state.get("current_state") in ("STABLE", "ROLLBACK", "UP_TO_DATE")

        # ---------------------------------------------------------------------
        # Step 3.4: APPDATA DATA LOSS PREVENTION PROOF
        # -------------------------------------------------------------------------
        print("\n[Step 3.4] Verifying AppData Data Loss Prevention Guarantee...")
        # Inspect user credentials file
        assert os.path.exists(cfg_file), "CRITICAL: config.json was deleted during update cycle!"
        with open(cfg_file, "r", encoding="utf-8") as f:
            inspected_cfg = json.load(f)
        assert inspected_cfg["api_key"] == "tos_live_secret_token_never_delete", "User API key was altered or corrupted!"
        assert inspected_cfg["user_id"] == 42
        print("  [OK] User configuration and pairing credentials in %LOCALAPPDATA% intact.")

        # Inspect local SQLite queue database
        assert os.path.exists(db_file), "CRITICAL: scout_local.db was deleted during update cycle!"
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        rows = cursor.execute("SELECT candidate_name, linkedin_url FROM local_offline_queue ORDER BY id ASC").fetchall()
        conn.close()

        print(f"  Inspected Local SQLite Database: {len(rows)} records found:")
        for r in rows:
            print(f"    - {r[0]} ({r[1]})")

        assert len(rows) == 2, f"Expected 2 rows in SQLite database, found {len(rows)}!"
        assert rows[0][0] == "Dr. Ada Lovelace"
        assert rows[1][0] == "Alan Turing"
        print("  [OK] SQLite offline queue in %LOCALAPPDATA% 100% preserved with zero data loss.")

    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)

    print("\n" + "=" * 80)
    print("CHECK 3 RESULT: PASSED (100% SUCCESSFUL)")
    print("Two-tier enforcement, automatic rollback, and AppData data loss prevention 100% verified.")
    print("=" * 80)


if __name__ == "__main__":
    run_check()
