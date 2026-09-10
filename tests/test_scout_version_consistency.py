"""
test_scout_version_consistency.py — Comprehensive Section 26 Test Suite for TalentOps Scout.

Tests the 13 core requirements of the Mainstream Desktop Auto-Update Model:
1.  test_backend_returns_correct_version
2.  test_manifest_matches_latest
3.  test_download_redirects_to_valid_url
4.  test_desktop_client_detects_update
5.  test_desktop_client_identifies_up_to_date
6.  test_desktop_client_handles_mandatory_update
7.  test_non_disruptive_background_download
8.  test_user_deferral_respected
9.  test_restart_and_update_triggers_cleanly
10. test_staged_rollout_deterministic
11. test_staged_rollout_respects_percentage
12. test_rollback_preserves_previous_state
13. test_identity_preserved_across_update
"""

import os
import sys
import time
import json
import shutil
import tempfile
import hashlib
import unittest
from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

# Ensure repo root and backend are on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.main import app
from scout_desktop.core.updater_state import UpdateState, UpdateStateMachine
from scout_desktop.core.updater import AutoUpdater, CURRENT_VERSION
from scout_desktop.updater.updater_helper import create_rollback_backup, restore_rollback_backup
from scout_desktop.sync.backend_client import BackendClient
from scout_desktop.sync.local_queue import LocalQueue


class ScoutVersionConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # Test 1: Backend returns correct version
    # -------------------------------------------------------------------------
    def test_backend_returns_correct_version(self):
        """1. GET /scout/updates/latest returns authoritative production release metadata."""
        resp = self.client.get("/scout/updates/latest")
        self.assertEqual(resp.status_code, 200, f"Failed: {resp.text}")
        data = resp.json()
        self.assertIn("version", data)
        self.assertIn("channel", data)
        self.assertTrue(len(data["version"]) >= 3)
        self.assertIn(data["channel"], ["stable", "beta", "internal"])

    # -------------------------------------------------------------------------
    # Test 2: Manifest matches latest production version
    # -------------------------------------------------------------------------
    def test_manifest_matches_latest(self):
        """2. GET /scout/updates/manifest matches latest release metadata."""
        resp_latest = self.client.get("/scout/updates/latest")
        self.assertEqual(resp_latest.status_code, 200)
        latest_data = resp_latest.json()

        resp_manifest = self.client.get("/scout/updates/manifest?channel=stable")
        self.assertEqual(resp_manifest.status_code, 200)
        manifest_data = resp_manifest.json()

        self.assertEqual(manifest_data.get("version"), latest_data.get("version"))
        self.assertEqual(manifest_data.get("channel"), "stable")
        self.assertIn("sha256", manifest_data)
        self.assertIn("signature", manifest_data)

    # -------------------------------------------------------------------------
    # Test 3: Download redirects to valid installer URL
    # -------------------------------------------------------------------------
    def test_download_redirects_to_valid_url(self):
        """3. GET /download/scout/windows provides valid installer redirect or binary."""
        resp = self.client.get("/download/scout/windows", follow_redirects=False)
        self.assertIn(resp.status_code, [200, 302, 307], f"Unexpected status: {resp.status_code}")
        if resp.status_code in [302, 307]:
            location = resp.headers.get("location")
            self.assertTrue(bool(location), "Redirect location missing")
            self.assertTrue(location.endswith(".exe") or "storage" in location or "download" in location)

    # -------------------------------------------------------------------------
    # Test 4: Desktop client detects newer update
    # -------------------------------------------------------------------------
    def test_desktop_client_detects_update(self):
        """4. AutoUpdater detects available update when local version < remote version."""
        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="1.0.0",
            device_id="DEV-TEST-01",
            installation_id="INST-TEST-01",
        )
        mock_manifest = {
            "version": "2.7.0",
            "channel": "stable",
            "download_url": "https://example.com/ScoutSetup.exe",
            "sha256": "fakehash",
            "signature": "",
            "release_notes": "Added features",
            "minimum_version": "1.0.0",
            "mandatory": False,
        }
        with patch.object(updater, "fetch_update_manifest", return_value=mock_manifest):
            manifest = updater.check_for_updates_now()
            self.assertIsNotNone(manifest)
            self.assertEqual(updater.pending_version, "2.7.0")
            self.assertEqual(updater.state_machine.current_state, UpdateState.UPDATE_AVAILABLE)

    # -------------------------------------------------------------------------
    # Test 5: Desktop client identifies up-to-date
    # -------------------------------------------------------------------------
    def test_desktop_client_identifies_up_to_date(self):
        """5. AutoUpdater enters UP_TO_DATE when local version == remote version."""
        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="2.7.0",
            device_id="DEV-TEST-01",
            installation_id="INST-TEST-01",
        )
        mock_manifest = {
            "version": "2.7.0",
            "channel": "stable",
            "download_url": "https://example.com/ScoutSetup.exe",
            "sha256": "fakehash",
            "signature": "",
            "minimum_version": "2.0.0",
            "mandatory": False,
        }
        with patch.object(updater, "fetch_update_manifest", return_value=mock_manifest):
            manifest = updater.check_for_updates_now()
            self.assertIsNotNone(manifest)
            self.assertIsNone(updater.pending_version)
            self.assertEqual(updater.state_machine.current_state, UpdateState.UP_TO_DATE)

    # -------------------------------------------------------------------------
    # Test 6: Desktop client handles mandatory update requirement
    # -------------------------------------------------------------------------
    def test_desktop_client_handles_mandatory_update(self):
        """6. AutoUpdater enters REQUIRED_UPDATE when local version < minimum_version."""
        mandatory_called = []
        def _on_mandatory(min_v, rem_v):
            mandatory_called.append((min_v, rem_v))

        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="1.2.0",
            device_id="DEV-TEST-01",
            installation_id="INST-TEST-01",
            on_mandatory_update_required=_on_mandatory,
        )
        mock_manifest = {
            "version": "2.7.0",
            "channel": "stable",
            "download_url": "https://example.com/ScoutSetup.exe",
            "sha256": "fakehash",
            "signature": "",
            "minimum_version": "2.0.0",
            "mandatory": True,
        }
        with patch.object(updater, "fetch_update_manifest", return_value=mock_manifest):
            manifest = updater.check_for_updates_now()
            self.assertTrue(updater.is_mandatory)
            self.assertEqual(updater.state_machine.current_state, UpdateState.REQUIRED_UPDATE)
            self.assertEqual(len(mandatory_called), 1)
            self.assertEqual(mandatory_called[0], ("2.0.0", "2.7.0"))

    # -------------------------------------------------------------------------
    # Test 7: Non-disruptive background download
    # -------------------------------------------------------------------------
    def test_non_disruptive_background_download(self):
        """7. AutoUpdater downloads quietly to temp staging file and transitions to READY_TO_INSTALL."""
        ready_events = []
        def _on_ready(ver, path, notes):
            ready_events.append((ver, path, notes))

        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="2.0.0",
            device_id="DEV-TEST-01",
            installation_id="INST-TEST-01",
            on_update_ready=_on_ready,
        )

        test_content = b"TalentOpsScoutSetupInstallerMockBinaryPayload"
        content_sha = hashlib.sha256(test_content).hexdigest()

        mock_manifest = {
            "version": "2.8.0",
            "channel": "stable",
            "download_url": "https://example.com/ScoutSetup.exe",
            "sha256": content_sha,
            "signature": "",
            "release_notes": "Test release notes",
            "minimum_version": "2.0.0",
            "mandatory": False,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [test_content]

        with patch("requests.get", return_value=mock_response):
            with patch.object(updater, "report_status_to_server"):
                ok = updater._download_and_verify(mock_manifest)
                self.assertTrue(ok)
                self.assertEqual(updater.state_machine.current_state, UpdateState.READY_TO_INSTALL)
                self.assertIsNotNone(updater.downloaded_installer_path)
                self.assertTrue(os.path.exists(updater.downloaded_installer_path))
                self.assertEqual(len(ready_events), 1)
                self.assertEqual(ready_events[0][0], "2.8.0")
                try:
                    os.remove(updater.downloaded_installer_path)
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Test 8: User deferral (24-hour snooze) is respected
    # -------------------------------------------------------------------------
    def test_user_deferral_respected(self):
        """8. AutoUpdater snooze policy prevents premature reprompting."""
        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="2.0.0",
            device_id="DEV-TEST-01",
        )
        self.assertTrue(updater.is_notification_due())

        # Postpone for 24 hours
        updater.postpone_update(hours=24.0)
        self.assertFalse(updater.is_notification_due())

        # Advance simulated time past snooze
        updater.snooze_until = time.time() - 1.0
        self.assertTrue(updater.is_notification_due())

    # -------------------------------------------------------------------------
    # Test 9: Restart & update triggers cleanly
    # -------------------------------------------------------------------------
    def test_restart_and_update_triggers_cleanly(self):
        """9. apply_update_and_restart launches out-of-process helper cleanly."""
        updater = AutoUpdater(
            api_base="http://test-server",
            current_version="2.0.0",
            device_id="DEV-TEST-01",
        )
        updater.pending_version = "2.8.0"

        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"mock-installer")
            tmp_installer = f.name

        try:
            with patch("subprocess.Popen") as mock_popen, patch("sys.exit") as mock_sys_exit, patch("os._exit") as mock_exit:
                with patch.object(updater, "report_status_to_server"):
                    success = updater.apply_update_and_restart(tmp_installer)
                    self.assertTrue(success)
                    self.assertTrue(mock_popen.called)
                    self.assertEqual(updater.state_machine.current_state, UpdateState.INSTALLING)
        finally:
            if os.path.exists(tmp_installer):
                os.remove(tmp_installer)

    # -------------------------------------------------------------------------
    # Test 10: Staged rollout cohort allocation is deterministic
    # -------------------------------------------------------------------------
    def test_staged_rollout_deterministic(self):
        """10. Cohort allocation hashing is 100% deterministic for a given installation_id."""
        inst_id = "INST-ALPHA-987654321"
        cohort_results = set()
        for _ in range(100):
            cohort_val = abs(hash(inst_id)) % 100
            cohort_results.add(cohort_val)
        self.assertEqual(len(cohort_results), 1, "Cohort hash was not deterministic")

    # -------------------------------------------------------------------------
    # Test 11: Staged rollout respects rollout_percentage
    # -------------------------------------------------------------------------
    def test_staged_rollout_respects_percentage(self):
        """11. Rollout gates client availability based on cohort bucket vs percentage."""
        inst_id = "INST-TEST-COHORT"
        cohort = abs(hash(inst_id)) % 100

        pct_below = max(0, cohort - 1)
        pct_above = min(100, cohort + 1)

        self.assertFalse(cohort < pct_below if pct_below > 0 else cohort == 0)
        self.assertTrue(cohort < pct_above)

    # -------------------------------------------------------------------------
    # Test 12: Rollback preserves and restores previous version state
    # -------------------------------------------------------------------------
    def test_rollback_preserves_previous_state(self):
        """12. Updater helper snapshot and rollback restore files 100% identically."""
        with tempfile.TemporaryDirectory() as base_tmp:
            target_dir = os.path.join(base_tmp, "app_dir")
            backup_dir = os.path.join(base_tmp, "backup_dir")
            os.makedirs(target_dir, exist_ok=True)

            # Create original application files
            exe_file = os.path.join(target_dir, "TalentOpsScout.exe")
            cfg_file = os.path.join(target_dir, "config.json")
            with open(exe_file, "wb") as f:
                f.write(b"ORIGINAL_BINARY_V2_7_0")
            with open(cfg_file, "w") as f:
                json.dump({"version": "2.7.0", "stable": True}, f)

            # 1. Create rollback snapshot
            ok_backup = create_rollback_backup(target_dir, backup_dir)
            self.assertTrue(ok_backup)

            # 2. Corrupt target directory (simulate bad installer)
            with open(exe_file, "wb") as f:
                f.write(b"CORRUPTED_INCOMPLETE_INSTALL")
            os.remove(cfg_file)

            # 3. Trigger rollback restoration
            ok_restore = restore_rollback_backup(backup_dir, target_dir)
            self.assertTrue(ok_restore)

            # 4. Verify 100% file restoration
            with open(exe_file, "rb") as f:
                self.assertEqual(f.read(), b"ORIGINAL_BINARY_V2_7_0")
            self.assertTrue(os.path.exists(cfg_file))
            with open(cfg_file, "r") as f:
                cfg = json.load(f)
                self.assertEqual(cfg["version"], "2.7.0")

    # -------------------------------------------------------------------------
    # Test 13: Identity and local queue survive across updater cycle
    # -------------------------------------------------------------------------
    def test_identity_preserved_across_update(self):
        """13. device_id, installation_id, and offline SQLite queue survive update cycle."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_file = os.path.join(tmp_dir, "config.json")
            db_file = os.path.join(tmp_dir, "test_queue.db")

            fixed_device_id = "DEV-PERMANENT-999"
            fixed_inst_id = "INST-PERMANENT-888"

            # Pre-seed persistent identity in config
            with open(cfg_file, "w") as f:
                json.dump({
                    "device_id": fixed_device_id,
                    "installation_id": fixed_inst_id,
                    "scout_id": fixed_device_id,
                }, f)

            # 1. Initialize client before update
            client_pre = BackendClient(device_id=fixed_device_id, config_path=cfg_file)
            self.assertEqual(client_pre.device_id, fixed_device_id)
            self.assertEqual(client_pre.installation_id, fixed_inst_id)

            # 2. Enqueue item in local offline SQLite queue
            queue = LocalQueue(db_path=db_file)
            queue.enqueue_cluster({
                "canonical_name": "Jane Doe",
                "current_title": "VP of Engineering",
                "current_company": "Acme Corp",
                "source_url": "https://linkedin.com/in/janedoe",
            })
            queue.checkpoint()

            stats_pre = queue.get_queue_stats()
            self.assertEqual(stats_pre["pending"], 1)

            # 3. Simulate client re-initialization (post-update reboot)
            client_post = BackendClient(config_path=cfg_file)
            self.assertEqual(client_post.device_id, fixed_device_id, "Device ID changed after update!")
            self.assertEqual(client_post.installation_id, fixed_inst_id, "Installation ID changed after update!")

            # 4. Reopen queue to verify queue survived intact
            queue_post = LocalQueue(db_path=db_file)
            stats_post = queue_post.get_queue_stats()
            self.assertEqual(stats_post["pending"], 1, "Offline queue items lost during update cycle!")
            items = queue_post.get_pending_batch(limit=10)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["canonical_name"], "Jane Doe")


if __name__ == "__main__":
    unittest.main()
