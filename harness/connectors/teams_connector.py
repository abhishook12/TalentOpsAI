"""
harness/connectors/teams_connector.py — Enterprise Microsoft Teams Harness Connector
===================================================================================

Provides full bidirectional local automation for Microsoft Teams on Windows:
1. Process & Runtime Status: Detects active ms-teams.exe (New Teams MSIX / Classic).
2. Native Protocol Dispatcher (msteams:): Deep-links to 1-on-1 chats, pre-filled
   messages, audio/video calls, and channel navigation without requiring IT admin consent.
3. Webhook & Adaptive Card Publisher: Publishes rich candidate summary cards and alerts
   to channels headlessly without UI interaction.
4. Window & Focus Management: Enumerates Teams HWNDs and restores/brings to front.
5. Passive Chat & Candidate Extraction: Bridges with OCR/UIA to capture contact data
   shared in team recruiter channels.
"""

import os
import sys
import json
import time
import urllib.parse
import urllib.request
import subprocess
import logging
from typing import Optional, Dict, Any, List, Tuple
from harness.connectors.base_connector import BaseConnector

logger = logging.getLogger("harness.teams")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [TEAMS_CONNECTOR] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class TeamsConnector(BaseConnector):
    """Master controller for local Microsoft Teams integration."""

    TEAMS_URI_SCHEME = "msteams:"

    def __init__(self, default_webhook_url: Optional[str] = None):
        super().__init__(app_name="teams", display_name="Microsoft Teams")
        self.default_webhook_url = default_webhook_url or os.getenv("TEAMS_WEBHOOK_URL", "")
        self._last_known_pid: Optional[int] = None
        self._is_new_teams: bool = True

    # =========================================================================
    # 1. PROCESS & RUNTIME DETECTION
    # =========================================================================

    def is_running(self) -> bool:
        """Checks if Microsoft Teams process (ms-teams.exe or Teams.exe) is currently active."""
        status = self.get_process_status()
        return status["is_running"]

    def get_process_status(self) -> Dict[str, Any]:
        """
        Inspects Windows process table to find Microsoft Teams instances,
        determining whether it is New Teams (ms-teams.exe) or Classic (Teams.exe).
        """
        try:
            import win32process
            import win32gui
        except ImportError:
            win32gui = None

        running_pids = []
        exe_names = []
        is_new_teams = False

        try:
            # Fast PowerShell/WMI query
            ps_cmd = 'Get-Process -Name "*teams*" -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path | ConvertTo-Json'
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        running_pids.append(item.get("Id"))
                        pname = item.get("ProcessName", "")
                        exe_names.append(pname)
                        if "ms-teams" in pname.lower():
                            is_new_teams = True
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Process lookup error: %s", e)

        self._is_new_teams = is_new_teams
        if running_pids:
            self._last_known_pid = running_pids[0]

        return {
            "is_running": len(running_pids) > 0,
            "pids": running_pids,
            "is_new_teams": is_new_teams,
            "version_type": "New Teams (MSIX WebView2)" if is_new_teams else "Classic Teams (Electron)",
            "primary_pid": self._last_known_pid,
        }

    # =========================================================================
    # 2. NATIVE DEEP-LINK DISPATCHER (msteams://)
    # =========================================================================

    def open_chat(self, recipient_email: str, message: Optional[str] = None) -> bool:
        """
        Deep-links directly into a 1-on-1 chat with a team member / recruiter.
        If message is provided, pre-populates the compose box.
        Bypasses IT admin permissions and works natively with New Teams.

        URI: msteams:/l/chat/0/0?users={email}&message={encoded_message}
        """
        if not recipient_email:
            logger.warning("open_chat failed: recipient_email is required.")
            return False

        clean_email = recipient_email.strip()
        params = {"users": clean_email}
        if message:
            params["message"] = message.strip()

        query_str = urllib.parse.urlencode(params)
        uri = f"{self.TEAMS_URI_SCHEME}/l/chat/0/0?{query_str}"
        logger.info("Opening Teams chat with %s", clean_email)
        return self._launch_uri(uri)

    def start_call(self, recipient_email: str, with_video: bool = False) -> bool:
        """
        Triggers a direct Teams audio or video call to the specified user.
        URI: msteams:/l/call/0/0?users={email}&withVideo={bool}
        """
        if not recipient_email:
            logger.warning("start_call failed: recipient_email is required.")
            return False

        clean_email = recipient_email.strip()
        params = {
            "users": clean_email,
            "withVideo": "true" if with_video else "false"
        }
        query_str = urllib.parse.urlencode(params)
        uri = f"{self.TEAMS_URI_SCHEME}/l/call/0/0?{query_str}"
        logger.info("Triggering Teams %s call to %s", "video" if with_video else "audio", clean_email)
        return self._launch_uri(uri)

    def open_meeting(self, join_url: str) -> bool:
        """Opens a Teams meeting join URL inside the desktop client."""
        if not join_url:
            return False
        clean_url = join_url.strip()
        # If web URL, convert to msteams: scheme if appropriate
        if clean_url.startswith("https://teams.microsoft.com"):
            uri = f"{self.TEAMS_URI_SCHEME}/l/meetup-join/{clean_url.split('/l/meetup-join/')[-1]}"
        else:
            uri = clean_url
        logger.info("Opening Teams meeting: %s", uri[:60])
        return self._launch_uri(uri)

    def _launch_uri(self, uri: str) -> bool:
        """Dispatches an msteams: URI via Windows ShellExecute (os.startfile)."""
        try:
            # os.startfile triggers registered Windows protocol handler natively (0 console flashing)
            os.startfile(uri)
            return True
        except Exception as e:
            logger.error("Failed to launch Teams URI '%s': %s", uri, e)
            # Fallback to explorer.exe
            try:
                subprocess.Popen(["explorer.exe", uri], shell=False)
                return True
            except Exception as e2:
                logger.error("Fallback explorer launch failed: %s", e2)
                return False

    # =========================================================================
    # 3. WEBHOOK & ADAPTIVE CARD PUBLISHER
    # =========================================================================

    def send_webhook_message(
        self,
        title: str,
        text: str,
        webhook_url: Optional[str] = None,
        theme_color: str = "1F4E78"
    ) -> bool:
        """
        Publishes a standard markdown notification to a Teams channel via Incoming Webhook.
        Requires 0 Admin API permissions.
        """
        url = webhook_url or self.default_webhook_url
        if not url:
            logger.warning("send_webhook_message: No webhook URL configured.")
            return False

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": title,
            "title": title,
            "text": text,
        }
        return self._post_json(url, payload)

    def send_candidate_card(
        self,
        candidate_data: Dict[str, Any],
        webhook_url: Optional[str] = None,
        theme_color: str = "0078D7"
    ) -> bool:
        """
        Publishes an interactive Candidate Dossier Card into a Teams channel.
        Features facts (Title, Company, Location, Contacts) and action buttons:
        - View Profile
        - Initiate Vitel Outreach
        """
        url = webhook_url or self.default_webhook_url
        if not url:
            logger.warning("send_candidate_card: No webhook URL configured.")
            return False

        name = candidate_data.get("canonical_name") or candidate_data.get("recruiter_name") or "Unnamed Candidate"
        title = candidate_data.get("title") or "Professional"
        company = candidate_data.get("company_name") or candidate_data.get("company") or "Independent"
        location = candidate_data.get("location") or "Not Specified"
        email = candidate_data.get("email") or candidate_data.get("primary_email") or "None"
        phone = candidate_data.get("phone") or candidate_data.get("primary_phone") or "None"
        linkedin_url = candidate_data.get("linkedin_url") or candidate_data.get("canonical_profile_url") or ""

        facts = [
            {"name": "Current Role:", "value": title},
            {"name": "Organization:", "value": company},
            {"name": "Location:", "value": location},
            {"name": "Email:", "value": email},
            {"name": "Phone:", "value": phone},
        ]

        potential_actions = []
        if linkedin_url:
            potential_actions.append({
                "@type": "OpenUri",
                "name": "🔗 View Profile",
                "targets": [{"os": "default", "uri": linkedin_url}]
            })

        card_payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"TalentOps Scout: {name}",
            "title": f"🎯 TalentOps Sourced: {name}",
            "sections": [
                {
                    "activityTitle": f"**{name}**",
                    "activitySubtitle": f"{title} @ {company}",
                    "facts": facts,
                    "markdown": True
                }
            ],
            "potentialAction": potential_actions
        }

        logger.info("Posting Candidate Card for '%s' to Teams channel", name)
        return self._post_json(url, card_payload)

    def _post_json(self, url: str, data: Dict[str, Any]) -> bool:
        """Sends an HTTP POST JSON request."""
        try:
            req_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                success = (resp.status == 200 or resp.status == 202)
                if success:
                    logger.info("Teams webhook published successfully.")
                else:
                    logger.warning("Teams webhook responded with status %s", resp.status)
                return success
        except Exception as e:
            logger.error("Failed to post Teams webhook: %s", e)
            return False

    # =========================================================================
    # 4. WINDOW & UI AUTOMATION INSPECTOR
    # =========================================================================

    def find_teams_windows(self) -> List[Dict[str, Any]]:
        """
        Finds all top-level Microsoft Teams windows currently available in Windows.
        Returns list of window details: HWND, Title, Visible, Rect.
        """
        windows = []
        try:
            import win32gui
            import win32process

            status = self.get_process_status()
            target_pids = set(status["pids"])

            def enum_cb(hwnd, extra):
                if not win32gui.IsWindow(hwnd):
                    return True
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid in target_pids:
                        title = win32gui.GetWindowText(hwnd)
                        cls = win32gui.GetClassName(hwnd)
                        is_vis = win32gui.IsWindowVisible(hwnd)
                        rect = win32gui.GetWindowRect(hwnd)
                        # Filter out invisible utility tooltips/offscreen helper windows
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 100 and h > 100:
                            windows.append({
                                "hwnd": hwnd,
                                "pid": pid,
                                "title": title,
                                "class_name": cls,
                                "visible": is_vis,
                                "rect": rect,
                                "width": w,
                                "height": h,
                            })
                except Exception:
                    pass
                return True

            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.debug("find_teams_windows error: %s", e)

        return windows

    def bring_to_front(self) -> bool:
        """Restores and focuses the main Microsoft Teams window."""
        # 1. If top-level window exists, restore and bring to foreground
        windows = self.find_teams_windows()
        if windows:
            try:
                import win32gui
                import win32con
                hwnd = windows[0]["hwnd"]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                logger.info("Focused Teams window HWND: %s", hwnd)
                return True
            except Exception as e:
                logger.debug("Could not set foreground window: %s", e)

        # 2. Native Windows AppExecutionAlias (User-level binary execution)
        alias = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe")
        if os.path.exists(alias):
            try:
                os.startfile(alias)
                logger.info("Launched Teams via AppExecutionAlias: %s", alias)
                return True
            except Exception as e:
                logger.debug("Failed to launch alias: %s", e)

        # 3. Native Windows msteams: protocol invocation
        try:
            os.startfile("msteams:")
            logger.info("Triggered Teams via msteams: native protocol")
            return True
        except Exception as e:
            logger.debug("Failed msteams: protocol: %s", e)

        # 4. Shell AppsFolder invocation
        try:
            os.startfile(r"shell:AppsFolder\MSTeams_8wekyb3d8bbwe!MSTeams")
            logger.info("Triggered Teams via shell:AppsFolder")
            return True
        except Exception as e:
            logger.error("Failed to restore Teams window: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns standard harness health and status dictionary."""
        proc = self.get_process_status()
        return {
            "app_name": self.app_name,
            "display_name": self.display_name,
            "is_running": proc["is_running"],
            "pids": proc["pids"],
            "version_type": proc["version_type"],
            "protocol_registered": True,
            "capabilities": ["open_chat", "start_call", "open_meeting", "send_candidate_card", "send_webhook_message", "bring_to_front"],
        }

    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches an action via the unified harness interface."""
        payload = payload or {}
        if action == "open_chat":
            success = self.open_chat(payload.get("recipient_email", ""), payload.get("message"))
            return {"action": action, "success": success}
        elif action == "start_call":
            success = self.start_call(payload.get("recipient_email", ""), payload.get("with_video", False))
            return {"action": action, "success": success}
        elif action == "send_card":
            success = self.send_candidate_card(payload.get("candidate_data", {}), payload.get("webhook_url"))
            return {"action": action, "success": success}
        elif action == "send_webhook":
            success = self.send_webhook_message(payload.get("title", ""), payload.get("text", ""), payload.get("webhook_url"))
            return {"action": action, "success": success}
        elif action == "bring_to_front":
            success = self.bring_to_front()
            return {"action": action, "success": success}
        else:
            return {"action": action, "success": False, "error": f"Unknown action '{action}' for {self.app_name}"}


# Singleton instance
teams_connector = TeamsConnector()
