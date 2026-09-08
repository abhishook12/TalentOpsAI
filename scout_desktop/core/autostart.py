"""
core/autostart.py — Windows Startup Registry Manager

Manages the [✓] Start Scout with Windows registry configuration under:
HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
"""

import os
import sys
import winreg
import logging

logger = logging.getLogger("scout.autostart")

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "TalentOpsScout"


def get_default_command() -> str:
    """Returns the command path to launch Scout silently at Windows startup."""
    pythonw = r"c:\TalentOpsAI\teams_extractor\venv\Scripts\pythonw.exe"
    if os.path.exists(pythonw):
        return f'"{pythonw}" -m scout_desktop.app'
    bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run_desktop_scout.bat"))
    return f'"{bat_path}"'


def is_autostart_enabled() -> bool:
    """Checks whether TalentOps Scout is set to start with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning("Failed to check autostart registry key: %s", e)
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables automatic startup with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_default_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                logger.info("Auto-start with Windows ENABLED: %s", cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    logger.info("Auto-start with Windows DISABLED")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error("Failed to update autostart registry key: %s", e)
        return False
