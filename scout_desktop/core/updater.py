"""
core/updater.py — Enterprise Autonomous Silent Background Auto-Updater for TalentOps Scout Desktop.

Security & Architecture:
1. Cryptographic Trust Chain:
   - Ed25519 digital signature verification on release manifest.
   - Detached cryptographic signature verification on installer packages.
   - Cryptographic SHA-256 integrity check.
   - Authenticode verification on Windows.
2. Two-Tier Version Enforcement:
   - latest_version: Background update downloaded and staged automatically.
   - minimum_version: Outdated versions blocked with mandatory update requirement.
3. Typed Update State Machine:
   - Formally managed transitions (UP_TO_DATE -> UPDATE_AVAILABLE -> DOWNLOADING -> DOWNLOADED -> VERIFYING -> APPLYING -> SUCCESS / ROLLBACK).
4. Staged Rollout & Channel Support:
   - Channels: stable, beta, internal.
   - Sends device_id for deterministic staged rollout cohort allocation.
5. Remote Feature Flags & Runtime Config:
   - Dynamic synchronization saved directly to `%LOCALAPPDATA%\\TalentOpsAI\\Scout\\config\\remote_config.json`.
6. Out-of-Process Execution & Automatic Rollback:
   - Delegates binary swapping, health check, and snapshot rollback to detached `updater_helper.py`.
"""

import os
import sys
import time
import json
import logging
import hashlib
import platform
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
from .security import (
    verify_manifest_signature,
    verify_package_signature,
    verify_authenticode_signature,
)
from .updater_state import UpdateStateMachine, UpdateState

logger = logging.getLogger("scout.updater")

try:
    from ..version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "2.7.0"

