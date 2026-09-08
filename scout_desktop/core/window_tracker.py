"""
core/window_tracker.py — Native Windows Active Window & Process Tracker

Monitors the active foreground window, window title, process ID,
executable name, and bounding rect using native Win32 APIs.
Supports interactive desktop attachment across desktop stations.
"""

import ctypes
from ctypes import wintypes
import os
import time
import logging

logger = logging.getLogger("scout.window_tracker")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Known application classifications
BROWSER_PROCESSES = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave Browser",
    "opera.exe": "Opera",
}

PRODUCTIVITY_PROCESSES = {
    "outlook.exe": "Microsoft Outlook",
    "ms-teams.exe": "Microsoft Teams",
    "teams.exe": "Microsoft Teams",
    "slack.exe": "Slack",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "Microsoft PowerPoint",
    "notepad.exe": "Notepad",
}


def ensure_interactive_desktop():
    """
    Ensures current thread is attached to the interactive 'Default' desktop
    in WinSta0. Essential for background/service threads on Windows.
    """
    try:
        DESKTOP_ALL = 0x01FF
        h_default = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL)
        if h_default:
            user32.SetThreadDesktop(h_default)
            return True
    except Exception as e:
        logger.debug("Failed to set thread desktop: %s", e)
    return False


class WindowInfo:
    def __init__(
        self,
        hwnd=0,
        title="",
        pid=0,
        process_name="unknown",
        app_type="GENERIC",
        rect=(0, 0, 0, 0),
        timestamp=None,
    ):
        self.hwnd = hwnd
        self.title = title
        self.pid = pid
        self.process_name = process_name
        self.app_type = app_type  # BROWSER | PRODUCTIVITY | GENERIC
        self.rect = rect  # (left, top, right, bottom)
        self.timestamp = timestamp or time.time()

    @property
    def width(self):
        return max(0, self.rect[2] - self.rect[0])

    @property
    def height(self):
        return max(0, self.rect[3] - self.rect[1])

    @property
    def is_browser(self):
        return self.app_type == "BROWSER"

    @property
    def is_valid(self):
        return bool(self.hwnd and self.title.strip() and self.width > 50 and self.height > 50)

    def to_dict(self):
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "pid": self.pid,
            "process_name": self.process_name,
            "app_type": self.app_type,
            "rect": {
                "left": self.rect[0],
                "top": self.rect[1],
                "right": self.rect[2],
                "bottom": self.rect[3],
                "width": self.width,
                "height": self.height,
            },
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return f"<WindowInfo [{self.process_name}] '{self.title[:40]}' (HWND:{self.hwnd})>"


class WindowTracker:
    def __init__(self):
        self._last_reported_info: Optional[WindowInfo] = None
        self._last_user_window: Optional[WindowInfo] = None
        self._desktop_attached = ensure_interactive_desktop()
        self._own_pid = os.getpid()

    def get_process_name(self, pid: int) -> str:
        """Resolves process name from PID via Win32 query."""
        if not pid:
            return "unknown"
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_process:
            return "unknown"
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            # QueryFullProcessImageNameW is standard across modern Windows
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                full_path = buf.value
                return os.path.basename(full_path).lower()
        except Exception:
            pass
        finally:
            kernel32.CloseHandle(h_process)
        return "unknown"

    def get_active_window(self) -> WindowInfo:
        """
        Queries and returns current foreground window metadata.
        Filters out Scout's own process to prevent self-focus loops.
        """
        # Ensure desktop attachment if needed
        ensure_interactive_desktop()

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return self._last_user_window or WindowInfo()

        # PID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_id = pid.value

        # If foreground is Scout's own process, preserve last known user window
        if process_id == self._own_pid:
            return self._last_user_window or WindowInfo()

        # Title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()

        # Executable name
        process_name = self.get_process_name(process_id)

        # App type classification
        if process_name in BROWSER_PROCESSES:
            app_type = "BROWSER"
        elif process_name in PRODUCTIVITY_PROCESSES:
            app_type = "PRODUCTIVITY"
        else:
            app_type = "GENERIC"

        # Bounding Rect
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        bounds = (rect.left, rect.top, rect.right, rect.bottom)

        info = WindowInfo(
            hwnd=hwnd,
            title=title,
            pid=process_id,
            process_name=process_name,
            app_type=app_type,
            rect=bounds,
            timestamp=time.time(),
        )

        if info.is_valid and process_id != self._own_pid:
            self._last_user_window = info

        return info

    def has_active_window_changed(self, current: WindowInfo) -> bool:
        """Returns True if foreground window HWND or title has changed."""
        if not current or not current.is_valid:
            return False
        if current.pid == self._own_pid:
            return False

        if self._last_reported_info is None:
            self._last_reported_info = current
            return True

        changed = (
            current.hwnd != self._last_reported_info.hwnd
            or current.title != self._last_reported_info.title
        )
        if changed:
            self._last_reported_info = current
        return changed
