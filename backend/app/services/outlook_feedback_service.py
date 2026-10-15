import re
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.outlook_feedback import OutlookFeedbackLog
from ..models.campaigns import CampaignRecruiter, Campaign
from ..models.models import Recruiter
from .mailintel_engine import process_delivery_event
from .recruiter_store import recruiter_store
from .parquet_writer import parquet_writer

logger = logging.getLogger("OutlookFeedbackService")

# Mutex to ensure non-conflicting Outlook COM access with send_engine
_outlook_feedback_lock = threading.Lock()

# Multi-pattern regex for RFC 3464 bounces & SMTP delivery diagnostics
RE_BOUNCE_TARGET_1 = re.compile(
    r'<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>:\s*(?:host[^\n\r]+said:\s*)?([^\n\r]+)',
    re.IGNORECASE
)
RE_BOUNCE_TARGET_2 = re.compile(
    r'permanent fatal errors\s*-+\s*<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>',
    re.IGNORECASE
)
RE_BOUNCE_TARGET_3 = re.compile(
    r'Final-Recipient:\s*rfc822;\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE
)
RE_BOUNCE_CODE = re.compile(
    r'\b(55[0-9]|5[0-9]{2}\s*5\.[0-9]\.[0-9]|45[0-9]|4[0-9]{2}\s*4\.[0-9]\.[0-9])\b'
)

# Delivery confirmation pattern (e.g. Psotmaster / Delivered)
RE_DELIVERED_TARGET = re.compile(
    r'delivered to the following recipients?:\s*(?:<mailto:)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
    re.IGNORECASE
)

# Common internal / platform emails to exclude as target recipient
SYSTEM_EXCLUDED_EMAILS = {
    "postmaster", "mailer-daemon", "mail delivery system", "microsoft",
    "technovion.com", "adcc.com"
}


