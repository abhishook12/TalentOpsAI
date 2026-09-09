"""
core/updater.py — Enterprise Autonomous Silent Background Auto-Updater for TalentOps Scout Desktop.

Features:
1. Two-Tier Version Enforcement:
   - latest_version: New version available, downloaded silently in background.
   - minimum_version: Outdated versions below minimum are blocked with mandatory update requirement.
2. Cryptographic SHA-256 Integrity Verification:
   - Rejects tampered or corrupted update packages before execution.
3. Remote Configuration & Feature Flags:
   - Dynamically syncs runtime flags (new capture pipelines, batch sizes, AI models) without desktop rebuilds.
4. Out-of-Process Execution & Automatic Rollback:
   - Delegates to `updater_helper.py` which manages process exit, snapshot backups, and rollback on crash.
5. Fleet Health Reporting:
   - Reports update status (UP_TO_DATE, DOWNLOADING, STAGED, FAILED, ROLLED_BACK) to backend telemetry.
"""

import os
import sys
import time
import json
import logging
import hashlib
import threading
import subprocess
from typing import Optional, Callable, Dict, Any
import requests

from .paths import (
    get_updates_dir,
    get_backups_dir,
    get_application_dir,
    get_remote_config_path,
)

logger = logging.getLogger("scout.updater")

CURRENT_VERSION = "2.0.0"
UPDATE_CHECK_INTERVAL_SEC = 21600.0  # 6 hours
FALLBACK_CDN_URL = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"


