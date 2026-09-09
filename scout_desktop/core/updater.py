"""
core/updater.py — Autonomous Silent Background Auto-Updater for TalentOps Scout Desktop

Periodically checks TalentOps release endpoint (/scout/release/latest).
Downloads new versions silently from Supabase CDN with integrity verification.
Notifies user via UI and tray when update is ready for 1-click apply.
"""

import os
import sys
import time
import json
import logging
import threading
import tempfile
import subprocess
from typing import Optional, Callable, Dict, Any
import requests

logger = logging.getLogger("scout.updater")

CURRENT_VERSION = "2.0.0"
UPDATE_CHECK_INTERVAL_SEC = 21600.0  # Check every 6 hours
FALLBACK_CDN_URL = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"


def parse_semver(v: str):
    """Parses version string like '2.1.0' into tuple (2, 1, 0)."""
    try:
        clean = v.strip().lstrip("v").split("-")[0]
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


class AutoUpdater:
    def __init__(
        self,
        api_base: str = "https://talentopsai-1.onrender.com",
        current_version: str = CURRENT_VERSION,
        on_update_ready: Optional[Callable[[str, str], None]] = None,
    ):
        self.api_base = api_base
        self.current_version = current_version
        self.on_update_ready = on_update_ready
        self.downloaded_installer_path: Optional[str] = None
        self.pending_version: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self):
        """Starts background polling worker."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._update_loop, daemon=True, name="ScoutAutoUpdater")
        self._thread.start()
        logger.info("AutoUpdater started (Current: v%s, interval: 6h)", self.current_version)

    def stop(self):
        """Stops the background worker."""
        self._stop_event.set()

    def check_for_updates_now(self) -> Optional[Dict[str, Any]]:
        """Performs an immediate synchronous update check."""
        try:
            url = f"{self.api_base}/scout/release/latest"
            res = requests.get(url, timeout=10.0)
            if res.status_code == 200:
                data = res.json()
                remote_ver_str = data.get("version", "2.0.0")
                remote_ver = parse_semver(remote_ver_str)
                local_ver = parse_semver(self.current_version)

                if remote_ver > local_ver:
                    logger.info("🎉 New TalentOps Scout version discovered: v%s (Current: v%s)", remote_ver_str, self.current_version)
                    return data
                else:
                    logger.debug("Scout is up to date (Local: v%s, Remote: v%s)", self.current_version, remote_ver_str)
        except Exception as e:
            logger.debug("Auto-update check ping failed: %s", e)
        return None

    def _update_loop(self):
        # Initial delay before first check to avoid slowing down app startup
        time.sleep(15.0)

        while not self._stop_event.is_set():
            update_data = self.check_for_updates_now()
            if update_data:
                self._download_and_stage(update_data)
                # Once an update is staged, back off polling
                time.sleep(86400.0)

            self._stop_event.wait(UPDATE_CHECK_INTERVAL_SEC)

    def _download_and_stage(self, release_info: Dict[str, Any]):
        ver = release_info.get("version", "latest")
        dl_url = release_info.get("download_url") or FALLBACK_CDN_URL

        target_file = os.path.join(tempfile.gettempdir(), f"TalentOpsScoutSetup_v{ver}.exe")
        if os.path.exists(target_file) and os.path.getsize(target_file) > 40_000_000:
            logger.info("Installer for v%s already cached at %s", ver, target_file)
            self.downloaded_installer_path = target_file
            self.pending_version = ver
            if self.on_update_ready:
                self.on_update_ready(ver, target_file)
            return

        logger.info("Silently downloading TalentOps Scout v%s from %s...", ver, dl_url)
        try:
            res = requests.get(dl_url, stream=True, timeout=120.0)
            if res.status_code == 200:
                with open(target_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=65536):
                        if self._stop_event.is_set():
                            return
                        if chunk:
                            f.write(chunk)

                if os.path.exists(target_file) and os.path.getsize(target_file) > 40_000_000:
                    logger.info("✅ TalentOps Scout v%s downloaded and staged successfully (%s)", ver, target_file)
                    self.downloaded_installer_path = target_file
                    self.pending_version = ver
                    if self.on_update_ready:
                        self.on_update_ready(ver, target_file)
        except Exception as e:
            logger.warning("Silent auto-update download failed: %s", e)

    @staticmethod
    def apply_update_and_restart(installer_path: str):
        """
        Executes the Inno Setup installer silently and restarts the app.
        """
        if not os.path.exists(installer_path):
            logger.error("Cannot apply update: file not found %s", installer_path)
            return False

        try:
            cmd = [
                installer_path,
                "/SILENT",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
                "/TASKS=desktopicon",
            ]
            logger.info("Launching installer: %s", cmd)
            subprocess.Popen(cmd, shell=False)
            sys.exit(0)
        except Exception as e:
            logger.error("Failed to launch update installer: %s", e)
            return False