def parse_outlook_message(msg: Any, folder_name: str) -> List[Dict[str, Any]]:
    """
    Parses a single Outlook MAPI message item and extracts delivery feedback events.
    Returns a list of parsed feedback dicts (one message may reference multiple recipients).
    """
    events = []
    try:
        entry_id = getattr(msg, "EntryID", None)
        if not entry_id:
            return []

        subject = getattr(msg, "Subject", "") or ""
        sender_name = getattr(msg, "SenderName", "") or ""
        sender_email = getattr(msg, "SenderEmailAddress", "") or ""
        received_time = getattr(msg, "ReceivedTime", None)
        body = getattr(msg, "Body", "") or ""

        # Normalize received_time to datetime
        ts = None
        if received_time:
            try:
                # pywin32 returns pywintypes.datetime
                ts = datetime.fromtimestamp(received_time.timestamp(), tz=timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        sender_combined = f"{sender_name} <{sender_email}>".strip()
        lower_folder = folder_name.lower()
        lower_subj = subject.lower()

        # ── 1. Check for Delivered Confirmation (Psotmaster / Delivered) ──
        if "psotmaster" in lower_folder or "delivered" in lower_folder or lower_subj.startswith("delivered:"):
            delivered_matches = RE_DELIVERED_TARGET.findall(body)
            if not delivered_matches:
                # Fallback: find any clean recipient mailto in body
                mailtos = re.findall(r'<mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>', body)
                delivered_matches = mailtos

            for email in set(delivered_matches):
                clean_email = email.strip().lower()
                if not any(ex in clean_email for ex in ["postmaster", "mailer-daemon"]):
                    events.append({
                        "entry_id": f"{entry_id}_{clean_email}",
                        "folder_name": folder_name,
                        "subject": subject[:490],
                        "sender": sender_combined[:250],
                        "recipient_email": clean_email,
                        "event_type": "delivered",
                        "smtp_code": "250",
                        "diagnostic_reason": "Delivered to remote mail server successfully",
                        "received_at": ts
                    })

        # ── 2. Check for Bounces / NDRs (Undilevered mail / Bounces / Mailer-Daemon) ──
        if "undilevered" in lower_folder or "undelivered" in lower_folder or "undelivered" in lower_subj or "returned" in lower_subj or "failure" in lower_subj:
            # Try Pattern 1: <email>: host ... said: 550 ...
            matches_p1 = RE_BOUNCE_TARGET_1.findall(body)
            matched_emails = set()

            for email, diag in matches_p1:
                clean_email = email.strip().lower()
                if clean_email in matched_emails:
                    continue
                matched_emails.add(clean_email)

                # Extract SMTP code if present in diagnostic snippet
                code_match = RE_BOUNCE_CODE.search(diag)
                smtp_code = code_match.group(1) if code_match else "550"
                event_type = "soft_bounce" if smtp_code.startswith("4") else "hard_bounce"
                clean_diag = diag.strip().replace("\n", " ").replace("\r", " ")[:400]

                events.append({
                    "entry_id": f"{entry_id}_{clean_email}",
                    "folder_name": folder_name,
                    "subject": subject[:490],
                    "sender": sender_combined[:250],
                    "recipient_email": clean_email,
                    "event_type": event_type,
                    "smtp_code": smtp_code,
                    "diagnostic_reason": clean_diag or "Undelivered mail returned to sender",
                    "received_at": ts
                })

            # Try Pattern 2 & 3 if Pattern 1 found nothing
            if not events:
                p2_emails = RE_BOUNCE_TARGET_2.findall(body) + RE_BOUNCE_TARGET_3.findall(body)
                for email in set(p2_emails):
                    clean_email = email.strip().lower()
                    if clean_email not in matched_emails:
                        matched_emails.add(clean_email)
                        code_match = RE_BOUNCE_CODE.search(body)
                        smtp_code = code_match.group(1) if code_match else "550"
                        event_type = "soft_bounce" if smtp_code.startswith("4") else "hard_bounce"
                        events.append({
                            "entry_id": f"{entry_id}_{clean_email}",
                            "folder_name": folder_name,
                            "subject": subject[:490],
                            "sender": sender_combined[:250],
                            "recipient_email": clean_email,
                            "event_type": event_type,
                            "smtp_code": smtp_code,
                            "diagnostic_reason": "Permanent delivery failure (NDR)",
                            "received_at": ts
                        })

    except Exception as e:
        logger.debug("Error parsing Outlook message: %s", e)

    return events


def ingest_feedback_event(event_dict: Dict[str, Any], db: Session) -> Optional[OutlookFeedbackLog]:
    """
    Ingests a single parsed feedback event into the database and synchronizes:
    - CampaignRecruiter rows (status -> Bounced or Delivered)
    - Master Recruiter directory (email_status -> invalid if hard bounce)
    - Parquet / DuckDB recruiter_store
    - MailIntel DomainReputation
    """
    entry_id = event_dict.get("entry_id")
    if not entry_id:
        return None

    # 1. Deduplication guard: skip already recorded entry_id
    existing = db.query(OutlookFeedbackLog).filter(OutlookFeedbackLog.entry_id == entry_id).first()
    if existing:
        return None

    email = event_dict.get("recipient_email", "").strip().lower()
    event_type = event_dict.get("event_type", "hard_bounce")
    reason = event_dict.get("diagnostic_reason", "")
    smtp_code = event_dict.get("smtp_code", "")
    received_at = event_dict.get("received_at") or datetime.now(timezone.utc)

    # 2. Match recruiter from master catalog
    recruiter = db.query(Recruiter).filter(Recruiter.email.ilike(email)).first()
    recruiter_id = recruiter.recruiter_id if recruiter else None

    # 3. Match campaign recruiter (most recent enrollment for this email)
    campaign_id = None
    cr_row = None
    if recruiter_id:
        cr_row = (
            db.query(CampaignRecruiter)
            .filter(CampaignRecruiter.recruiter_id == recruiter_id)
            .order_by(CampaignRecruiter.enrolled_at.desc())
            .first()
        )
    if not cr_row:
        # Try joining by recruiter email directly
        cr_row = (
            db.query(CampaignRecruiter)
            .join(Recruiter, CampaignRecruiter.recruiter_id == Recruiter.recruiter_id)
            .filter(Recruiter.email.ilike(email))
            .order_by(CampaignRecruiter.enrolled_at.desc())
            .first()
        )

    if cr_row:
        campaign_id = cr_row.campaign_id

    # 4. Create log record
    log_rec = OutlookFeedbackLog(
        entry_id=entry_id,
        folder_name=event_dict.get("folder_name", ""),
        subject=event_dict.get("subject", ""),
        sender=event_dict.get("sender", ""),
        recipient_email=email,
        event_type=event_type,
        smtp_code=smtp_code,
        diagnostic_reason=reason,
        campaign_id=campaign_id,
        recruiter_id=recruiter_id,
        received_at=received_at
    )
    db.add(log_rec)

    # 5. Update CampaignRecruiter status
    if cr_row:
        if event_type in ("hard_bounce", "soft_bounce"):
            cr_row.status = "Bounced"
            cr_row.bounced_at = received_at
            cr_row.last_error = f"[{smtp_code}] {reason}"[:450]
        elif event_type == "delivered" and cr_row.status in ("Sent", "Sending", "Queued"):
            cr_row.status = "Delivered"

    # 6. Update Master Recruiter directory
    if recruiter:
        if event_type in ("hard_bounce", "soft_bounce"):
            recruiter.email_status = "invalid" if event_type == "hard_bounce" else "unverified"
            if event_type == "hard_bounce":
                recruiter.email_confidence = 0
            recruiter.email_last_checked_at = received_at
            recruiter.email_source = f"Outlook NDR ({smtp_code})"[:100]
        elif event_type == "delivered" and recruiter.email_status != "valid":
            recruiter.email_status = "valid"
            recruiter.email_confidence = 100
            recruiter.email_last_checked_at = received_at
            recruiter.email_source = "Outlook Delivery Receipt"

    # 7. Update MailIntel DomainReputation (Direct ORM write, zero parquet rewrite delay)
    try:
        domain = email.split('@')[-1] if '@' in email else None
        if domain:
            from ..models.models import DomainReputation
            dr = db.get(DomainReputation, domain)
            if not dr:
                dr = DomainReputation(domain=domain, total_sent=0, total_delivered=0, total_bounced=0, total_replied=0)
                db.add(dr)
            if event_type in ['delivered', 'hard_bounce', 'soft_bounce']:
                dr.total_sent = (dr.total_sent or 0) + 1
            if event_type == 'delivered':
                dr.total_delivered = (dr.total_delivered or 0) + 1
            if event_type in ['hard_bounce', 'soft_bounce']:
                dr.total_bounced = (dr.total_bounced or 0) + 1
            dr.updated_at = datetime.now(timezone.utc)
            if dr.total_sent > 0:
                dr.reputation_score = (dr.total_delivered / dr.total_sent) * 100.0
    except Exception as e:
        logger.debug("MailIntel DomainReputation sync note: %s", e)

    db.commit()
    return log_rec


class OutlookFeedbackWatcher:
    """
    Background worker that connects to Outlook MAPI and monitors delivery feedback folders.
    """
    def __init__(self):
        self._running = False
        self._thread = None
        self.last_scan_time = None
        self.last_stats = {
            "processed": 0,
            "bounces": 0,
            "delivered": 0,
            "folders_checked": []
        }

    def scan_folders(
        self,
        folder_names: Optional[List[str]] = None,
        limit_per_folder: int = 150
    ) -> Dict[str, Any]:
        """
        Executes a folder scan across Outlook feedback folders.
        Thread-safe and non-destructive (read-only).
        """
        if folder_names is None:
            folder_names = ["Undilevered mail", "Psotmaster", "Inbox"]

        stats = {
            "scanned": 0,
            "new_events": 0,
            "bounces": 0,
            "delivered": 0,
            "folders": {}
        }

        with _outlook_feedback_lock:
            try:
                import pythoncom
                import win32com.client
            except ImportError:
                return {"error": "pywin32 not installed"}

            pythoncom.CoInitialize()
            try:
                outlook = win32com.client.Dispatch("Outlook.Application")
                ns = outlook.GetNamespace("MAPI")
                inbox = ns.GetDefaultFolder(6)  # 6 = olFolderInbox

                with SessionLocal() as db:
                    for fname in folder_names:
                        folder_obj = None
                        try:
                            if fname.lower() == "inbox":
                                folder_obj = inbox
                            else:
                                # Look for subfolder under Inbox
                                for j in range(1, inbox.Folders.Count + 1):
                                    f_candidate = inbox.Folders.Item(j)
                                    if f_candidate.Name.lower() == fname.lower():
                                        folder_obj = f_candidate
                                        break
                        except Exception as fe:
                            logger.debug("Folder find error for %s: %s", fname, fe)

                        if not folder_obj:
                            continue

                        stats["folders"][folder_obj.Name] = {"total_items": folder_obj.Items.Count, "processed": 0}
                        items = folder_obj.Items
                        items.Sort("[ReceivedTime]", True)

                        scan_count = min(items.Count, limit_per_folder)
                        for i in range(1, scan_count + 1):
                            stats["scanned"] += 1
                            try:
                                msg = items.Item(i)
                                events = parse_outlook_message(msg, folder_obj.Name)
                                for ev in events:
                                    rec = ingest_feedback_event(ev, db)
                                    if rec:
                                        stats["new_events"] += 1
                                        if ev["event_type"] in ("hard_bounce", "soft_bounce"):
                                            stats["bounces"] += 1
                                        elif ev["event_type"] == "delivered":
                                            stats["delivered"] += 1
                                        stats["folders"][folder_obj.Name]["processed"] += 1
                            except Exception as me:
                                logger.debug("Message scan note: %s", me)

                self.last_scan_time = datetime.now(timezone.utc).isoformat()
                self.last_stats = stats
                return stats

            except Exception as e:
                logger.error("Outlook feedback scan failed: %s", e)
                return {"error": str(e), "stats": stats}
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    def start_background_loop(self, interval_seconds: int = 60):
        """Starts continuous non-blocking background sentinel loop."""
        if self._running:
            return

        self._running = True

        def _loop():
            logger.info("OutlookFeedbackWatcher background sentinel started (every %ds)", interval_seconds)
            while self._running:
                try:
                    self.scan_folders(limit_per_folder=50)
                except Exception as e:
                    logger.debug("Background scan loop exception: %s", e)
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True, name="OutlookFeedbackSentinel")
        self._thread.start()

    def stop(self):
        self._running = False


# Singleton instance
outlook_feedback_watcher = OutlookFeedbackWatcher()
