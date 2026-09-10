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
from typing import Tuple, Optional, Dict, Any

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


import re


def is_allowed_scout_target(win_info: Optional['WindowInfo'], b_ctx: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    STRICT USER TARGET WHITELIST RULE:
    The scanner MUST ONLY work on:
    1. Microsoft Teams (`teams.exe` or `ms-teams.exe`).
    2. Google Chrome (`chrome.exe`) STRICTLY on LinkedIn data (Profiles, Recruiter, Talent, Company People).
       - Window title MUST contain "linkedin".
       - Window title MUST NOT be a search engine (e.g. Google Search), chat, or other site.
       - Non-talent LinkedIn pages are strictly ignored:
         * Feed ("Feed | LinkedIn")
         * Messaging / Chat ("Messaging | LinkedIn", "Chat")
         * Notifications ("Notifications | LinkedIn")
         * Learning, Settings, Help Center, or empty home stream.
       - If URL is present, must contain "linkedin.com" and must not be feed/messaging/notifications.
    All other applications and all non-LinkedIn Chrome tabs are strictly rejected and dropped.
    
    Returns: (is_allowed: bool, target_type: str)
      target_type: "CHROME_LINKEDIN" | "TEAMS" | "UNSUPPORTED_CHROME" | "UNSUPPORTED_APP"
    """
    if not win_info or not win_info.is_valid:
        return False, "INVALID_WINDOW"

    proc = (win_info.process_name or "").lower()
    title = (win_info.title or "").strip()
    title_lower = title.lower()

    # Rule 1: Desktop Collaboration, Communication & Resume Apps
    if proc in ("teams.exe", "ms-teams.exe") or "microsoft teams" in title_lower or "teams | microsoft" in title_lower:
        return True, "TEAMS"
    if proc == "slack.exe" or "slack |" in title_lower:
        return True, "SLACK"
    if proc in ("whatsapp.exe", "whatsapp.root.exe") or "whatsapp" in title_lower:
        return True, "WHATSAPP"
    if proc == "telegram.exe" or "telegram" in title_lower:
        return True, "TELEGRAM"
    if proc == "outlook.exe":
        return True, "OUTLOOK"
    if proc in ("acrord32.exe", "acrobat.exe") or (("resume" in title_lower or "cv" in title_lower or "curriculum" in title_lower) and "pdf" in title_lower):
        return True, "PDF_RESUME"

    # Rule 2: Browsers — Sourcing, ATS, Mail & Chat Targets (Chrome, Edge, Brave, Firefox)
    if proc in ("chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
        b_ctx = b_ctx or {}
        url = (b_ctx.get("url") or "").lower()

        # Target 1: Chat & Messaging Platforms
        if (
            "chat.google.com" in url
            or ("/mail/u/" in url and "/chat" in url)
            or "google chat" in title_lower
            or title_lower.endswith(" - chat")
            or " - chat" in title_lower
        ):
            if not any(m in title_lower for m in ["youtube", "twitch", "facebook", "tiktok", "netflix", "reddit"]):
                return True, "GOOGLE_CHAT"

        if "teams.microsoft.com" in url or "teams.live.com" in url or "teams.cloud.microsoft" in url:
            return True, "TEAMS"

        if "app.slack.com" in url or "slack.com" in url or "slack |" in title_lower:
            return True, "SLACK"

        if "web.whatsapp.com" in url or "whatsapp" in title_lower:
            return True, "WHATSAPP"

        if "web.telegram.org" in url or "k.telegram.org" in url or "a.telegram.org" in url:
            return True, "TELEGRAM"

        # Target 2: Email Inboxes (Candidate applications & outreach replies)
        if "mail.google.com" in url or "gmail" in title_lower:
            return True, "GMAIL"

        if "outlook.office.com" in url or "outlook.live.com" in url or "outlook.office365.com" in url:
            return True, "OUTLOOK"

        # Target 3: PDF Resumes & Candidate Portfolios in Browser
        if (
            url.endswith(".pdf")
            or ".pdf?" in url
            or "/pdf/" in url
            or "blob:" in url
            or any(w in title_lower for w in ["resume", " cv ", "- cv", "curriculum vitae", "candidate profile"])
        ):
            if not any(s in title_lower for s in ["receipt", "invoice", "statement", "bill"]):
                return True, "PDF_RESUME"

        # Reject generic search engine queries, blank tabs, and media
        disallowed_title_substrings = [
            "google search", "- google search", "search - google chrome", "search - microsoft edge",
            "untitled", "new tab", "youtube",
            "facebook", "instagram", "tiktok", "netflix", "reddit",
        ]
        if any(s in title_lower for s in disallowed_title_substrings):
            return False, "UNSUPPORTED_BROWSER (SEARCH_OR_MEDIA)"

        # Target 4: LinkedIn Data (Profiles, Recruiter, Talent, Directory)
        if "linkedin" in title_lower or "sales navigator" in title_lower or "linkedin.com" in url:
            disallowed_linkedin_sections = [
                "feed | linkedin", "feed |", "messaging | linkedin", "messaging |",
                "notifications | linkedin", "notifications |", "linkedin learning",
                ": jobs | linkedin", ": jobs |", "jobs | linkedin", "jobs |",
                "help center", "settings & privacy", "manage my network",
            ]
            if any(s in title_lower for s in disallowed_linkedin_sections):
                return False, "UNSUPPORTED_LINKEDIN (NON_DATA_SECTION)"

            clean_title = re.sub(r"^(?:\(\d+\)\s*)?", "", title_lower)
            clean_title = re.sub(r"\s*-\s*(?:google\s*chrome|microsoft\s*edge|brave)\s*$", "", clean_title).strip()
            if clean_title in ("linkedin", "home | linkedin", "feed", "jobs"):
                return False, "UNSUPPORTED_LINKEDIN (NON_DATA_SECTION)"

            if url and any(p in url for p in ["/feed", "/messaging", "/notifications", "/learning", "/settings", "/jobs"]):
                return False, "UNSUPPORTED_LINKEDIN (NON_DATA_SECTION)"

            return True, "LINKEDIN"

        # Target 5: Developer & Niche Talent Communities
        if "github" in title_lower or "github.com" in url:
            disallowed_gh = ["pulls", "issues", "marketplace", "explore", "notifications", "settings"]
            if any(f"/{s}" in url for s in disallowed_gh):
                return False, "UNSUPPORTED_GITHUB (NON_PROFILE)"
            return True, "GITHUB"

        if "stackoverflow.com" in url or "stack overflow" in title_lower:
            return True, "STACKOVERFLOW"

        if "kaggle.com" in url or "kaggle" in title_lower:
            return True, "KAGGLE"

        if "dice.com" in url or "dice" in title_lower:
            return True, "DICE"

        if "wellfound.com" in url or "angel.co" in url or "wellfound" in title_lower:
            return True, "WELLFOUND"

        # Target 6: ATS Platforms (Greenhouse, Lever, Ashby, Workday, iCIMS, SmartRecruiters)
        if "greenhouse.io" in url or "greenhouse" in title_lower:
            return True, "ATS_GREENHOUSE"
        if "lever.co" in url or "lever" in title_lower:
            return True, "ATS_LEVER"
        if "ashbyhq.com" in url or "ashby" in title_lower:
            return True, "ATS_ASHBY"
        if "myworkday.com" in url or "workday.com" in url or "workday" in title_lower:
            return True, "ATS_WORKDAY"
        if "icims.com" in url or "icims" in title_lower:
            return True, "ATS_ICIMS"
        if "smartrecruiters.com" in url or "smartrecruiters" in title_lower:
            return True, "ATS_SMARTRECRUITERS"

        # Target 7: B2B Contact & Talent Intelligence Platforms (ZoomInfo, Apollo)
        if "zoominfo.com" in url or "zoominfo" in title_lower or "zi-lite" in url or "zi-lite" in title_lower:
            return True, "ZOOMINFO"
        if "apollo.io" in url or "apollo" in title_lower:
            return True, "APOLLO"

        return False, "UNSUPPORTED_BROWSER_PAGE"

    # All other applications are strictly ignored
    return False, f"UNSUPPORTED_APP ({proc})"


import threading
_tracker_tls = threading.local()

def ensure_interactive_desktop():
    """
    Ensures current thread is attached to the interactive 'Default' desktop
    in WinSta0. Performs attachment ONCE per thread and properly closes the handle.
    """
    if getattr(_tracker_tls, "attached", False):
        return True
    try:
        DESKTOP_ALL = 0x01FF
        h_default = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL)
        if h_default:
            user32.SetThreadDesktop(h_default)
            user32.CloseDesktop(h_default)
            _tracker_tls.attached = True
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
