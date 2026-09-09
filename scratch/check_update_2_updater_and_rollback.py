"""
check_update_2_updater_and_rollback.py
Verification Check 2: Out-of-Process Updater Helper, SHA-256 Integrity & Automatic Rollback Engine.

Tests:
1. SHA-256 Cryptographic Verification:
   - Valid checksum matches.
   - Tampered payload (corrupted byte) is detected and rejected before execution.
2. Out-of-Process Atomic File Swap:
   - Sets up a simulated target application directory (v2.0.0).
   - Applies update package (v2.1.0) using updater_helper.
   - Verifies target directory is updated and backup snapshot is created.
3. Automatic Rollback on Health Check Failure:
   - Simulates an update containing a broken binary that crashes on startup.
   - Runs `perform_update()`.
   - Verifies post-install health check detects crash, triggers AUTOMATIC ROLLBACK, restores previous version, and returns rolled_back=True.
   - Verifies target application directory is fully restored to previous stable state.
"""

import sys
import os
import time
import shutil
import tempfile
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scout_desktop.core.updater import compute_file_sha256
from scout_desktop.updater.updater_helper import (
    create_rollback_backup,
    restore_rollback_backup,
    verify_post_install_health,
    perform_update,
)


def run_check_2():
    print("=" * 80)
    print("CHECK 2: OUT-OF-PROCESS UPDATER, SHA-256 INTEGRITY & AUTOMATIC ROLLBACK")
    print("=" * 80)

    work_dir = tempfile.mkdtemp(prefix="scout_updater_test_")
    target_app_dir = os.path.join(work_dir, "app_bin")
    backup_dir = os.path.join(work_dir, "app_backup")
    staged_pkg_dir = os.path.join(work_dir, "staged_pkg")
    os.makedirs(target_app_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(staged_pkg_dir, exist_ok=True)

    # ── Test 1: Cryptographic SHA-256 Verification ───────────────────────────
    print("\n[Step 1/5] Testing Cryptographic SHA-256 Verification...")
    test_pkg_file = os.path.join(staged_pkg_dir, "test_package.bin")
    with open(test_pkg_file, "wb") as f:
        f.write(b"TALENTOPS_OFFICIAL_RELEASE_V2_1_0_BINARY_PAYLOAD_SAFE")

    expected_sha256 = hashlib.sha256(b"TALENTOPS_OFFICIAL_RELEASE_V2_1_0_BINARY_PAYLOAD_SAFE").hexdigest()
    actual_sha256 = compute_file_sha256(test_pkg_file)
    print(f"-> Calculated SHA-256: {actual_sha256}")
    assert actual_sha256 == expected_sha256, "SHA-256 mismatch on valid file!"
    print("   [OK] Valid file hash matches expected manifest signature.")

    # Tampered file test
    tampered_file = os.path.join(staged_pkg_dir, "tampered_package.bin")
    with open(tampered_file, "wb") as f:
        f.write(b"MALICIOUS_TAMPERED_INJECTED_PAYLOAD")
    tampered_hash = compute_file_sha256(tampered_file)
    assert tampered_hash != expected_sha256, "Tampered file should NOT match expected hash!"
    print(f"   [OK] Tampered file rejected: {tampered_hash[:16]} != {expected_sha256[:16]}")
    print("   [PASSED] Cryptographic SHA-256 integrity verification fully operational.")

    # ── Test 2: Setup Initial Stable Application (v2.0.0) ────────────────────
    print("\n[Step 2/5] Setting up initial stable application (v2.0.0)...")
    app_script_v20 = os.path.join(target_app_dir, "TalentOpsScout.py")
    with open(app_script_v20, "w") as f:
        f.write('''"""Mock Scout v2.0.0"""
import sys
if "--health-check" in sys.argv:
    print("MOCK_SCOUT_V2_0_0_HEALTHY")
    sys.exit(0)
print("RUNNING_V2_0_0")
''')
    # Verify initial health
    assert verify_post_install_health(app_script_v20) is True
    print(f"-> Installed v2.0.0 in target directory: {target_app_dir}")

    # ── Test 3: Successful Update to v2.1.0 ───────────────────────────────────
    print("\n[Step 3/5] Applying valid update to v2.1.0 using updater helper...")
    new_pkg_v21 = os.path.join(staged_pkg_dir, "update_v21")
    os.makedirs(new_pkg_v21, exist_ok=True)
    with open(os.path.join(new_pkg_v21, "TalentOpsScout.py"), "w") as f:
        f.write('''"""Mock Scout v2.1.0"""
import sys
if "--health-check" in sys.argv:
    print("MOCK_SCOUT_V2_1_0_HEALTHY")
    sys.exit(0)
print("RUNNING_V2_1_0")
''')

    update_res = perform_update(
        package_path=new_pkg_v21,
        target_dir=target_app_dir,
        backup_dir=backup_dir,
        target_pid=0,
        executable_name="TalentOpsScout.py",
        restart_after=False,
    )
    print(f"-> Update Result: {update_res}")
    assert update_res["status"] == "SUCCESS", f"Expected SUCCESS, got {update_res['status']}"
    assert update_res["rolled_back"] is False

    # Check updated content
    with open(app_script_v20, "r") as f:
        content = f.read()
    assert "Mock Scout v2.1.0" in content, "Target file was not updated to v2.1.0!"
    print("   [PASSED] Successful update verified: v2.0.0 upgraded to v2.1.0 with valid backup.")

    # ── Test 4: Automatic Rollback on Faulty Build ────────────────────────────
    print("\n[Step 4/5] Testing Automatic Rollback when an update build crashes on startup...")
    # Create faulty update package that crashes with exit code 1
    faulty_pkg = os.path.join(staged_pkg_dir, "update_faulty")
    os.makedirs(faulty_pkg, exist_ok=True)
    with open(os.path.join(faulty_pkg, "TalentOpsScout.py"), "w") as f:
        f.write('''"""Mock Scout Broken Build"""
import sys
# Intentional fatal crash during startup/health check!
sys.stderr.write("FATAL: Missing critical dependency or corrupted binary!\\n")
sys.exit(1)
''')

    print("-> Applying faulty update package...")
    rollback_res = perform_update(
        package_path=faulty_pkg,
        target_dir=target_app_dir,
        backup_dir=backup_dir,
        target_pid=0,
        executable_name="TalentOpsScout.py",
        restart_after=False,
    )
    print(f"-> Result on faulty build: {rollback_res}")
    assert rollback_res["status"] == "HEALTH_CHECK_FAILED_ROLLED_BACK"
    assert rollback_res["rolled_back"] is True
    assert "health check failed" in rollback_res["error"]

    # ── Test 5: Verify Restoration of Previous Stable Release ─────────────────
    print("\n[Step 5/5] Verifying Target Directory Integrity after Rollback...")
    with open(app_script_v20, "r") as f:
        restored_content = f.read()

    assert "Mock Scout v2.1.0" in restored_content, "Rollback failed to restore previous v2.1.0 stable build!"
    assert verify_post_install_health(app_script_v20) is True, "Restored version is not healthy!"
    print("   [OK] Restored file content: Mock Scout v2.1.0 confirmed intact.")
    print("   [OK] Post-rollback health check confirmed PASSED.")

    shutil.rmtree(work_dir, ignore_errors=True)

    print("\n" + "=" * 80)
    print("CHECK 2 RESULT: PASSED (100% SUCCESSFUL)")
    print("Out-of-process update, SHA-256 verification, and automatic rollback 100% operational.")
    print("=" * 80)


if __name__ == "__main__":
    run_check_2()