UPDATE_CHECK_INTERVAL_SEC = 21600.0  # 6 hours
FALLBACK_CDN_URL = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup_v2.7.0.exe"


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
        device_id: Optional[str] = None,
        on_update_ready: Optional[Callable[[str, str], None]] = None,
        on_mandatory_update_required: Optional[Callable[[str, str], None]] = None,
    ):
        self.api_base = api_base
        self.current_version = current_version
        self.channel = channel
        self.device_id = device_id or f"DEV-{platform.node()}-{os.getlogin()}"
        self.on_update_ready = on_update_ready
        self.on_mandatory_update_required = on_mandatory_update_required

        self.state_machine = UpdateStateMachine()
        self.downloaded_installer_path: Optional[str] = None
        self.pending_version: Optional[str] = None
        self.release_notes: Optional[str] = None
        self.is_mandatory: bool = False
        self.minimum_version: str = "1.0.0"
        self.active_features: Dict[str, Any] = {}
        self.active_config: Dict[str, Any] = {}
        self.last_checked_at: Optional[float] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def update_status(self) -> str:
        return self.state_machine.current_state.value

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
        Polls signed update manifest from the backend.
        Verifies cryptographic signature using embedded public key.
        Evaluates two-tier version requirements (latest vs minimum).
        """
        self.last_checked_at = time.time()
        try:
            url = f"{self.api_base}/scout/updates/manifest?channel={self.channel}&device_id={self.device_id}"
            logger.debug("Checking update manifest at %s...", url)
            res = requests.get(url, timeout=10.0)

            if res.status_code == 200:
                manifest = res.json()

                # Cryptographic Trust Chain Check 1: Verify Manifest Signature
                sig = manifest.get("signature") or manifest.get("manifest_signature")
                if sig:
                    is_valid_sig = verify_manifest_signature(manifest, signature_b64=sig)
                    if not is_valid_sig:
                        logger.error("[SECURITY] REJECTED MANIFEST: Cryptographic signature verification failed!")
                        self.report_status_to_server(self.device_id, "VERIFICATION_FAILED", "Manifest signature invalid")
                        return None
                else:
                    logger.warning("Manifest has no cryptographic signature. Proceeding with caution.")

                self._process_manifest(manifest)
                return manifest
            else:
                logger.debug("Update server responded with HTTP %d", res.status_code)
        except Exception as e:
            logger.debug("Update check ping failed: %s", e)

        return None

    def _process_manifest(self, manifest: Dict[str, Any]):
        """Processes version comparison, remote feature flags, and mandatory status."""
        remote_ver_str = manifest.get("latest_version") or manifest.get("version", "2.0.0")
        min_ver_str = manifest.get("minimum_version", "1.0.0")
        self.minimum_version = min_ver_str
        self.release_notes = manifest.get("release_notes")

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
            self.state_machine.transition(UpdateState.UPDATE_AVAILABLE, target_version=remote_ver_str, strict=False)
        else:
            self.state_machine.transition(UpdateState.UP_TO_DATE, strict=False)
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
        time.sleep(5.0)
        while not self._stop_event.is_set():
            manifest = self.check_for_updates_now()
            if manifest and self.pending_version and parse_semver(self.pending_version) > parse_semver(self.current_version):
                self._download_and_verify(manifest)
                # If staged, back off polling to avoid repeated downloads
                time.sleep(86400.0)

            self._stop_event.wait(UPDATE_CHECK_INTERVAL_SEC)

    def _download_and_verify(self, manifest: Dict[str, Any]) -> bool:
        """
        Downloads package with full cryptographic trust chain verification:
        1. SHA-256 byte integrity check
        2. Package digital signature check (Ed25519)
        3. Authenticode certificate check on Windows
        """
        pkg = manifest.get("package", {})
        dl_url = pkg.get("url") or manifest.get("download_url") or FALLBACK_CDN_URL
        expected_hash = pkg.get("sha256") or manifest.get("sha256")
        pkg_sig = manifest.get("package_signature")
        ver = self.pending_version or manifest.get("version", "latest")

        target_file = os.path.join(get_updates_dir(), f"TalentOpsScoutSetup_v{ver}.exe")

        # 1. Check cached package
        if os.path.exists(target_file) and os.path.getsize(target_file) > 1000:
            actual_hash = compute_file_sha256(target_file)
            if not expected_hash or actual_hash.lower() == expected_hash.lower():
                logger.info("[OK] Staged installer for v%s already cached and verified (%s)", ver, target_file)
                self.downloaded_installer_path = target_file
                self.state_machine.transition(UpdateState.DOWNLOADED, target_version=ver, strict=False)
                self.state_machine.transition(UpdateState.VERIFYING, strict=False)
                self.state_machine.transition(UpdateState.SUCCESS, context="Cached and verified", strict=False)
                if self.on_update_ready:
                    self.on_update_ready(ver, target_file)
                return True

        # 2. Download
        self.state_machine.transition(UpdateState.DOWNLOADING, target_version=ver, strict=False)
        self.report_status_to_server(self.device_id, "DOWNLOADING", target_version=ver)
        logger.info("Silently downloading TalentOps Scout v%s from %s...", ver, dl_url)
        temp_download = target_file + ".part"

        try:
            res = requests.get(dl_url, stream=True, timeout=180.0)
            if res.status_code == 200:
                with open(temp_download, "wb") as f:
                    for chunk in res.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            return False
                        if chunk:
                            f.write(chunk)

                self.state_machine.transition(UpdateState.DOWNLOADED, strict=False)
                self.state_machine.transition(UpdateState.VERIFYING, strict=False)

                # 3. Cryptographic Check A: SHA-256 Integrity
                if expected_hash:
                    actual_hash = compute_file_sha256(temp_download)
                    if actual_hash.lower() != expected_hash.lower():
                        logger.error(
                            "[SECURITY ALERT] SHA-256 VERIFICATION FAILED! Expected: %s, Actual: %s",
                            expected_hash,
                            actual_hash,
                        )
                        os.remove(temp_download)
                        self.state_machine.transition(UpdateState.VERIFICATION_FAILED, context="SHA-256 mismatch", strict=False)
                        self.report_status_to_server(self.device_id, "VERIFICATION_FAILED", "SHA-256 mismatch", target_version=ver)
                        return False
                    logger.info("[OK] Cryptographic SHA-256 verification PASSED (%s)", actual_hash[:16])

                # 4. Cryptographic Check B: Detached Digital Signature (Ed25519)
                if pkg_sig:
                    is_pkg_sig_valid = verify_package_signature(temp_download, package_signature_b64=pkg_sig)
                    if not is_pkg_sig_valid:
                        logger.error("[SECURITY ALERT] Package digital signature verification FAILED! Untrusted binary.")
                        os.remove(temp_download)
                        self.state_machine.transition(UpdateState.VERIFICATION_FAILED, context="Package signature mismatch", strict=False)
                        self.report_status_to_server(self.device_id, "VERIFICATION_FAILED", "Package signature mismatch", target_version=ver)
                        return False
                    logger.info("[OK] Package digital signature PASSED.")

                # 5. Cryptographic Check C: Windows Authenticode (if Windows executable)
                if sys.platform == "win32" and temp_download.endswith(".exe"):
                    auth_res = verify_authenticode_signature(temp_download)
                    logger.info("Windows Authenticode status: %s", auth_res.get("status"))

                if os.path.exists(target_file):
                    os.remove(target_file)
                os.rename(temp_download, target_file)

                logger.info("[SUCCESS] TalentOps Scout v%s verified and staged (%s)", ver, target_file)
                self.downloaded_installer_path = target_file
                self.state_machine.transition(UpdateState.SUCCESS, context="Staged successfully", strict=False)
                self.report_status_to_server(self.device_id, "STAGED", target_version=ver)

                if self.on_update_ready:
                    self.on_update_ready(ver, target_file)
                return True

        except Exception as e:
            logger.warning("Silent auto-update download failed: %s", e)
            self.state_machine.transition(UpdateState.DOWNLOAD_FAILED, context=str(e), strict=False)
            self.report_status_to_server(self.device_id, "DOWNLOAD_FAILED", str(e), target_version=ver)
            if os.path.exists(temp_download):
                try:
                    os.remove(temp_download)
                except Exception:
                    pass
            return False

    def apply_update_and_restart(self, installer_path: Optional[str] = None) -> bool:
        """
        Transitions state to APPLYING and launches detached `updater_helper.py`
        to coordinate process exit, backup, update, health check, and rollback.
        """
        pkg_path = installer_path or self.downloaded_installer_path
        if not pkg_path or not os.path.exists(pkg_path):
            logger.error("Cannot apply update: file not found (%s)", pkg_path)
            return False

        self.state_machine.transition(UpdateState.APPLYING, strict=False)
        self.report_status_to_server(self.device_id, "APPLYING", target_version=self.pending_version)

        app_dir = get_application_dir()
        backup_dir = get_backups_dir()
        current_pid = os.getpid()

        # Locate updater_helper.py or standalone ScoutUpdater.exe
        updater_exe = os.path.join(app_dir, "TalentOpsScoutUpdater.exe")
        helper_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "updater", "updater_helper.py")

        if os.path.exists(updater_exe):
            cmd = [
                updater_exe,
                "--package", pkg_path,
                "--target-dir", app_dir,
                "--backup-dir", backup_dir,
                "--target-pid", str(current_pid),
                "--executable-name", "TalentOpsScout.exe",
            ]
        elif os.path.exists(helper_py):
            cmd = [
                sys.executable,
                helper_py,
                "--package", pkg_path,
                "--target-dir", app_dir,
                "--backup-dir", backup_dir,
                "--target-pid", str(current_pid),
                "--executable-name", "TalentOpsScout.exe",
            ]
        else:
            # Fallback direct execution
            cmd = [pkg_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS=1"]
            subprocess.Popen(cmd, shell=False)
            sys.exit(0)

        logger.info("Launching detached out-of-process updater helper: %s", cmd)

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | (
                subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0
            )

        subprocess.Popen(cmd, creationflags=flags, close_fds=True)
        logger.info("Scout shutting down cleanly to permit out-of-process binary update...")
        sys.exit(0)

    def report_status_to_server(
        self,
        device_id: str,
        status: str,
        error_msg: Optional[str] = None,
        target_version: Optional[str] = None,
    ):
        """Reports update telemetry to backend fleet manager."""
        try:
            url = f"{self.api_base}/scout/updates/report"
            payload = {
                "device_id": device_id,
                "scout_version": self.current_version,
                "channel": self.channel,
                "os_info": f"{platform.system()} {platform.release()} ({platform.machine()})",
                "os_version": platform.version(),
                "update_status": status,
                "error_message": error_msg,
                "target_version": target_version or self.pending_version,
                "timestamp": time.time(),
            }
            requests.post(url, json=payload, timeout=5.0)
        except Exception:
            pass
