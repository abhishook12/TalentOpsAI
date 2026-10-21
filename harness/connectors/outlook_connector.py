"""
harness/connectors/outlook_connector.py — Enterprise Microsoft Outlook Harness Connector
=======================================================================================

Provides local automation for desktop Microsoft Outlook on Windows:
1. Runtime & Process Detection: Detects OUTLOOK.EXE (Office16 / Click-to-Run / MSI).
2. Native COM / MAPI Integration: Connects directly via Outlook.Application without UI interference.
3. Candidate Pitch & Outreach Drafting: Formats and drafts candidate pitch emails or sends them.
4. Inbox & Reply Monitoring: Inspects incoming candidate/recruiter responses.
5. mailto: Protocol Fallback: Dispatches native OS mail composer when COM is sandboxed.
"""

import os
import sys
import subprocess
import urllib.parse
import logging
from typing import Optional, Dict, Any, List
from harness.connectors.base_connector import BaseConnector

logger = logging.getLogger("harness.outlook")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [OUTLOOK_CONNECTOR] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class OutlookConnector(BaseConnector):
    """Master controller for local Microsoft Outlook desktop integration."""

    def __init__(self):
        super().__init__(app_name="outlook", display_name="Microsoft Outlook")
        self._outlook_com = None
        self._mapi_ns = None

    # =========================================================================
    # 1. PROCESS & RUNTIME DETECTION
    # =========================================================================

    def is_running(self) -> bool:
        """Checks if OUTLOOK.EXE is active in the Windows process table."""
        try:
            import psutil
            for p in psutil.process_iter(['name']):
                if (p.info['name'] or '').lower() == 'outlook.exe':
                    return True
        except Exception as e:
            logger.debug("Process lookup error: %s", e)
        return False

    def _get_com_session(self):
        """Initializes or reuses the Outlook COM MAPI session."""
        try:
            import win32com.client
            if not self._outlook_com:
                self._outlook_com = win32com.client.Dispatch("Outlook.Application")
                self._mapi_ns = self._outlook_com.GetNamespace("MAPI")
            return self._outlook_com, self._mapi_ns
        except Exception as e:
            logger.warning("Could not initialize Outlook COM: %s", e)
            return None, None

    # =========================================================================
    # 2. STATUS & TELEMETRY
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Returns Outlook running status, inbox counts, and capabilities."""
        running = self.is_running()
        inbox_count = 0
        unread_count = 0
        default_account = "Unknown"
        com_active = False

        if running:
            app, ns = self._get_com_session()
            if ns:
                com_active = True
                try:
                    inbox = ns.GetDefaultFolder(6)  # 6 = olFolderInbox
                    inbox_count = inbox.Items.Count
                    unread_count = inbox.UnReadItemCount
                    if ns.Accounts.Count > 0:
                        default_account = ns.Accounts.Item(1).DisplayName
                except Exception as e:
                    logger.debug("MAPI folder lookup error: %s", e)

        return {
            "app_name": self.app_name,
            "display_name": self.display_name,
            "is_running": running,
            "com_active": com_active,
            "default_account": default_account,
            "inbox_count": inbox_count,
            "unread_count": unread_count,
            "capabilities": ["create_email", "get_recent_emails", "bring_to_front"],
        }

    # =========================================================================
    # 3. EMAIL COMPOSING & DRAFTING
    # =========================================================================

    def create_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        send_now: bool = False,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Creates an email in Outlook via COM.
        If send_now is False, saves it to Drafts for recruiter review.
        """
        app, _ = self._get_com_session()
        if app:
            try:
                mail = app.CreateItem(0)  # 0 = olMailItem
                mail.To = to_email
                mail.Subject = subject
                mail.HTMLBody = body_html
                if attachments:
                    for att in attachments:
                        if os.path.exists(att):
                            mail.Attachments.Add(att)

                if send_now:
                    mail.Send()
                    logger.info("Sent email to %s via Outlook COM", to_email)
                else:
                    mail.Save()
                    logger.info("Drafted email for %s in Outlook Drafts", to_email)
                return True
            except Exception as e:
                logger.error("Failed to create email via COM: %s", e)

        # Fallback to mailto:
        return self._launch_mailto(to_email, subject, body_html)

    def _launch_mailto(self, to_email: str, subject: str, body: str) -> bool:
        """Fallback to native mailto: URL dispatch."""
        try:
            params = {"subject": subject, "body": body}
            query = urllib.parse.urlencode(params)
            url = f"mailto:{to_email}?{query}"
            os.startfile(url)
            return True
        except Exception as e:
            logger.error("mailto fallback failed: %s", e)
            return False

    def get_recent_emails(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Reads recent received emails from the Outlook Inbox."""
        results = []
        _, ns = self._get_com_session()
        if not ns:
            return results

        try:
            inbox = ns.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)  # Descending
            count = 0
            for item in items:
                if count >= limit:
                    break
                try:
                    results.append({
                        "subject": getattr(item, "Subject", "No Subject"),
                        "sender": getattr(item, "SenderEmailAddress", getattr(item, "SenderName", "")),
                        "received_time": str(getattr(item, "ReceivedTime", "")),
                        "unread": getattr(item, "UnRead", False),
                    })
                    count += 1
                except Exception:
                    continue
        except Exception as e:
            logger.error("Error reading recent emails: %s", e)

        return results

    def bring_to_front(self) -> bool:
        """Restores and brings the main Outlook window to the front."""
        app, _ = self._get_com_session()
        if app:
            try:
                explorer = app.ActiveExplorer()
                if explorer:
                    explorer.Activate()
                    return True
            except Exception as e:
                logger.debug("Explorer activate error: %s", e)

        try:
            subprocess.Popen(["outlook.exe"], shell=False)
            return True
        except Exception as e:
            logger.error("Could not launch Outlook: %s", e)
            return False

    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Unified action dispatcher."""
        payload = payload or {}
        if action == "create_email":
            success = self.create_email(
                to_email=payload.get("to_email", ""),
                subject=payload.get("subject", ""),
                body_html=payload.get("body_html", payload.get("body", "")),
                send_now=payload.get("send_now", False),
                attachments=payload.get("attachments")
            )
            return {"action": action, "success": success}
        elif action == "get_recent_emails":
            emails = self.get_recent_emails(limit=payload.get("limit", 5))
            return {"action": action, "success": True, "emails": emails}
        elif action == "bring_to_front":
            success = self.bring_to_front()
            return {"action": action, "success": success}
        else:
            return {"action": action, "success": False, "error": f"Unknown action '{action}' for {self.app_name}"}


# Singleton instance
outlook_connector = OutlookConnector()
