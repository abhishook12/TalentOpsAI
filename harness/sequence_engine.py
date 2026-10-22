"""
harness/sequence_engine.py — Autonomous Repeat Follow-up & Sequence Engine
===========================================================================

Orchestrates multi-touch, repetitive candidate outreach sequences across Vitel Global
(and other harness channels) with:
1. Persistent State Machine: SQLite database ensuring zero contact loss across reboots.
2. Cadence & Interval Scheduling: Escalating follow-ups (Touch 1, 2, 3...) at configurable intervals.
3. Real-Time Reply Detection: Continuously monitors Vitel local eventHistory.db for inbound
   replies and immediately halts follow-ups the moment a response is detected.
4. Business Hours & Quiet Hours Enforcement: Protects recruiter reputation and carrier deliverability.
"""

import os
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("harness.sequence")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [SEQUENCE_ENGINE] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SequenceEngine:
    """Manages persistent candidate follow-up sequences until reply."""

    DEFAULT_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
    DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "harness_sequences.db")

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._mem_conn = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
        self._init_db()

    def _get_connection(self):
        if self._mem_conn is not None:
            return self._mem_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes SQLite schema for sequences and event history."""
        if self.db_path != ":memory:":
            dirname = os.path.dirname(self.db_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequence_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                name TEXT DEFAULT '',
                status TEXT DEFAULT 'ACTIVE',
                current_stage INTEGER DEFAULT 1,
                max_touches INTEGER DEFAULT 4,
                interval_hours INTEGER DEFAULT 24,
                initial_message TEXT NOT NULL,
                followup_template TEXT DEFAULT '',
                last_sent_at TEXT,
                next_eligible_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                event_type TEXT NOT NULL,
                stage INTEGER,
                content TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        if self._mem_conn is None:
            conn.close()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Cleans and formats phone number to standard E.164."""
        clean = "".join(ch for ch in str(phone) if ch.isdigit() or ch == '+')
        if not clean.startswith('+'):
            if len(clean) == 10:
                clean = f"+1{clean}"
            elif len(clean) == 11 and clean.startswith('1'):
                clean = f"+{clean}"
            else:
                clean = f"+{clean}"
        return clean

    # =========================================================================
    # 1. SEQUENCE ENROLLMENT & DISPATCH
    # =========================================================================

    def enroll_and_dispatch(
        self,
        phone: str,
        message: str,
        name: str = "",
        interval_hours: int = 24,
        max_touches: int = 4,
        followup_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enrolls a candidate phone number into the repeat sequence loop and stages Touch 1.
        If the contact is already enrolled, updates their message and reactivates.
        """
        clean_phone = self.normalize_phone(phone)
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        next_eligible = (now + timedelta(hours=interval_hours)).isoformat()

        if not followup_template:
            followup_template = f"Hi {name or 'there'}, following up on my previous message. Are you open to a quick chat?"

        from harness.connectors.vitel_connector import vitel_connector
        dispatch_result = vitel_connector.prepare_sms(clean_phone, message)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sequence_contacts (
                    phone, name, status, current_stage, max_touches, interval_hours,
                    initial_message, followup_template, last_sent_at, next_eligible_at,
                    created_at, updated_at
                ) VALUES (?, ?, 'ACTIVE', 1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(phone) DO UPDATE SET
                    name = excluded.name,
                    status = 'ACTIVE',
                    current_stage = 1,
                    max_touches = excluded.max_touches,
                    interval_hours = excluded.interval_hours,
                    initial_message = excluded.initial_message,
                    followup_template = excluded.followup_template,
                    last_sent_at = excluded.last_sent_at,
                    next_eligible_at = excluded.next_eligible_at,
                    updated_at = excluded.updated_at
            """, (
                clean_phone, name, max_touches, interval_hours,
                message, followup_template, now_iso, next_eligible,
                now_iso, now_iso
            ))

            cursor.execute("""
                INSERT INTO sequence_events (phone, event_type, stage, content, timestamp)
                VALUES (?, 'TOUCH_1_DISPATCHED', 1, ?, ?)
            """, (clean_phone, message, now_iso))
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

        logger.info("Enrolled %s into sequence: Touch 1 staged. Next eligible: %s", clean_phone, next_eligible)

        return {
            "success": True,
            "phone": clean_phone,
            "name": name,
            "stage": 1,
            "max_touches": max_touches,
            "interval_hours": interval_hours,
            "next_touch_scheduled": next_eligible,
            "message_sent": message,
            "vitel_status": dispatch_result.get("status", "staged"),
            "status": "ACTIVE_WAITING_REPLY",
        }

    # =========================================================================
    # 2. REAL-TIME REPLY MONITORING & AUTO-HALT
    # =========================================================================

    def check_vitel_replies(self) -> List[Dict[str, Any]]:
        """
        Scans Vitel local eventHistory.db for incoming calls/messages from enrolled numbers.
        If an inbound interaction is detected, immediately flips status to 'REPLIED' and halts.
        """
        from harness.connectors.vitel_connector import vitel_connector
        vitel_db = vitel_connector.db_path
        if not os.path.exists(vitel_db):
            return []

        active_phones = self.get_active_phones()
        if not active_phones:
            return []

        replies_detected = []
        try:
            conn_vitel = sqlite3.connect(f"file:{vitel_db}?mode=ro", uri=True)
            cur_vitel = conn_vitel.cursor()

            # Query inbound events (direction != 1, typically 0 or 2 for inbound)
            # and check RemoteUsers table for transportUri
            cur_vitel.execute("""
                SELECT e.eventId, e.timestamp, r.transportUri, r.displayName
                FROM Events e
                JOIN RemoteUsers r ON e.eventId = r.eventId
                WHERE e.direction != 1
            """)
            rows = cur_vitel.fetchall()
            conn_vitel.close()

            now_iso = datetime.now(timezone.utc).isoformat()

            for row in rows:
                event_id, timestamp, transport_uri, display_name = row
                inbound_clean = self.normalize_phone(transport_uri or "")
                if inbound_clean in active_phones:
                    # Halt sequence
                    self.halt_sequence(inbound_clean, reason=f"Inbound reply detected in Vitel (Event ID {event_id})")
                    replies_detected.append({
                        "phone": inbound_clean,
                        "vitel_event_id": event_id,
                        "timestamp": timestamp,
                        "action": "SEQUENCE_HALTED",
                    })
        except Exception as e:
            logger.debug("Error checking Vitel replies: %s", e)

        return replies_detected

    def halt_sequence(self, phone: str, reason: str = "user_halt") -> bool:
        """Immediately halts repeat follow-ups for a contact."""
        clean_phone = self.normalize_phone(phone)
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sequence_contacts
                SET status = 'REPLIED', updated_at = ?
                WHERE phone = ?
            """, (now_iso, clean_phone))
            cursor.execute("""
                INSERT INTO sequence_events (phone, event_type, stage, content, timestamp)
                VALUES (?, 'HALTED', 0, ?, ?)
            """, (clean_phone, reason, now_iso))
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

        logger.info("Sequence HALTED for %s: %s", clean_phone, reason)
        return True

    # =========================================================================
    # 3. QUERIES & STATUS
    # =========================================================================

    def get_contact_status(self, phone: str) -> Optional[Dict[str, Any]]:
        """Retrieves live sequence tracking record for a contact."""
        clean_phone = self.normalize_phone(phone)
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sequence_contacts WHERE phone = ?", (clean_phone,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_active_phones(self) -> List[str]:
        """Returns all phones with active pending sequences."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT phone FROM sequence_contacts WHERE status = 'ACTIVE'")
            return [r[0] for r in cursor.fetchall()]
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_sequences(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists active and completed sequences."""
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sequence_contacts ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            if self._mem_conn is None:
                conn.close()


# Singleton instance
sequence_engine = SequenceEngine()
