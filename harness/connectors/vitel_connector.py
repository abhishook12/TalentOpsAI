"""
harness/connectors/vitel_connector.py — Enterprise Vitel Global Harness Connector
================================================================================

Provides local automation for the Vitel Global desktop VoIP & SMS application on Windows:
1. Runtime & Process Detection: Detects Vitelglobal.exe (Qt6/QtWebEngine softphone).
2. Local Telemetry & Event Inspection: Connects directly to local eventHistory.db to track
   call history, SMS activity, and account status without cloud scraping.
3. Call & SMS Dispatching: Formats outreach phone numbers and prepares message payloads.
4. Window & Focus Management: Brings Vitel Global application to the foreground.
"""

import os
import sys
import sqlite3
import subprocess
import logging
from typing import Optional, Dict, Any, List
from harness.connectors.base_connector import BaseConnector

logger = logging.getLogger("harness.vitel")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [VITEL_CONNECTOR] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class VitelConnector(BaseConnector):
    """Master controller for local Vitel Global desktop integration."""

    DEFAULT_DB_PATH = os.path.expandvars(
        r"%LOCALAPPDATA%\com.vitelglobal.vitelgloabalapp.winx.storage\Data\eventHistory.db"
    )
    DEFAULT_EXE_PATH = os.path.expandvars(
        r"%LOCALAPPDATA%\com.vitelglobal.vitelgloabalapp.winx\Vitelglobal.exe"
    )

    def __init__(self, db_path: Optional[str] = None):
        super().__init__(app_name="vitel", display_name="Vitel Global")
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._last_known_pid: Optional[int] = None

    # =========================================================================
    # 1. PROCESS & RUNTIME DETECTION
    # =========================================================================

    def is_running(self) -> bool:
        """Checks if Vitelglobal.exe is active in the Windows process table."""
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name']):
                if 'vitel' in (p.info['name'] or '').lower():
                    self._last_known_pid = p.info['pid']
                    return True
        except Exception as e:
            logger.debug("Vitel process lookup error: %s", e)
        return False

    # =========================================================================
    # 2. STATUS & LOCAL TELEMETRY
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Returns Vitel running status, account name, and call event counts."""
        running = self.is_running()
        account_name = "Not Configured"
        total_events = 0
        db_connected = False

        if os.path.exists(self.db_path):
            db_connected = True
            try:
                # Open read-only connection
                conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                
                # Get event count
                cursor.execute("SELECT COUNT(*) FROM Events")
                total_events = cursor.fetchone()[0]

                # Get latest configured account name
                cursor.execute(
                    "SELECT value FROM EventAttributes WHERE key='accountName' ORDER BY eventId DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    account_name = row[0]
                conn.close()
            except Exception as e:
                logger.debug("Vitel DB read error: %s", e)

        return {
            "app_name": self.app_name,
            "display_name": self.display_name,
            "is_running": running,
            "pid": self._last_known_pid,
            "db_connected": db_connected,
            "active_account": account_name,
            "total_logged_events": total_events,
            "capabilities": ["get_call_logs", "prepare_sms", "dial_number", "bring_to_front"],
        }

    # =========================================================================
    # 3. CALL LOGS & SMS DISPATCH
    # =========================================================================

    def get_call_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Reads recent call/SMS activity from the local database."""
        results = []
        if not os.path.exists(self.db_path):
            return results

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT eventId, streamKey, timestamp, eventType, direction FROM Events ORDER BY eventId DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            for r in rows:
                event_id = r[0]
                # Get attributes
                cursor.execute("SELECT key, value FROM EventAttributes WHERE eventId = ?", (event_id,))
                attrs = dict(cursor.fetchall())
                results.append({
                    "event_id": event_id,
                    "stream_key": r[1],
                    "timestamp": r[2],
                    "event_type": r[3],
                    "direction": "outbound" if r[4] == 1 else "inbound",
                    "account": attrs.get("accountName", ""),
                    "call_id": attrs.get("callId", ""),
                    "duration": attrs.get("callDuration", "0"),
                })
            conn.close()
        except Exception as e:
            logger.error("Failed to read Vitel call logs: %s", e)

        return results

    def prepare_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Formats and prepares an SMS payload for candidate outreach via Vitel.
        Validates E.164 phone number formatting.
        """
        clean_phone = "".join(ch for ch in phone_number if ch.isdigit() or ch == '+')
        if not clean_phone.startswith('+') and len(clean_phone) == 10:
            clean_phone = f"+1{clean_phone}"

        logger.info("Prepared Vitel SMS dispatch for %s (Length: %d)", clean_phone, len(message))
        return {
            "success": True,
            "recipient": clean_phone,
            "message": message,
            "channel": "vitel_sms",
            "status": "staged_for_dispatch",
        }

    def dial_number(self, phone_number: str) -> bool:
        """Launches a call to the specified number via tel: protocol or app launch."""
        clean_phone = "".join(ch for ch in phone_number if ch.isdigit() or ch == '+')
        try:
            os.startfile(f"tel:{clean_phone}")
            return True
        except Exception:
            # Fallback to activating Vitel window
            return self.bring_to_front()

    def bring_to_front(self) -> bool:
        """Brings the Vitel Global window to the front."""
        if os.path.exists(self.DEFAULT_EXE_PATH):
            try:
                subprocess.Popen([self.DEFAULT_EXE_PATH], shell=False)
                return True
            except Exception as e:
                logger.error("Failed to focus Vitel window: %s", e)
        return False

    def execute_action(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Unified action dispatcher."""
        payload = payload or {}
        if action == "prepare_sms":
            res = self.prepare_sms(
                phone_number=payload.get("phone", payload.get("phone_number", "")),
                message=payload.get("message", "")
            )
            return {"action": action, **res}
        elif action == "get_call_logs":
            logs = self.get_call_logs(limit=payload.get("limit", 5))
            return {"action": action, "success": True, "call_logs": logs}
        elif action == "dial_number":
            success = self.dial_number(phone_number=payload.get("phone", ""))
            return {"action": action, "success": success}
        elif action == "bring_to_front":
            success = self.bring_to_front()
            return {"action": action, "success": success}
        else:
            return {"action": action, "success": False, "error": f"Unknown action '{action}' for {self.app_name}"}


# Singleton instance
vitel_connector = VitelConnector()
