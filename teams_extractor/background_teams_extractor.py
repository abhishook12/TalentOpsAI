"""
background_teams_extractor.py — Headless Autonomous Microsoft Teams Ingestion Engine.

Solves the user problem:
- 100% Background Execution: Runs purely via Windows UI Automation (UIA) directly against ms-teams.exe.
- ZERO Full-Screen Requirement: Does not require Teams to be full screen, focused, or visible. Works while minimized.
- ZERO Visual Screen Captures: No PrintWindow, no OCR, no coordinate clicking, no visual noise.
- Direct Ingestion: Ingests candidate contacts directly into Supabase PostgreSQL (discovery_staging table),
  feeding the main TalentOps AI database and live web UI.
- Fully Idempotent: Generates deterministic discovery_id per Teams message timestamp to prevent duplicate staging.
- Dual-Sync & Email Gate Compliant: Normalizes corporate entities and adheres to Corporate Email Intelligence Gate.
"""

import os
import sys
import time
import re
import json
import logging
import argparse
import ctypes
from typing import Dict, Any, List, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [TeamsUIA] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("talentops.teams_uia")

# Force stdout encoding to UTF-8 for Windows console emojis/symbols
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Attach to interactive desktop session to ensure Win32/UIA calls succeed from daemons
def attach_interactive_desktop():
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.debug(f"Desktop attachment notice: {e}")

attach_interactive_desktop()

import win32gui
from pywinauto import Application
from pywinauto.controls.uiawrapper import UIAWrapper

# Import database models
from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging

# Regex patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]??\(?\d{2,4}\)?[-.\s]??\d{2,4}[-.\s]??\d{3,9})')

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com',
    'gateway.net', 'sbcglobal.net', 'att.net', 'verizon.net'
}

COMPANY_SUFFIXES = [
    ' inc', ' llc', ' ltd', ' corp', ' corporation', ' consulting',
    ' staffing', ' solutions', ' group', ' technologies', ' technology',
    ' systems', ' partners', ' resources', ' health', ' hospital',
    ' services', ' firm', ' associates', ' capital', ' global', ' labs'
]

TITLE_KEYWORDS = [
    'developer', 'engineer', 'manager', 'director', 'partner', 'lead',
    'analyst', 'consultant', 'founder', 'ceo', 'coo', 'cto', 'officer',
    'specialist', 'recruiter', 'architect', 'administrator', 'coordinator',
    'scientist', 'executive', 'vice president', 'vp', 'head of'
]

NOISE_NAMES = {
    'link', 'sent', 'corporate', 'personal', 'mobile', 'unknown',
    'unread', 'message', 'group chat', 'today', 'yesterday', 'contact info'
}


def clean_phone_number(raw: str) -> Optional[str]:
    """Normalizes phone string into clean E.164 or US 10-digit format."""
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) >= 10:
        return f"+{digits}" if not raw.startswith('+') else f"+{digits}"
    return None


def infer_company_from_email_domain(domain: str) -> str:
    """Infers clean corporate company name from corporate email domain (Phase 1 Gate)."""
    if not domain or domain.lower() in FREE_EMAIL_DOMAINS:
        return ""
    root = domain.lower().split('.')[0]
    # Remove common corporate suffixes embedded in domain
    root = re.sub(r'-(inc|llc|tech|group|corp|consulting|solutions)$', '', root)
    words = re.split(r'[-_]', root)
    return " ".join(w.capitalize() for w in words)


