import os
import sys
import json
import logging
import ctypes
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
import psutil
import requests

from ..services.auth_service import get_current_user_from_request
from ..models.auth_models import User

logger = logging.getLogger("system_windows")
router = APIRouter(prefix="/system-windows", tags=["System Windows"])

def _attach_interactive_desktop():
    """Attaches background worker thread to interactive user desktop session."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception as e:
            logger.debug(f"Desktop attachment notice: {e}")

def _get_teams_hwnds():
    _attach_interactive_desktop()
    found = []
    if sys.platform == "win32":
        import win32gui
        def enum_cb(h, _):
            if win32gui.IsWindow(h):
                t = win32gui.GetWindowText(h)
                if "microsoft teams" in t.lower() or "ctv-" in t.lower():
                    found.append((h, t))
            return 1
        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.warning(f"EnumWindows notice: {e}")
    return found

def _get_scout_hwnd():
    _attach_interactive_desktop()
    if sys.platform == "win32":
        import win32gui
        for title in ["TalentOps Scout v2.14.1", "TalentOps Scout", "Scout Desktop"]:
            h = win32gui.FindWindow(None, title)
            if h and win32gui.IsWindow(h):
                return h
    return None

@router.get("/status")
def get_windows_status(current_user: User = Depends(get_current_user_from_request)):
    """Returns the screen status of all background engine windows."""
    teams_hwnds = _get_teams_hwnds()
    teams_visible = False
    teams_rect = None

    if teams_hwnds:
        import win32gui
        h, t = teams_hwnds[0]
        try:
            rect = win32gui.GetWindowRect(h)
            teams_rect = rect
            # Offscreen is <= -5000
            teams_visible = rect[0] > -5000 and rect[0] != -32000
        except Exception:
            pass

    # Scout Desktop Loopback Check
    scout_online = False
    scout_device_id = None
    try:
        res = requests.get("http://127.0.0.1:49152/handshake", timeout=1.0)
        if res.status_code == 200:
            scout_online = True
            scout_device_id = res.json().get("device_id")
    except Exception:
        pass

    # Teams Supervisor Stats
    supervisor_data = {}
    workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    status_file = os.path.join(workspace_dir, "teams_extractor", "supervisor_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                supervisor_data = json.load(f)
        except Exception:
            pass

    return {
        "teams": {
            "found_windows": len(teams_hwnds),
            "is_visible_on_screen": teams_visible,
            "rect": teams_rect,
            "supervisor": supervisor_data,
        },
        "scout": {
            "is_running": scout_online,
            "device_id": scout_device_id,
        }
    }

@router.post("/teams/show")
def show_teams_window(current_user: User = Depends(get_current_user_from_request)):
    """Brings Microsoft Teams window visibly onto screen at (50, 50, 1280, 720)."""
    hwnds = _get_teams_hwnds()
    if not hwnds:
        raise HTTPException(status_code=404, detail="No Microsoft Teams window found.")

    import win32gui
    import win32con

    for h, t in hwnds:
        try:
            win32gui.ShowWindow(h, win32con.SW_RESTORE)
            win32gui.SetWindowPos(
                h,
                win32con.HWND_NOTOPMOST,
                50, 50, 1280, 720,
                win32con.SWP_SHOWWINDOW
            )
            logger.info(f"Restored Teams window HWND {h} onto screen at (50, 50).")
        except Exception as e:
            logger.error(f"Error restoring Teams window {h}: {e}")

    return {"status": "ok", "message": "Teams window opened on screen", "count": len(hwnds)}

@router.post("/teams/hide")
def hide_teams_window(current_user: User = Depends(get_current_user_from_request)):
    """Tucks Microsoft Teams window safely offscreen to (-9000, -9000) for zero screen intrusion."""
    hwnds = _get_teams_hwnds()
    if not hwnds:
        return {"status": "ok", "message": "No active Teams windows to hide"}

    import win32gui
    import win32con

    for h, t in hwnds:
        try:
            win32gui.SetWindowPos(
                h,
                win32con.HWND_BOTTOM,
                -9000, -9000,
                1048, 688,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            logger.info(f"Tucked Teams window HWND {h} offscreen to background (-9000, -9000).")
        except Exception as e:
            logger.error(f"Error hiding Teams window {h}: {e}")

    return {"status": "ok", "message": "Teams window hidden to background", "count": len(hwnds)}

@router.post("/scout/show")
def show_scout_window(current_user: User = Depends(get_current_user_from_request)):
    """Brings Desktop Scout companion window up on screen."""
    # Try loopback first
    try:
        res = requests.post("http://127.0.0.1:49152/open-window", timeout=2.0)
        if res.status_code == 200:
            return {"status": "ok", "message": "Desktop Scout window opened via loopback"}
    except Exception:
        pass

    # Fallback to win32
    h = _get_scout_hwnd()
    if h:
        import win32gui
        import win32con
        try:
            win32gui.ShowWindow(h, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(h)
        except Exception as e:
            logger.debug(f"SetForegroundWindow non-fatal note: {e}")
        return {"status": "ok", "message": "Desktop Scout window brought to front"}

    raise HTTPException(status_code=404, detail="Desktop Scout companion is not currently running.")

@router.post("/scout/hide")
def hide_scout_window(current_user: User = Depends(get_current_user_from_request)):
    """Hides Desktop Scout window to tray."""
    try:
        res = requests.post("http://127.0.0.1:49152/hide-window", timeout=2.0)
        if res.status_code == 200:
            return {"status": "ok", "message": "Desktop Scout window hidden to tray"}
    except Exception:
        pass

    h = _get_scout_hwnd()
    if h:
        import win32gui
        import win32con
        win32gui.ShowWindow(h, win32con.SW_HIDE)
        return {"status": "ok", "message": "Desktop Scout window hidden via Win32"}

    return {"status": "ok", "message": "Scout window is already hidden"}