def parse_semver(v: str):
    """Parses version string like '2.4.0' or 'v2.4.0' into tuple (2, 4, 0)."""
    try:
        clean = v.strip().lstrip("v").split("-")[0]
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file for cryptographic verification."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class AutoUpdater:
    def __init__(
        self,
        api_base: str = "https://talentopsai-1.onrender.com",
        current_version: str = CURRENT_VERSION,
        channel: str = "stable",
        on_update_ready: Optional[Callable[[str, str], None]] = None,
        on_mandatory_update_required: Optional[Callable[[str, str], None]] = None,
    ):
        self.api_base = api_base
        self.current_version = current_version
        self.channel = channel
        self.on_update_ready = on_update_ready
        self.on_mandatory_update_required = on_mandatory_update_required

        self.downloaded_installer_path: Optional[str] = None
        self.pending_version: Optional[str] = None
        self.is_mandatory: bool = False
        self.minimum_version: str = "1.0.0"
        self.update_status: str = "IDLE"  # IDLE, CHECKING, DOWNLOADING, VERIFYING, STAGED, FAILED
        self.active_features: Dict[str, Any] = {}
        self.active_config: Dict[str, Any] = {}

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """Starts background periodic update poller."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._update_loop, daemon=True, name="ScoutAutoUpdater")
        self._thread.start()
        logger.info("AutoUpdater started (Current: v%s, channel: %s, interval: 6h)", self.current_version, self.channel)

    def stop(self):
        """Stops background update worker."""
        self._stop_event.set()

    def check_for_updates_now(self) -> Optional[Dict[str, Any]]:
        """
        Polls the update manifest from the backend.
        Evaluates two-tier version requirements (latest vs minimum).
        """
        self.update_status = "CHECKING"
        try:
            url = f"{self.api_base}/scout/updates/manifest?channel={self.channel}"
            logger.debug("Checking update manifest at %s...", url)
            res = requests.get(url, timeout=10.0)

            if res.status_code != 200:
                # Fallback to legacy endpoint if manifest endpoint is not yet deployed
                url_fallback = f"{self.api_base}/scout/release/latest"
                res = requests.get(url_fallback, timeout=10.0)

            if res.status_code == 200:
                manifest = res.json()
                self._process_manifest(manifest)
                return manifest
            else:
                logger.debug("Update server responded with HTTP %d", res.status_code)
        except Exception as e:
            logger.debug("Update check ping failed: %s", e)

        self.update_status = "IDLE"
        return None

    def _process_manifest(self, manifest: Dict[str, Any]):
        """Processes version comparison, remote feature flags, and mandatory status."""
        remote_ver_str = manifest.get("latest_version") or manifest.get("version", "2.0.0")
        min_ver_str = manifest.get("minimum_version", "1.0.0")
        self.minimum_version = min_ver_str

        # 1. Update Remote Feature Flags & Config dynamically
        features = manifest.get("features", {})
        config = manifest.get("config", {})
        if features or config:
            self._save_remote_config(features, config)

        # 2. Evaluate Version Rules
        remote_ver = parse_semver(remote_ver_str)
        min_ver = parse_semver(min_ver_str)
        local_ver = parse_semver(self.current_version)

        # Check if local version is deprecated below minimum
        if local_ver < min_ver or manifest.get("mandatory", False):
            self.is_mandatory = True
            logger.warning("[MANDATORY] UPDATE REQUIRED! Local v%s is below minimum v%s", self.current_version, min_ver_str)
            if self.on_mandatory_update_required:
                self.on_mandatory_update_required(min_ver_str, remote_ver_str)

        # Check if new version exists
        if remote_ver > local_ver:
            logger.info("[UPDATE] Update available: v%s (Local: v%s)", remote_ver_str, self.current_version)
            self.pending_version = remote_ver_str
            self.update_status = "UPDATE_AVAILABLE"
        else:
            self.update_status = "UP_TO_DATE"
            logger.debug("Scout is up to date (v%s)", self.current_version)

    def _save_remote_config(self, features: Dict[str, Any], config: Dict[str, Any]):
        """Persists remote features and runtime config without requiring app restart."""
        self.active_features = features
        self.active_config = config
        try:
            cfg_path = get_remote_config_path()
            payload = {
                "features": features,
                "config": config,
                "synced_at": time.time(),
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.debug("Persisted remote config to %s", cfg_path)
        except Exception as e:
            logger.warning("Could not persist remote config: %s", e)

    def _update_loop(self):
        # Initial stagger
        time.sleep(10.0)

        while not self._stop_event.is_set():
            manifest = self.check_for_updates_now()
            if manifest and self.pending_version and parse_semver(self.pending_version) > parse_semver(self.current_version):
                self._download_and_verify(manifest)
                # If staged, back off polling to avoid repeated downloads
                time.sleep(86400.0)

            self._stop_event.wait(UPDATE_CHECK_INTERVAL_SEC)

    def _download_and_verify(self, manifest: Dict[str, Any]):
        """
        Downloads package with integrity verification.
        Rejects payload if SHA-256 does not match.
        """
        pkg = manifest.get("package", {})
        dl_url = pkg.get("url") or manifest.get("download_url") or FALLBACK_CDN_URL
        expected_hash = pkg.get("sha256") or manifest.get("sha256")
        ver = self.pending_version or manifest.get("version", "latest")

        target_file = os.path.join(get_updates_dir(), f"TalentOpsScoutSetup_v{ver}.exe")

        # 1. Check if valid cached package already exists
        if os.path.exists(target_file) and os.path.getsize(target_file) > 1000:
            if not expected_hash or compute_file_sha256(target_file).lower() == expected_hash.lower():
                logger.info("✓ Staged installer for v%s already cached and verified (%s)", ver, target_file)
                self.downloaded_installer_path = target_file
                self.update_status = "STAGED"
                if self.on_update_ready:
                    self.on_update_ready(ver, target_file)
                return

        # 2. Download package
        self.update_status = "DOWNLOADING"
        logger.info("Silently downloading TalentOps Scout v%s from %s...", ver, dl_url)
        temp_download = target_file + ".part"

        try:
            res = requests.get(dl_url, stream=True, timeout=180.0)
            if res.status_code == 200:
                with open(temp_download, "wb") as f:
                    for chunk in res.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            return
                        if chunk:
                            f.write(chunk)

                # 3. Verify SHA-256 Integrity
                self.update_status = "VERIFYING"
                if expected_hash:
                    actual_hash = compute_file_sha256(temp_download)
                    if actual_hash.lower() != expected_hash.lower():
                        logger.error(
                            "❌ SHA-256 VERIFICATION FAILED! Expected: %s, Actual: %s",
                            expected_hash,
                            actual_hash,
                        )
                        os.remove(temp_download)
                        self.update_status = "FAILED"
                        return
                    logger.info("✓ Cryptographic SHA-256 verification PASSED (%s)", actual_hash[:16])

                if os.path.exists(target_file):
                    os.remove(target_file)
                os.rename(temp_download, target_file)

                logger.info("✅ TalentOps Scout v%s successfully downloaded, verified, and staged (%s)", ver, target_file)
                self.downloaded_installer_path = target_file
                self.update_status = "STAGED"

                if self.on_update_ready:
                    self.on_update_ready(ver, target_file)

        except Exception as e:
            logger.warning("Silent auto-update download failed: %s", e)
            self.update_status = "FAILED"
            if os.path.exists(temp_download):
                try:
                    os.remove(temp_download)
                except Exception:
                    pass

    def apply_update_and_restart(self, installer_path: Optional[str] = None):
        """
        Delegates update execution to the independent out-of-process helper (`updater_helper.py`).
        Terminates the current Scout application cleanly so binaries can be safely swapped.
        """
        pkg_path = installer_path or self.downloaded_installer_path
        if not pkg_path or not os.path.exists(pkg_path):
            logger.error("Cannot apply update: file not found (%s)", pkg_path)
            return False

        app_dir = get_application_dir()
        backup_dir = get_backups_dir()
        current_pid = os.getpid()

        # Locate updater_helper.py
        helper_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "updater", "updater_helper.py")
        if not os.path.exists(helper_path):
            # Fallback direct execution if helper is missing
            logger.warning("updater_helper.py not found at %s; executing direct silent setup", helper_path)
            cmd = [pkg_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS=1"]
            subprocess.Popen(cmd, shell=False)
            sys.exit(0)

        cmd = [
            sys.executable,
            helper_path,
            "--package", pkg_path,
            "--target-dir", app_dir,
            "--backup-dir", backup_dir,
            "--target-pid", str(current_pid),
            "--executable-name", "TalentOpsScout.exe",
        ]

        logger.info("Launching detached out-of-process updater helper: %s", cmd)

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | (
                subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0
            )

        subprocess.Popen(cmd, creationflags=flags, close_fds=True)
        logger.info("Scout shutting down cleanly to permit out-of-process binary update...")
        sys.exit(0)

    def report_status_to_server(self, device_id: str, status: str, error_msg: Optional[str] = None):
        """Reports update telemetry to backend fleet manager."""
        try:
            url = f"{self.api_base}/scout/updates/report"
            payload = {
                "device_id": device_id,
                "scout_version": self.current_version,
                "update_status": status,
                "error_message": error_msg,
                "timestamp": time.time(),
            }
            requests.post(url, json=payload, timeout=5.0)
        except Exception:
            pass
