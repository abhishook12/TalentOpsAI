"""
paths.py — Centralized Path & AppData Isolation Manager for TalentOps Scout Desktop.

Enforces strict separation between:
1. Application Binaries: Read-only install directory (e.g. C:\\Program Files\\TalentOpsAI\\Scout\\ or repository root).
2. User Persistent Data: %LOCALAPPDATA%\\TalentOpsAI\\Scout\\ (or ~/.talentops/scout on non-Windows).

Updates never touch or delete user persistent data:
- Local queue database (local_queue.db / scout_local.db)
- Screen captures buffer (captures/)
- User settings & pairing credentials (config.json)
- Remote feature flags & config (remote_config.json)
- Application logs (logs/)
- Update staging & backups (updates/, backups/)
"""

import os
import sys
import shutil
import logging

logger = logging.getLogger("scout.paths")

_APP_NAME = "TalentOpsAI"
_SUB_NAME = "Scout"


def get_app_data_dir() -> str:
    """
    Returns the root directory for persistent user data.
    On Windows: %LOCALAPPDATA%\\TalentOpsAI\\Scout\\
    On Unix/Mac: ~/.talentops/scout/
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        data_dir = os.path.join(base, _APP_NAME, _SUB_NAME)
    else:
        data_dir = os.path.expanduser(f"~/.{_APP_NAME.lower()}/{_SUB_NAME.lower()}")
    
    os.makedirs(data_dir, exist_ok=True)
    return os.path.abspath(data_dir)


def get_database_path() -> str:
    """Returns absolute path to the local SQLite database in AppData."""
    data_folder = os.path.join(get_app_data_dir(), "data")
    os.makedirs(data_folder, exist_ok=True)
    return os.path.join(data_folder, "scout_local.db")


def get_captures_dir() -> str:
    """Returns absolute path to the screen captures buffer directory in AppData."""
    captures_folder = os.path.join(get_app_data_dir(), "captures")
    os.makedirs(captures_folder, exist_ok=True)
    return captures_folder


def get_config_path() -> str:
    """Returns absolute path to user configuration file in AppData."""
    config_folder = os.path.join(get_app_data_dir(), "config")
    os.makedirs(config_folder, exist_ok=True)
    return os.path.join(config_folder, "config.json")


def get_remote_config_path() -> str:
    """Returns absolute path to remote feature flags & runtime config in AppData."""
    config_folder = os.path.join(get_app_data_dir(), "config")
    os.makedirs(config_folder, exist_ok=True)
    return os.path.join(config_folder, "remote_config.json")


def get_updates_dir() -> str:
    """Returns absolute path to the staged updates directory in AppData."""
    updates_folder = os.path.join(get_app_data_dir(), "updates")
    os.makedirs(updates_folder, exist_ok=True)
    return updates_folder


def get_backups_dir() -> str:
    """Returns absolute path to the rollback backups directory in AppData."""
    backups_folder = os.path.join(get_app_data_dir(), "backups")
    os.makedirs(backups_folder, exist_ok=True)
    return backups_folder


def get_logs_dir() -> str:
    """Returns absolute path to application logs directory in AppData."""
    logs_folder = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(logs_folder, exist_ok=True)
    return logs_folder


def get_state_dir() -> str:
    """Returns absolute path to runtime state and telemetry directory in AppData."""
    state_folder = os.path.join(get_app_data_dir(), "state")
    os.makedirs(state_folder, exist_ok=True)
    return state_folder


def get_application_dir() -> str:
    """Returns the directory containing application binaries."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # If running from source
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def migrate_legacy_data_if_needed():
    """
    Detects if data exists in the legacy workspace folder and transparently
    migrates it to AppData so no user data is lost.
    """
    app_dir = get_application_dir()
    
    # 1. Migrate config.json
    legacy_config = os.path.join(app_dir, "config.json")
    target_config = get_config_path()
    if os.path.exists(legacy_config) and not os.path.exists(target_config):
        try:
            shutil.copy2(legacy_config, target_config)
            logger.info("Migrated legacy config.json -> %s", target_config)
        except Exception as e:
            logger.warning("Could not migrate legacy config: %s", e)

    # 2. Migrate local_queue.db
    legacy_db = os.path.join(app_dir, "local_queue.db")
    target_db = get_database_path()
    if os.path.exists(legacy_db) and not os.path.exists(target_db):
        try:
            shutil.copy2(legacy_db, target_db)
            logger.info("Migrated legacy local_queue.db -> %s", target_db)
        except Exception as e:
            logger.warning("Could not migrate legacy db: %s", e)

    # 3. Migrate captures folder
    legacy_captures = os.path.join(app_dir, "captures")
    target_captures = get_captures_dir()
    if os.path.exists(legacy_captures) and os.path.isdir(legacy_captures):
        try:
            for item in os.listdir(legacy_captures):
                s = os.path.join(legacy_captures, item)
                d = os.path.join(target_captures, item)
                if not os.path.exists(d):
                    shutil.copy2(s, d)
            logger.info("Migrated legacy captures -> %s", target_captures)
        except Exception as e:
            logger.warning("Could not migrate legacy captures: %s", e)