class TeamsBackgroundExtractor:
    """
    Autonomous UI Automation extractor for Microsoft Teams.
    Extracts structured candidate cards in 100% background without screen coordinates.
    """

    def __init__(self, target_chat: str = "CTV- Phone numbers", owner_user_id: int = 1):
        self.target_chat = target_chat
        self.owner_user_id = owner_user_id
        self.app: Optional[Application] = None
        self.win: Optional[UIAWrapper] = None
        self.hwnd: Optional[int] = None

    def find_teams_window(self) -> Optional[int]:
        """Finds the Microsoft Teams window HWND matching the target group chat."""
        attach_interactive_desktop()
        found_hwnds = []

        def enum_cb(h, _):
            if win32gui.IsWindow(h):
                title = win32gui.GetWindowText(h)
                if "microsoft teams" in title.lower():
                    # Check if target chat is in title
                    if self.target_chat.lower() in title.lower():
                        found_hwnds.append((h, title, 2))  # Highest priority
                    elif "chat | " in title.lower():
                        found_hwnds.append((h, title, 1))  # Generic chat window
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.warning(f"EnumWindows error: {e}")

        if not found_hwnds:
            return None

        # Sort by priority
        found_hwnds.sort(key=lambda x: x[2], reverse=True)
        selected_hwnd, selected_title, _ = found_hwnds[0]
        logger.info(f"Target Teams window discovered: HWND {selected_hwnd} ('{selected_title}')")
        return selected_hwnd

    def connect(self) -> bool:
        """Connects to the Teams window via pywinauto UIA backend."""
        attach_interactive_desktop()
        self.hwnd = self.find_teams_window()
        if not self.hwnd:
            logger.warning("No Microsoft Teams window matching criteria found.")
            return False

        try:
            self.app = Application(backend="uia").connect(handle=self.hwnd)
            self.win = self.app.window(handle=self.hwnd)
            return True
        except Exception as e:
            logger.error(f"Failed to connect UIA to Teams window (HWND {self.hwnd}): {e}")
            return False

    def parse_message_element(self, msg_elem: UIAWrapper) -> Optional[Dict[str, Any]]:
        """Parses a single Teams UIA message element into structured candidate data."""
        mid = msg_elem.element_info.automation_id or ""
        header = msg_elem.element_info.name or ""

        # Find child content container
        tokens = []
        try:
            contents = [c for c in msg_elem.children() if (c.element_info.automation_id or "").startswith("content-")]
            if contents:
                for child in contents[0].children():
                    name = child.element_info.name
                    if name and name.strip():
                        tokens.append(name.strip())
        except Exception as e:
            logger.debug(f"Error reading child tokens for {mid}: {e}")

        # Extract sender from header
        sender = ""
        sender_match = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:Link\s+|Sent\s+|Corporate\s+)?', header)
        if sender_match:
            cand_sender = sender_match.group(1).strip()
            if cand_sender.lower() not in NOISE_NAMES:
                sender = cand_sender

        # Extract timestamp string if present
        timestamp_str = ""
        time_match = re.search(r'(?:Today|Yesterday|[A-Za-z]+)\s+at\s+\d{1,2}:\d{2}\s*(?:am|pm)?', header, re.IGNORECASE)
        if time_match:
            timestamp_str = time_match.group(0).strip()

        # Extract all emails and phone numbers from raw text
        raw_emails = list(dict.fromkeys(EMAIL_REGEX.findall(header)))
        raw_phones = PHONE_REGEX.findall(header)
        cleaned_phones = []
        for rp in raw_phones:
            cp = clean_phone_number(rp)
            if cp and cp not in cleaned_phones:
                cleaned_phones.append(cp)

        # Classify labeled tokens from content children
        corp_emails: List[str] = []
        personal_emails: List[str] = []
        corp_phones: List[str] = []
        mobile_phones: List[str] = []
        other_phones: List[str] = []
        linkedin_url: str = ""

        current_label = None
        for t in tokens:
            if "linkedin.com/in/" in t.lower() or "linkedin.com" in t.lower():
                linkedin_url = t.strip()
                continue

            if t in ['Corporate email', 'Personal email', 'Corporate phone', 'Mobile phone', 'Unknown phone']:
                current_label = t
                continue

            if current_label == 'Corporate email':
                if '@' in t and t not in corp_emails:
                    corp_emails.append(t)
            elif current_label == 'Personal email':
                if '@' in t and t not in personal_emails:
                    personal_emails.append(t)
            elif current_label == 'Corporate phone':
                cp = clean_phone_number(t)
                if cp and cp not in corp_phones:
                    corp_phones.append(cp)
            elif current_label == 'Mobile phone':
                cp = clean_phone_number(t)
                if cp and cp not in mobile_phones:
                    mobile_phones.append(cp)
            elif current_label == 'Unknown phone':
                cp = clean_phone_number(t)
                if cp and cp not in other_phones:
                    other_phones.append(cp)

        # ── Candidate Name Heuristics ──
        candidate_name = ""
        # 1. Look for 'Link <Name>'
        for t in tokens:
            if t.startswith('Link ') and '@' not in t and 'contact' not in t.lower() and 'linkedin' not in t.lower():
                cand = t.replace('Link ', '').strip()
                # Clean badges e.g. '· 3rd' or pronouns
                cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her|They/Them)\b', cand)[0].strip()
                if '·' in cand:
                    cand = cand.split('·')[0].strip()
                # Ensure it's a person's name, not a company
                is_company = any(sfx in cand.lower() for sfx in COMPANY_SUFFIXES)
                if not is_company and 1 < len(cand.split()) <= 4 and cand.lower() not in NOISE_NAMES:
                    candidate_name = cand
                    break

        # 2. First non-label token if no 'Link <Name>'
        if not candidate_name:
            for t in tokens:
                if t in ['Corporate email', 'Personal email', 'Corporate phone', 'Mobile phone', 'Unknown phone', '·', ':']:
                    continue
                if '@' in t or any(c.isdigit() for c in t):
                    continue
                if t.lower().startswith(('http', 'link', 'sent', 'unread')):
                    continue
                cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her)\b', t)[0].strip()
                is_company = any(sfx in cand.lower() for sfx in COMPANY_SUFFIXES)
                if not is_company and 1 < len(cand.split()) <= 4 and cand.lower() not in NOISE_NAMES:
                    candidate_name = cand
                    break

        # ── Title & Location Extraction ──
        title = ""
        location = ""
        for t in tokens:
            if any(kw in t.lower() for kw in TITLE_KEYWORDS):
                if not title and len(t) < 180 and not any(sfx in t.lower() for sfx in ['llc', 'inc', 'consulting']):
                    # Clean prefix actions
                    cleaned_t = re.sub(r'^(?:Link\s+|·\s*)+', '', t).strip()
                    title = cleaned_t
            if any(loc_w in t.lower() for loc_w in [' metropolitan area', ' united states', ', us', ' canada', ' area']):
                if not location:
                    location = t.strip()

        # ── Company Extraction ──
        company = ""
        for t in tokens:
            if t in [candidate_name, f"Link {candidate_name}", title, location]:
                continue
            if any(sfx in t.lower() for sfx in COMPANY_SUFFIXES):
                if not company and len(t) < 100 and '@' not in t:
                    company = re.sub(r'^(?:Link\s+|·\s*)+', '', t).strip()
                    break

        # ── Primary Email Selection (Gate Rule 5 Compliant) ──
        primary_email = ""
        if corp_emails:
            primary_email = corp_emails[0]
        else:
            # Check raw emails for corporate domain
            for em in raw_emails:
                domain = em.split('@')[-1].lower()
                if domain not in FREE_EMAIL_DOMAINS:
                    primary_email = em
                    break
            if not primary_email:
                if personal_emails:
                    primary_email = personal_emails[0]
                elif raw_emails:
                    primary_email = raw_emails[0]

        # Infer company from email domain if company was not found in tokens
        if not company and primary_email:
            domain = primary_email.split('@')[-1].lower()
            company = infer_company_from_email_domain(domain)

        # ── Primary Phone Selection ──
        primary_phone = ""
        if mobile_phones:
            primary_phone = mobile_phones[0]
        elif corp_phones:
            primary_phone = corp_phones[0]
        elif other_phones:
            primary_phone = other_phones[0]
        elif cleaned_phones:
            primary_phone = cleaned_phones[0]

        all_emails = list(dict.fromkeys(corp_emails + personal_emails + raw_emails))
        all_phones = list(dict.fromkeys(mobile_phones + corp_phones + other_phones + cleaned_phones))

        # Require at least name, email, or phone to consider it a candidate record
        if not candidate_name and not primary_email and not primary_phone:
            return None

        # Clean extraction ID
        clean_mid = mid.replace("message-body-", "")
        discovery_id = f"TEAMS-CTV-{clean_mid}"

        return {
            "message_id": mid,
            "discovery_id": discovery_id,
            "sender": sender,
            "timestamp": timestamp_str,
            "name": candidate_name or None,
            "title": title or None,
            "company": company or None,
            "location": location or None,
            "primary_email": primary_email or None,
            "primary_phone": primary_phone or None,
            "linkedin": linkedin_url or None,
            "all_emails": all_emails,
            "all_phones": all_phones,
            "raw_tokens": tokens,
            "raw_header": header
        }

    def harvest_messages(self) -> List[Dict[str, Any]]:
        """Traverses the UIA tree to extract all messages currently loaded in Teams DOM."""
        if not self.win:
            if not self.connect():
                return []

        try:
            msg_bodies = [
                d for d in self.win.descendants()
                if (d.element_info.automation_id or "").startswith("message-body-")
            ]
        except Exception as e:
            logger.warning(f"Error enumerating descendants, reconnecting: {e}")
            if self.connect():
                msg_bodies = [
                    d for d in self.win.descendants()
                    if (d.element_info.automation_id or "").startswith("message-body-")
                ]
            else:
                return []

        logger.info(f"Scanned {len(msg_bodies)} message elements in Teams UIA tree.")
        records = []
        for m in msg_bodies:
            parsed = self.parse_message_element(m)
            if parsed:
                records.append(parsed)

        return records

    def stage_records(self, records: List[Dict[str, Any]]) -> Tuple[int, int, int]:
        """
        Inserts extracted candidate records directly into Supabase PostgreSQL (discovery_staging).
        Returns: (inserted_count, skipped_count, error_count)
        """
        if not records:
            return (0, 0, 0)

        db = SessionLocal()
        inserted = 0
        skipped = 0
        errors = 0

        batch_id = f"TEAMS_{re.sub(r'[^A-Za-z0-9_]', '_', self.target_chat).upper()}"

        try:
            for rec in records:
                disc_id = rec["discovery_id"]
                # Check for existing discovery_id (Idempotency)
                existing = db.query(DiscoveryStaging.id).filter(DiscoveryStaging.discovery_id == disc_id).first()
                if existing:
                    skipped += 1
                    continue

                # Build rich metadata json
                metadata = {
                    "sender": rec["sender"],
                    "timestamp": rec["timestamp"],
                    "all_emails": rec["all_emails"],
                    "all_phones": rec["all_phones"],
                    "raw_tokens": rec["raw_tokens"],
                    "source_chat": self.target_chat,
                    "ingestion_agent": "teams_background_uia_worker"
                }

                staging_entry = DiscoveryStaging(
                    batch_id=batch_id,
                    discovery_id=disc_id,
                    session_id=f"teams_uia_{int(time.time())}",
                    device_id="TEAMS_UIA_DAEMON",
                    owner_user_id=self.owner_user_id,
                    raw_name=rec["name"],
                    raw_title=rec["title"],
                    raw_company=rec["company"],
                    raw_email=rec["primary_email"],
                    raw_phone=rec["primary_phone"],
                    raw_linkedin=rec["linkedin"],
                    raw_location=rec["location"],
                    source_url=f"msteams:/l/chat/{self.target_chat.replace(' ', '%20')}",
                    source_page_title=f"Microsoft Teams - {self.target_chat}",
                    extraction_source="teams_uia_background",
                    processing_status="pending",
                    metadata_json=json.dumps(metadata, ensure_ascii=False)
                )

                db.add(staging_entry)
                db.commit()
                inserted += 1
                logger.info(f"✅ Staged candidate: {rec['name']} | Company: {rec['company']} | Email: {rec['primary_email']} | Phone: {rec['primary_phone']} [ID: {disc_id}]")

        except Exception as e:
            logger.error(f"Database ingestion error: {e}")
            db.rollback()
            errors += 1
        finally:
            db.close()

        return (inserted, skipped, errors)

    def run_once(self) -> Dict[str, Any]:
        """Executes a single extraction and staging pass."""
        logger.info(f"Starting Teams Background Extractor pass for '{self.target_chat}'...")
        records = self.harvest_messages()
        inserted, skipped, errors = self.stage_records(records)
        summary = {
            "target_chat": self.target_chat,
            "total_scanned": len(records),
            "staged_new": inserted,
            "skipped_existing": skipped,
            "errors": errors,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"Extraction pass finished: {inserted} new staged, {skipped} skipped, {errors} errors.")
        return summary

    def run_continuous(self, interval_seconds: int = 30):
        """Runs the extractor perpetually in the background."""
        logger.info(f"🚀 Launching Perpetual Teams Background Extractor (polling every {interval_seconds}s)...")
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Teams Extractor stopped by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in perpetual loop: {e}")
            time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Headless Teams Background Ingestion Engine")
    parser.add_argument("--chat", type=str, default="CTV- Phone numbers", help="Target Teams chat name")
    parser.add_argument("--owner", type=int, default=1, help="Owner user ID for discovery_staging")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds for continuous mode")

    args = parser.parse_args()

    extractor = TeamsBackgroundExtractor(target_chat=args.chat, owner_user_id=args.owner)
    if args.once:
        summary = extractor.run_once()
        print(json.dumps(summary, indent=2))
    else:
        extractor.run_continuous(interval_seconds=args.interval)


if __name__ == "__main__":
    main()
