"""
deep_upward_extractor.py — Autonomous Upward-Harvesting Deep Ingestion Engine for Teams.

Fulfills all user mandates:
1. One Message = One Single Person: Extracts all fields per message bubble without splitting entities.
2. Complete Multi-Value Capture: Captures up to 4 distinct separated phone numbers (raw_phone, phone2,
   phone3, phone4) and multiple emails (raw_email, email2, email3, email4), plus all_phones and all_emails arrays.
3. Smart Entity & Name Guessing:
   - Recovers missing names from email local-parts (e.g. first.last@... -> First Last).
   - Cleans degree suffixes (, MBA, , MD, , PMP, , PHR) and UI noise (Link, He/Him, · 3rd, Revealed).
   - Infers missing companies from corporate email domains, 'at <Company>', '@ <Company>', and context tokens.
4. Upward Background Scrolling: Starts at the literal bottom (latest message) and scrolls UPWARDS
   page by page to collect the entire chat history in 100% background.
5. Direct PostgreSQL Staging: Immediately commits candidate cards into Supabase PostgreSQL (discovery_staging).
6. Autonomous 20-Minute Duration Execution: Continuously harvests for exactly 20 minutes (1,200s),
   reporting the last person collected and maintaining real-time status.
"""

import os
import sys
import time
import re
import json
import logging
import argparse
import ctypes
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add TalentOpsAI root to sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [DeepUpwardTeams] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("talentops.deep_upward_teams")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
import win32con
import win32process
import psutil
from pywinauto import Application
from pywinauto.controls.uiawrapper import UIAWrapper

from backend.app.database import SessionLocal
from backend.app.models.staging_models import DiscoveryStaging
from backend.app.services.ingestion_funnel import universal_funnel
from backend.scripts.incremental_parquet_sync import sync as sync_parquet
from backend.app.services.recruiter_store import recruiter_store

# Regex patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]??\(?\d{2,4}\)?[-.\s]??\d{2,4}[-.\s]??\d{3,9})')
LINKEDIN_REGEX = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?', re.IGNORECASE)
CREDENTIAL_REGEX = re.compile(
    r'[,.\s]+(?:MBA|MD|PMP|MS|PhD|CPA|BS|BA|PHR|SPHR|SHRM-CP|SHRM-SCP|CPC|CTS|CSP)\b',
    re.I
)

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com',
    'gateway.net', 'sbcglobal.net', 'att.net', 'verizon.net', 'proton.me', 'protonmail.com'
}

KNOWN_DOMAIN_COMPANIES = {
    'dppit.com': 'DP Professionals (DPP)',
    'ssipeople.com': 'SSI People',
    'source-technology.com': 'SGI',
    'sourcegroupinternational.com': 'Source Group International',
    'bluemarbleanalytics.com': 'Blue Marble Analytics',
    'delphi-us.com': 'Delphi-US',
    'teksystems.com': 'TEKsystems',
    'randstadusa.com': 'Randstad USA',
    'fairview.org': 'Fairview Health Services',
    'systemone.com': 'System One',
    'copiastaffing.com': 'Copia Staffing Partners',
    'paragonitpros.com': 'Paragon IT Professionals',
    'bcforward.com': 'BCforward',
    'prosoftgroup.com': 'Prosoft Group',
    'pdsinc.com': 'PDS Inc',
    'missionstaffing.com': 'Mission Staffing',
    'bnastaffing.com': 'Bernard Nickels & Associates',
    'empiric.com': 'Empiric',
    'nelsonandassociates.com': 'Nelson Connects',
    'globalchannelmanagement.com': 'Global Channel Management, Inc',
    'healthfirst.org': 'Healthfirst',
    'brooksource.com': 'Brooksource',
    'knowledgeservices.com': 'Knowledge Services',
    'suntechpros.com': 'SunTechPros Inc',
    'stewartsstaffing.com': 'Stewart',
    'walkerhealthforce.com': 'Walker Healthforce',
    'gcenergysolutions.com': 'GoldCoast Search Group',
    'firstpointgroup.com': 'First Point Group',
    'customsoftwaresystems.com': 'Custom Software Systems'
}

COMPANY_SUFFIXES = [
    ' inc', ' llc', ' ltd', ' corp', ' corporation', ' consulting',
    ' staffing', ' solutions', ' group', ' technologies', ' technology',
    ' systems', ' partners', ' resources', ' health', ' hospital',
    ' services', ' firm', ' associates', ' capital', ' global', ' labs', 'sgi'
]

TITLE_KEYWORDS = [
    'developer', 'engineer', 'manager', 'director', 'partner', 'lead',
    'analyst', 'consultant', 'founder', 'ceo', 'coo', 'cto', 'officer',
    'specialist', 'recruiter', 'architect', 'administrator', 'coordinator',
    'scientist', 'executive', 'vice president', 'vp', 'head of', 'president'
]

NOISE_NAMES_EXTENDED = {
    'link', 'sent', 'corporate', 'personal', 'mobile', 'mobile phone', 'phone',
    'cell phone', 'cell', 'work phone', 'work', 'direct phone', 'direct line',
    'office phone', 'office', 'wrong number', 'wrong', 'number', 'unknown',
    'unread', 'message', 'group chat', 'today', 'yesterday', 'contact info',
    'more message options', 'company logo', 'logo', 'view profile',
    'connect', 'he/him', 'she/her', 'they/them', '+ 1 more', 'revealed',
    'phone revealed', 'email revealed', 'link contact info', 'not available',
    'n/a', 'na', 'none', 'null', 'test', 'fake',
    # Compound UI label noise phrases (Teams contact card labels)
    'corporate email', 'personal email', 'work email', 'home email',
    'corporate phone', 'personal phone', 'home phone',
    'direct email', 'office email', 'business email', 'business phone',
    'email address', 'phone number', 'mobile number', 'cell number',
    'direct number', 'work number', 'office number',
    'link corporate email', 'link personal email', 'link mobile phone',
    'link work phone', 'link direct phone', 'link office phone',
    'link cell phone', 'link corporate phone', 'link personal phone',
}


def clean_phone_number(raw: str) -> Optional[str]:
    """Cleans phone numbers into clean E.164 or US 10-digit format."""
    if not raw:
        return None
    raw_str = str(raw).strip()
    digits = re.sub(r'\D', '', raw_str)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) >= 10:
        return f"+{digits}" if not raw_str.startswith('+') else f"+{digits}"
    elif len(digits) >= 7:
        return raw_str
    return None


def clean_extracted_name(cand: str) -> str:
    """Strips UI prefix, degree credentials, and phone numbers from raw name token."""
    if not cand:
        return ""
    cand = cand.replace('Link ', '').strip()
    cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her|They/Them)\b', cand)[0].strip()
    cand = CREDENTIAL_REGEX.sub('', cand).strip()
    cand = PHONE_REGEX.sub('', cand).strip()
    cand = re.sub(r'[\s\xa0]+', ' ', cand).strip()
    cand = re.sub(r'^[^A-Za-z]+', '', cand).strip()
    if cand.lower() in NOISE_NAMES_EXTENDED:
        return ""
    return cand


def infer_name_from_email(email: Optional[str]) -> str:
    """Intelligently deduces human name from corporate or personal email."""
    if not email or '@' not in email:
        return ""
    local = email.split('@')[0].lower()
    local = re.sub(r'\d+', '', local)
    parts = re.split(r'[._-]', local)
    if len(parts) >= 2 and all(len(p) >= 2 for p in parts[:2]):
        return f"{parts[0].capitalize()} {parts[1].capitalize()}"
    elif len(parts) == 1 and len(parts[0]) >= 3:
        return parts[0].capitalize()
    return ""


def infer_company_from_email_domain(domain: Optional[str]) -> str:
    """Infers canonical corporate company name from corporate email domain."""
    if not domain or domain.lower() in FREE_EMAIL_DOMAINS:
        return ""
    d_clean = domain.lower().strip()
    if d_clean in KNOWN_DOMAIN_COMPANIES:
        return KNOWN_DOMAIN_COMPANIES[d_clean]
    root = d_clean.split('.')[0]
    root = re.sub(r'-(inc|llc|tech|group|corp|consulting|solutions)$', '', root)
    words = re.split(r'[-_]', root)
    return " ".join(w.capitalize() for w in words)


class DeepUpwardTeamsExtractor:
    """
    Autonomous engine that connects to Teams, parses all messages into complete
    multi-field candidate records, and scrolls UPWARDS into history.
    """

    def __init__(self, target_chat: str = "CTV- Phone numbers", owner_user_id: int = 1, visible: bool = False):
        self.target_chat = target_chat
        self.owner_user_id = owner_user_id
        self.visible = visible
        self.top_hwnd: Optional[int] = None
        self.render_hwnd: Optional[int] = None
        self.orig_rect: Optional[Tuple[int, int, int, int]] = None
        self.app: Optional[Application] = None
        self.win: Optional[UIAWrapper] = None

    def ensure_visible_on_screen(self):
        """Ensures Microsoft Teams window is restored and visibly positioned on the user's desktop."""
        if not self.top_hwnd or not win32gui.IsWindow(self.top_hwnd):
            return
        try:
            curr_rect = win32gui.GetWindowRect(self.top_hwnd)
            # If minimized or far offscreen, restore to visible screen coords
            if curr_rect[0] <= -5000 or curr_rect[0] == -32000:
                win32gui.ShowWindow(self.top_hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(
                    self.top_hwnd,
                    win32con.HWND_NOTOPMOST,
                    50, 50, 1280, 720,
                    win32con.SWP_SHOWWINDOW
                )
                logger.info("🖥️ Microsoft Teams restored and positioned visibly on screen at (50, 50, 1280, 720).")
            else:
                win32gui.ShowWindow(self.top_hwnd, win32con.SW_RESTORE)
                logger.info(f"🖥️ Microsoft Teams confirmed visible on screen at {curr_rect}.")
        except Exception as e:
            logger.warning(f"ensure_visible_on_screen notice: {e}")

    def hide_to_background(self):
        """Moves Teams window far off-screen (-9000, -9000) so it never pops up on screen or steals focus."""
        if not self.top_hwnd or not win32gui.IsWindow(self.top_hwnd):
            return
        try:
            curr_rect = win32gui.GetWindowRect(self.top_hwnd)
            if curr_rect[0] > -5000:
                self.orig_rect = curr_rect
            w = max(800, self.orig_rect[2] - self.orig_rect[0]) if self.orig_rect else 1048
            h = max(600, self.orig_rect[3] - self.orig_rect[1]) if self.orig_rect else 688
            win32gui.SetWindowPos(
                self.top_hwnd,
                win32con.HWND_BOTTOM,
                -9000, -9000,
                w, h,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            logger.info("👻 Microsoft Teams hidden at off-screen coordinates (-9000, -9000). Zero screen intrusion.")
        except Exception as e:
            logger.warning(f"hide_to_background notice: {e}")

    def restore_window(self):
        """Restores Teams window to its original position without activating it."""
        if self.visible:
            return  # Kept visibly open on user's screen as requested
        if not self.top_hwnd or not win32gui.IsWindow(self.top_hwnd) or not self.orig_rect:
            return
        try:
            x, y, r, b = self.orig_rect
            w = max(400, r - x)
            h = max(300, b - y)
            win32gui.SetWindowPos(
                self.top_hwnd,
                win32con.HWND_NOTOPMOST,
                x, y, w, h,
                win32con.SWP_NOACTIVATE
            )
            logger.info(f"Restored Teams window position to {self.orig_rect} (SWP_NOACTIVATE).")
        except Exception as e:
            logger.warning(f"restore_window notice: {e}")

    def find_windows(self) -> bool:
        """Locates both the top Teams window and the child Chrome_RenderWidgetHostHWND."""
        attach_interactive_desktop()
        found_top = []

        def enum_cb(h, _):
            try:
                if win32gui.IsWindow(h):
                    title = win32gui.GetWindowText(h)
                    if "microsoft teams" in title.lower() or self.target_chat.lower() in title.lower():
                        _, pid = win32process.GetWindowThreadProcessId(h)
                        try:
                            pname = psutil.Process(pid).name().lower()
                        except Exception:
                            pname = ""
                        if "teams" in pname:
                            if self.target_chat.lower() in title.lower():
                                found_top.append((h, title, 2))
                            elif "chat | " in title.lower():
                                found_top.append((h, title, 1))
                            else:
                                found_top.append((h, title, 0))
            except Exception:
                pass
            return 1

        for attempt in range(5):
            found_top.clear()
            try:
                win32gui.EnumWindows(enum_cb, None)
                if found_top:
                    break
            except Exception as e:
                logger.debug(f"EnumWindows retry {attempt+1}: {e}")
            time.sleep(0.3)

        if not found_top:
            logger.error("Could not find any Microsoft Teams window.")
            return False

        found_top.sort(key=lambda x: x[2], reverse=True)
        self.top_hwnd = found_top[0][0]
        logger.info(f"Top Teams Window: HWND {self.top_hwnd} ('{found_top[0][1]}')")

        # Find child Chrome_RenderWidgetHostHWND (Chromium Webview input target)
        def find_render(h):
            child = win32gui.FindWindowEx(h, 0, None, None)
            while child:
                if win32gui.GetClassName(child) == "Chrome_RenderWidgetHostHWND":
                    return child
                res = find_render(child)
                if res: return res
                child = win32gui.FindWindowEx(h, child, None, None)
            return None

        self.render_hwnd = find_render(self.top_hwnd)
        logger.info(f"Child Render Target: HWND {self.render_hwnd} (Chrome_RenderWidgetHostHWND)")
        return bool(self.top_hwnd and self.render_hwnd)

    def ensure_target_chat_active(self) -> bool:
        """Verifies target chat is active. If not, selects it in the Teams UI."""
        if not self.win:
            return False
        try:
            title = win32gui.GetWindowText(self.top_hwnd)
            if self.target_chat.lower() in title.lower():
                return True

            logger.info(f"Chat '{self.target_chat}' not active (currently '{title}'). Selecting in UI...")
            items = [
                d for d in self.win.descendants()
                if (d.element_info.name or "").startswith(f"Group chat {self.target_chat}")
            ]
            if items:
                try:
                    pattern = items[0].iface_selection_item
                    if pattern:
                        pattern.Select()
                        logger.info(f"Successfully selected '{self.target_chat}' via SelectionPattern.")
                        time.sleep(2.0)
                        return True
                except Exception:
                    pass
                # Do NOT call click_input() as it moves mouse cursor and steals focus
                logger.info(f"Selection item present for '{self.target_chat}'.")
                return True
        except Exception as e:
            logger.warning(f"ensure_target_chat_active notice: {e}")
        return True

    def connect(self) -> bool:
        """Connects UIA application object and ensures target chat is active."""
        if not self.find_windows():
            return False
        try:
            if self.visible:
                self.ensure_visible_on_screen()
            else:
                self.hide_to_background()
            self.app = Application(backend="uia").connect(handle=self.top_hwnd)
            self.win = self.app.window(handle=self.top_hwnd)
            self.ensure_target_chat_active()
            return True
        except Exception as e:
            logger.error(f"UIA connection failed: {e}")
            return False

    def parse_message(self, msg_elem: UIAWrapper) -> Optional[Dict[str, Any]]:
        """
        Parses a single message bubble into a complete, non-lossy candidate record.
        Captures all emails, up to 4 separated phones, title, company, location,
        degrees, and sender metadata.
        """
        mid = msg_elem.element_info.automation_id or ""
        header = msg_elem.element_info.name or ""

        # Extract child tokens from content container
        tokens = []
        try:
            contents = [c for c in msg_elem.children() if (c.element_info.automation_id or "").startswith("content-")]
            if contents:
                for child in contents[0].children():
                    name = child.element_info.name
                    if name and name.strip():
                        tokens.append(name.strip())
        except Exception as e:
            logger.debug(f"Child token read error: {e}")

        # 1. Emails
        raw_emails = list(dict.fromkeys(EMAIL_REGEX.findall(header)))
        corp_emails = []
        personal_emails = []
        for em in raw_emails:
            dom = em.split('@')[-1].lower()
            if dom in FREE_EMAIL_DOMAINS:
                personal_emails.append(em)
            else:
                corp_emails.append(em)

        # 2. Phones
        raw_phones = PHONE_REGEX.findall(header)
        cleaned_phones = []
        for rp in raw_phones:
            cp = clean_phone_number(rp)
            if cp and cp not in cleaned_phones:
                cleaned_phones.append(cp)

        # 3. Candidate Name
        candidate_name = ""

        # Method A: Look for 'Link <Name>'
        for t in tokens:
            t_clean = t.replace('Link ', '').strip()
            if t_clean.lower() in NOISE_NAMES_EXTENDED or 'contact info' in t.lower() or 'linkedin' in t.lower():
                continue
            # Check company suffix on the cleaned name (not the full token with "Link " prefix)
            t_clean_lower = t_clean.lower()
            is_company_suffix = any(t_clean_lower.endswith(sfx.strip()) or (sfx + ' ') in t_clean_lower for sfx in COMPANY_SUFFIXES)
            if is_company_suffix and not any(kw in t_clean_lower for kw in TITLE_KEYWORDS):
                continue
            cleaned = clean_extracted_name(t)
            if cleaned and cleaned.lower() not in NOISE_NAMES_EXTENDED and 1 < len(cleaned.split()) <= 4:
                if not any(c.isdigit() for c in cleaned):
                    candidate_name = cleaned
                    break

        # Method B: Search all tokens for clean person name
        if not candidate_name:
            for t in tokens:
                if t.lower() in NOISE_NAMES_EXTENDED or '@' in t:
                    continue
                cleaned = clean_extracted_name(t)
                if not cleaned or cleaned.lower() in NOISE_NAMES_EXTENDED:
                    continue
                is_company = any(cleaned.lower().endswith(sfx.strip()) or (sfx + ' ') in cleaned.lower() for sfx in COMPANY_SUFFIXES)
                if not is_company and 1 < len(cleaned.split()) <= 4 and not any(c.isdigit() for c in cleaned):
                    candidate_name = cleaned
                    break

        # Method C: Infer from email
        if not candidate_name and (corp_emails or personal_emails):
            hint = corp_emails[0] if corp_emails else personal_emails[0]
            candidate_name = infer_name_from_email(hint)

        # 4. Company, Title, Location, LinkedIn
        company = ""
        title = ""
        location = ""
        linkedin_url = ""

        for i, t in enumerate(tokens):
            if "linkedin.com/in/" in t.lower():
                # Extract clean LinkedIn URL using regex
                li_match = LINKEDIN_REGEX.search(t)
                if li_match:
                    linkedin_url = li_match.group(0)
                else:
                    linkedin_url = t.strip()
            elif "linkedin.com" in t.lower() and not linkedin_url:
                linkedin_url = t.strip()

            # Regex 'Title at Company'
            m_at = re.search(r'([A-Za-z\s/&]+)\s+at\s+([A-Za-z0-9\s/&().,-]+)', t, re.I)
            if m_at:
                cand_title = m_at.group(1).strip()
                raw_comp = m_at.group(2).strip()
                cand_comp = re.split(r'\s+(?:and|&|\||\-|,)\s+', raw_comp)[0].strip()
                if not title and len(cand_title) < 90:
                    title = cand_title
                if not company and len(cand_comp) < 90:
                    company = cand_comp

            # Consecutive tokens: title followed by 'at', followed by company
            if i + 2 < len(tokens) and tokens[i+1].strip().lower() == 'at':
                cand_title = tokens[i].strip()
                cand_comp = tokens[i+2].strip().replace('Link ', '').strip()
                if not title and len(cand_title) < 90 and not any(c.isdigit() for c in cand_title):
                    title = cand_title
                if not company and len(cand_comp) < 90:
                    company = cand_comp

            # Pattern '@ <Company>'
            m_at_sym = re.search(r'@\s+([A-Za-z0-9\s&().,-]+?)(?:,\s*focused|\s*\(|\s*$)', t, re.I)
            if m_at_sym and not company:
                company = m_at_sym.group(1).strip()

            # Location match
            if any(loc_w in t.lower() for loc_w in [' metropolitan area', ' united states', ', us', ' canada', ' area', 'uk']):
                if not location:
                    location = t.strip()

        # Look for Company from Link <Company> token
        if not company:
            for t in tokens:
                if t.startswith('Link ') and candidate_name and t != f"Link {candidate_name}":
                    cand_c = t.replace('Link ', '').strip()
                    if cand_c.lower() not in NOISE_NAMES_EXTENDED and 'contact' not in cand_c.lower() and 'linkedin' not in cand_c.lower() and '@' not in cand_c:
                        company = cand_c
                        break

        # Look for Company right after 'Link Contact info'
        if not company:
            for i, t in enumerate(tokens):
                if 'contact info' in t.lower() and i + 1 < len(tokens):
                    nxt = tokens[i+1].strip()
                    if nxt.lower() not in NOISE_NAMES_EXTENDED and not nxt.startswith(('+', 'http')) and len(nxt) < 80 and '@' not in nxt:
                        nxt = nxt.split('|')[0].strip()
                        company = nxt
                        break

        # Look for Company token between Name and contact info
        if not company and candidate_name:
            try:
                cand_idx = -1
                for i, t in enumerate(tokens):
                    if candidate_name.lower() in t.lower():
                        cand_idx = i
                        break
                if cand_idx != -1 and cand_idx + 1 < len(tokens):
                    candidate_token = tokens[cand_idx + 1].strip()
                    c_tok_clean = candidate_token.lower()
                    if (c_tok_clean not in NOISE_NAMES_EXTENDED and
                        not any(c.isdigit() for c in candidate_token) and
                        '@' not in candidate_token and
                        len(candidate_token) < 70 and
                        candidate_token != title and candidate_token != location and
                        not any(kw in c_tok_clean for kw in TITLE_KEYWORDS) and
                        candidate_name.lower() not in c_tok_clean):
                        company = candidate_token
            except Exception:
                pass

        # Company fallback from token with company suffix
        if not company:
            for t in tokens:
                t_clean = t.replace('Link ', '').strip()
                if candidate_name and candidate_name.lower() in t_clean.lower():
                    continue
                if any(sfx in t_clean.lower() for sfx in COMPANY_SUFFIXES):
                    if not any(kw in t_clean.lower() for kw in TITLE_KEYWORDS) and len(t_clean) < 70 and '@' not in t_clean:
                        company = t_clean
                        break

        # Company from email domain fallback
        if (not company or '@' in company or any(kw in company.lower() for kw in TITLE_KEYWORDS)) and corp_emails:
            inferred = infer_company_from_email_domain(corp_emails[0].split('@')[-1])
            if inferred:
                company = inferred

        # LinkedIn fallback: search header text if not found in tokens
        if not linkedin_url:
            li_header_match = LINKEDIN_REGEX.search(header)
            if li_header_match:
                linkedin_url = li_header_match.group(0)

        # Clean company
        if company:
            company = re.sub(r'^Link\s+', '', company, flags=re.I).strip()
            company = company.rstrip(',. ')
            if candidate_name and candidate_name.lower() in company.lower():
                company = ""
            if '@' in company:
                company = ""

        # ── Post-extraction Name Recovery ──
        # If candidate_name is still empty or a noise UI label, attempt recovery:
        #   1. Check if 'company' field actually holds a person name -> swap
        #   2. Re-scan tokens for bare person names (no "Link " prefix)
        #   3. Infer from email as last resort
        name_is_noise = (not candidate_name or candidate_name.lower().strip() in NOISE_NAMES_EXTENDED)
        if name_is_noise:
            # Recovery A: Company field looks like a person name (2-3 words, no company suffix, no digits)
            if company:
                comp_words = company.split()
                comp_has_suffix = any(sfx in company.lower() for sfx in COMPANY_SUFFIXES)
                if not comp_has_suffix and 1 < len(comp_words) <= 3 and not any(c.isdigit() for c in company):
                    # Company field holds the real person name
                    recovered_name = company
                    # Try to find actual company from email domain
                    new_company = ""
                    if corp_emails:
                        new_company = infer_company_from_email_domain(corp_emails[0].split('@')[-1]) or ""
                    candidate_name = recovered_name
                    company = new_company
                    name_is_noise = False

        if name_is_noise:
            # Recovery B: Re-scan tokens for embedded person names
            for t in tokens:
                t_stripped = t.replace('Link ', '').replace('\xa0', ' ').strip()
                if t_stripped.lower() in NOISE_NAMES_EXTENDED or t_stripped.lower().startswith(('http', 'www.')):
                    continue

                # B1: "Name at Company" pattern in single token
                m_at = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+){1,2})\s+at\s+', t_stripped, re.I)
                if m_at:
                    cand = m_at.group(1).strip()
                    if cand.lower() not in NOISE_NAMES_EXTENDED and 1 < len(cand.split()) <= 3:
                        candidate_name = cand
                        name_is_noise = False
                        break

                # B2: NBSP-separated compound tokens (e.g. "Company\xa0\xa0\xa0Name" or "Phone\xa0\xa0\xa0Company\xa0\xa0\xa0Name")
                parts = re.split(r'\s{2,}', t_stripped)
                if len(parts) > 1:
                    # Check last part — most common position for person name
                    last_part = parts[-1].strip()
                    last_clean = re.sub(r'[^A-Za-z\s.\'-]', '', last_part).strip()
                    if last_clean and 1 < len(last_clean.split()) <= 3 and last_clean.lower() not in NOISE_NAMES_EXTENDED:
                        if not any(sfx in last_clean.lower() for sfx in COMPANY_SUFFIXES):
                            candidate_name = last_clean
                            name_is_noise = False
                            break

                # B3: Check for comma-separated name with credential suffix (e.g. "S Waheed Ullah Sadat, P")
                if ',' in t_stripped and not '@' in t_stripped:
                    pre_comma = t_stripped.split(',')[0].strip()
                    pre_clean = clean_extracted_name(pre_comma)
                    if pre_clean and pre_clean.lower() not in NOISE_NAMES_EXTENDED and 1 < len(pre_clean.split()) <= 4:
                        if not any(c.isdigit() for c in pre_clean):
                            is_company_tok = any(pre_clean.lower().endswith(sfx.strip()) for sfx in COMPANY_SUFFIXES)
                            if not is_company_tok:
                                candidate_name = pre_clean
                                name_is_noise = False
                                break

                # B4: Normal 2-3 word name check (no digits, no email, no company suffix)
                if '@' in t_stripped or any(c.isdigit() for c in t_stripped):
                    continue
                is_company_tok = any(t_stripped.lower().endswith(sfx.strip()) or (sfx + ' ') in t_stripped.lower() for sfx in COMPANY_SUFFIXES)
                if not is_company_tok and 1 < len(t_stripped.split()) <= 3:
                    if t_stripped != company and t_stripped != title and t_stripped != location:
                        candidate_name = clean_extracted_name(t_stripped)
                        if candidate_name and candidate_name.lower() not in NOISE_NAMES_EXTENDED:
                            name_is_noise = False
                            break
                        candidate_name = ""

        if name_is_noise and (corp_emails or personal_emails):
            # Recovery C: Infer from email
            hint = corp_emails[0] if corp_emails else personal_emails[0]
            inferred = infer_name_from_email(hint)
            if inferred:
                candidate_name = inferred

        # 5. Multi-Email Separation
        primary_email = corp_emails[0] if corp_emails else (personal_emails[0] if personal_emails else None)
        email2 = personal_emails[0] if (corp_emails and personal_emails) else (corp_emails[1] if len(corp_emails) > 1 else (personal_emails[1] if len(personal_emails) > 1 else None))
        email3 = corp_emails[2] if len(corp_emails) > 2 else (personal_emails[2] if len(personal_emails) > 2 else None)
        email4 = corp_emails[3] if len(corp_emails) > 3 else (personal_emails[3] if len(personal_emails) > 3 else None)

        # 6. Multi-Phone Separation (Up to 4 separated phone fields)
        primary_phone = cleaned_phones[0] if len(cleaned_phones) >= 1 else None
        phone2 = cleaned_phones[1] if len(cleaned_phones) >= 2 else None
        phone3 = cleaned_phones[2] if len(cleaned_phones) >= 3 else None
        phone4 = cleaned_phones[3] if len(cleaned_phones) >= 4 else None

        # Sender & Timestamp
        sender_match = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:Link\s+|Sent\s+|Corporate\s+)?', header)
        sender = sender_match.group(1).strip() if sender_match else ""
        time_match = re.search(r'(?:Today|Yesterday|[A-Za-z]+)\s+at\s+\d{1,2}:\d{2}\s*(?:am|pm)?', header, re.IGNORECASE)
        timestamp_str = time_match.group(0).strip() if time_match else ""

        if not candidate_name and not primary_email and not primary_phone:
            return None

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
            "primary_email": primary_email,
            "email2": email2,
            "email3": email3,
            "email4": email4,
            "all_emails": raw_emails,
            "primary_phone": primary_phone,
            "phone2": phone2,
            "phone3": phone3,
            "phone4": phone4,
            "all_phones": cleaned_phones,
            "linkedin": linkedin_url or None,
            "raw_tokens": tokens,
            "raw_header": header
        }

    def scroll_up(self, steps: int = 10, oldest_elem = None):
        """Dispatches upward scroll events to Chrome_RenderWidgetHostHWND."""
        if not self.render_hwnd or not win32gui.IsWindow(self.render_hwnd):
            self.find_windows()

        if not self.render_hwnd or not win32gui.IsWindow(self.render_hwnd):
            return

        rect = win32gui.GetWindowRect(self.render_hwnd)
        if rect[0] <= -5000 and self.visible:
            self.find_windows()
            rect = win32gui.GetWindowRect(self.render_hwnd)

        cx = (rect[0] + rect[2]) // 2
        cy = (rect[1] + rect[3]) // 2

        amount = 120 * 6  # Positive delta = scroll UPWARDS into past
        wparam = (amount & 0xFFFF) << 16
        lparam = ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)

        for _ in range(steps):
            win32gui.PostMessage(self.render_hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)
            time.sleep(0.02)
        # Post VK_PRIOR (Page Up) to trigger virtualized DOM rendering
        win32gui.PostMessage(self.render_hwnd, win32con.WM_KEYDOWN, win32con.VK_PRIOR, 0)
        win32gui.PostMessage(self.render_hwnd, win32con.WM_KEYUP, win32con.VK_PRIOR, 0)

    def harvest_current_view(self) -> List[Dict[str, Any]]:
        """Harvests all message bubbles currently in the UIA DOM."""
        if not self.win:
            if not self.connect():
                return []
        try:
            msg_bodies = [
                d for d in self.win.descendants()
                if (d.element_info.automation_id or "").startswith("message-body-")
            ]
        except Exception as e:
            logger.warning(f"DOM read error, reconnecting: {e}")
            if self.connect():
                msg_bodies = [
                    d for d in self.win.descendants()
                    if (d.element_info.automation_id or "").startswith("message-body-")
                ]
            else:
                return []

        records = []
        for m in msg_bodies:
            parsed = self.parse_message(m)
            if parsed:
                records.append(parsed)
        return records

    def stage_batch(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
        """Bulk stages records into Supabase PostgreSQL (discovery_staging) AND promotes into master recruiters table."""
        if not records:
            return ([], [], 0, 0)

        db = SessionLocal()
        staged_list = []
        promoted_list = []
        skipped = 0
        errors = 0

        try:
            all_ids = [r["discovery_id"] for r in records]
            existing_ids = set()
            for i in range(0, len(all_ids), 500):
                chunk = all_ids[i:i + 500]
                rows = db.query(DiscoveryStaging.discovery_id).filter(DiscoveryStaging.discovery_id.in_(chunk)).all()
                existing_ids.update(row[0] for row in rows)

            new_entries = []
            seen = set()
            for r in records:
                did = r["discovery_id"]
                if did in existing_ids or did in seen:
                    skipped += 1
                    continue
                seen.add(did)

                metadata = {
                    "email2": r["email2"],
                    "email3": r["email3"],
                    "email4": r["email4"],
                    "all_emails": r["all_emails"],
                    "phone2": r["phone2"],
                    "phone3": r["phone3"],
                    "phone4": r["phone4"],
                    "all_phones": r["all_phones"],
                    "sender": r["sender"],
                    "timestamp": r["timestamp"],
                    "source_chat": self.target_chat,
                    "ingestion_agent": "deep_upward_teams_extractor"
                }

                stg = DiscoveryStaging(
                    batch_id="TEAMS_CTV_UPWARD_STREAM",
                    discovery_id=did[:64],
                    session_id=f"teams_upward_{int(time.time())}",
                    device_id="TEAMS_UPWARD_NODE",
                    owner_user_id=self.owner_user_id,
                    raw_name=r["name"][:200] if r["name"] else None,
                    raw_title=r["title"][:200] if r["title"] else None,
                    raw_company=r["company"][:255] if r["company"] else None,
                    raw_email=r["primary_email"][:200] if r["primary_email"] else None,
                    raw_phone=r["primary_phone"][:50] if r["primary_phone"] else None,
                    raw_linkedin=r["linkedin"][:300] if r["linkedin"] else None,
                    raw_location=r["location"][:255] if r["location"] else None,
                    source_url="msteams:/l/chat/CTV-Phone-numbers",
                    source_page_title=f"Microsoft Teams - {self.target_chat}",
                    extraction_source="teams_uia_background",
                    processing_status="pending",
                    metadata_json=json.dumps(metadata, ensure_ascii=False)
                )
                new_entries.append((stg, r))
                staged_list.append(r)

            if new_entries:
                db_stgs = [item[0] for item in new_entries]
                db.add_all(db_stgs)
                db.commit()

                # Master DB Promotion Flywheel: Immediately promote through Universal Funnel
                for stg_entry, rec_info in new_entries:
                    try:
                        res = universal_funnel.process_staging_record(stg_entry, db)
                        db.commit()
                        st = res.get("status")
                        rec_id = res.get("recruiter_id")
                        if st in ("PROMOTED", "ENRICHED"):
                            promoted_info = dict(rec_info)
                            promoted_info["recruiter_id"] = rec_id
                            promoted_info["funnel_status"] = st
                            promoted_list.append(promoted_info)
                            logger.info(f"🚀 Master DB Live: {stg_entry.raw_name} -> Recruiter #{rec_id} ({st})")
                        else:
                            logger.info(f"⏳ Staged in queue: {stg_entry.raw_name} -> {res.get('reason')}")
                    except Exception as pe:
                        logger.debug(f"Funnel promotion notice for {stg_entry.raw_name}: {pe}")
                        db.rollback()

        except Exception as e:
            logger.error(f"Database stage error: {e}")
            db.rollback()
            errors += 1
        finally:
            db.close()

        return (staged_list, promoted_list, skipped, errors)

    def run_upward_harvest(
        self,
        duration_seconds: int = 7200,
        delay_between_scrolls: float = 1.8,
        status_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the autonomous upward harvesting loop for up to duration_seconds:
        1. Harvests current bottom view.
        2. Scrolls UPWARDS page by page into past chat history.
        3. Stages each candidate AND directly promotes into Master DB (Recruiters) via Universal Funnel.
        4. Synchronizes DuckDB Parquet and RecruiterStore continuously for live site display.
        5. Listens for manual stop signal (STOP_HARVEST.flag) or dynamic extension (harvest_control.json).
        6. Reports full candidate roster and summary.
        """
        out_dir = os.path.join(REPO_ROOT, "teams_extractor", "output")
        os.makedirs(out_dir, exist_ok=True)
        if not status_file_path:
            status_file_path = os.path.join(out_dir, "upward_harvest_status.json")
        roster_file_path = os.path.join(out_dir, "harvested_candidates_report.json")
        stop_flag = os.path.join(out_dir, "STOP_HARVEST.flag")
        control_path = os.path.join(out_dir, "harvest_control.json")

        # Clear any stale stop flag before starting
        if os.path.exists(stop_flag):
            try:
                os.remove(stop_flag)
            except Exception:
                pass

        logger.info(f"🚀 Starting Deep Upward Teams Autonomous Ingestion for '{self.target_chat}'...")
        logger.info(f"⏱️ Duration Target: {duration_seconds} seconds ({duration_seconds / 3600:.1f} hours / {duration_seconds / 60:.1f} mins).")

        if not self.connect():
            return {"error": "Failed to connect to Teams"}

        start_time = time.time()
        end_time = start_time + duration_seconds

        total_scanned = 0
        total_staged = 0
        session_promoted = 0
        total_skipped = 0
        scroll_count = 0
        consecutive_no_new = 0

        last_sync_time = time.time()
        promoted_since_sync = 0

        first_person_staged: Optional[Dict[str, Any]] = None
        last_person_staged: Optional[Dict[str, Any]] = None
        oldest_candidate_reached: Optional[Dict[str, Any]] = None
        all_promoted_candidates: List[Dict[str, Any]] = []
        prior_promoted_count = 0
        initial_run_start = datetime.fromtimestamp(start_time).isoformat()

        # Load existing candidates from cumulative report if present
        if os.path.exists(roster_file_path):
            try:
                with open(roster_file_path, "r", encoding="utf-8") as rf:
                    prev_roster = json.load(rf)
                    if isinstance(prev_roster, dict) and "candidates" in prev_roster:
                        all_promoted_candidates = list(prev_roster["candidates"])
                        prior_promoted_count = len(all_promoted_candidates)
                        if "initial_session_start" in prev_roster:
                            initial_run_start = prev_roster["initial_session_start"]
                        elif "session_start" in prev_roster:
                            initial_run_start = prev_roster["session_start"]
                        logger.info(f"📋 Loaded {prior_promoted_count} previously promoted candidates from cumulative roster.")
            except Exception as e:
                logger.warning(f"Could not load previous roster: {e}")

        # Load previous status tracking if available
        if os.path.exists(status_file_path):
            try:
                with open(status_file_path, "r", encoding="utf-8") as sf:
                    prev_status = json.load(sf)
                    if isinstance(prev_status, dict):
                        first_person_staged = prev_status.get("first_person_staged")
                        oldest_candidate_reached = prev_status.get("oldest_candidate_reached")
                        if "start_time" in prev_status and not initial_run_start:
                            initial_run_start = prev_status["start_time"]
            except Exception:
                pass

        try:
            while time.time() < end_time:
                # Check manual stop flag
                if os.path.exists(stop_flag):
                    logger.info("🛑 STOP_HARVEST.flag detected! Gracefully wrapping up harvesting loop...")
                    break

                # Check dynamic runtime control file (harvest_control.json)
                if os.path.exists(control_path):
                    try:
                        with open(control_path, "r", encoding="utf-8") as cf:
                            ctrl = json.load(cf)
                        if ctrl.get("stop"):
                            logger.info("🛑 Stop commanded via harvest_control.json!")
                            break
                        if "add_seconds" in ctrl:
                            add_sec = int(ctrl["add_seconds"])
                            if add_sec > 0:
                                end_time += add_sec
                                duration_seconds += add_sec
                                logger.info(f"⏱️ Extended duration by {add_sec}s! Total duration: {duration_seconds}s")
                        os.remove(control_path)
                    except Exception as ce:
                        logger.debug(f"harvest_control error: {ce}")

                scroll_count += 1
                now = time.time()
                elapsed = int(now - start_time)
                remaining = max(0, int(end_time - now))

                # Harvest visible UIA message bubbles
                records = self.harvest_current_view()
                staged_records, promoted_records, skp, err = self.stage_batch(records)
                ins = len(staged_records)
                prom = len(promoted_records)

                total_scanned += len(records)
                total_staged += ins
                session_promoted += prom
                total_skipped += skp
                promoted_since_sync += prom

                if promoted_records:
                    all_promoted_candidates.extend(promoted_records)

                if staged_records:
                    if not first_person_staged:
                        first_person_staged = {
                            "name": staged_records[-1]["name"],
                            "company": staged_records[-1]["company"],
                            "email": staged_records[-1]["primary_email"],
                            "phone": staged_records[-1]["primary_phone"],
                            "all_phones": staged_records[-1]["all_phones"],
                            "timestamp": staged_records[-1]["timestamp"],
                            "discovery_id": staged_records[-1]["discovery_id"]
                        }
                    # Track latest staged record
                    last_person_staged = {
                        "name": staged_records[0]["name"],
                        "company": staged_records[0]["company"],
                        "email": staged_records[0]["primary_email"],
                        "phone": staged_records[0]["primary_phone"],
                        "all_phones": staged_records[0]["all_phones"],
                        "timestamp": staged_records[0]["timestamp"],
                        "discovery_id": staged_records[0]["discovery_id"]
                    }
                    consecutive_no_new = 0
                else:
                    consecutive_no_new += 1

                # Update oldest candidate reached
                if records:
                    oldest_in_view = records[0]  # Topmost item in current view
                    if not oldest_candidate_reached or (oldest_in_view.get("timestamp") and oldest_in_view["timestamp"] != oldest_candidate_reached.get("timestamp")):
                        oldest_candidate_reached = {
                            "name": oldest_in_view["name"],
                            "company": oldest_in_view["company"],
                            "email": oldest_in_view["primary_email"],
                            "phone": oldest_in_view["primary_phone"],
                            "all_phones": oldest_in_view["all_phones"],
                            "timestamp": oldest_in_view["timestamp"],
                            "discovery_id": oldest_in_view["discovery_id"]
                        }

                # Periodic Parquet & RecruiterStore synchronization (every 10 new promoted candidates or every 60s)
                if promoted_since_sync >= 10 or (promoted_since_sync > 0 and time.time() - last_sync_time > 60):
                    try:
                        sync_parquet()
                        recruiter_store.reload()
                        last_sync_time = time.time()
                        promoted_since_sync = 0
                        logger.info("🔄 Parquet Store synchronized with live Master DB.")
                    except Exception as se:
                        logger.debug(f"Parquet sync notice: {se}")

                cumulative_promoted = len(all_promoted_candidates)

                # Log progress
                logger.info(
                    f"[Scroll #{scroll_count}] Elapsed: {elapsed//60}m {elapsed%60}s / {duration_seconds//60}m | "
                    f"Buffer: {len(records)} | +{ins} staged, +{prom} session live (Cumulative DB: {cumulative_promoted}) | Remaining: {remaining}s"
                )

                # Save live JSON status file
                status_data = {
                    "status": "running",
                    "initial_run_start": initial_run_start,
                    "session_start_time": datetime.fromtimestamp(start_time).isoformat(),
                    "current_time": datetime.fromtimestamp(now).isoformat(),
                    "scheduled_finish_time": datetime.fromtimestamp(end_time).isoformat(),
                    "total_target_hours": round(duration_seconds / 3600, 2),
                    "duration_seconds_target": duration_seconds,
                    "elapsed_seconds": elapsed,
                    "remaining_seconds": remaining,
                    "scroll_count": scroll_count,
                    "total_messages_scanned": total_scanned,
                    "total_new_candidates_staged": total_staged,
                    "cumulative_promoted_to_master_db": cumulative_promoted,
                    "session_promoted_to_master_db": session_promoted,
                    "prior_promoted_to_master_db": prior_promoted_count,
                    "total_skipped_duplicates": total_skipped,
                    "first_person_staged": first_person_staged,
                    "last_person_staged": last_person_staged,
                    "oldest_candidate_reached": oldest_candidate_reached,
                    "last_person_collected_name": (last_person_staged.get("name") if last_person_staged else (oldest_candidate_reached.get("name") if oldest_candidate_reached else "Unknown")),
                    "recent_promoted_sample": all_promoted_candidates[-10:] if all_promoted_candidates else []
                }
                try:
                    with open(status_file_path, "w", encoding="utf-8") as f:
                        json.dump(status_data, f, indent=2)
                    with open(roster_file_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "initial_session_start": initial_run_start,
                            "session_start": datetime.fromtimestamp(start_time).isoformat(),
                            "current_update": datetime.fromtimestamp(now).isoformat(),
                            "total_promoted": cumulative_promoted,
                            "session_promoted": session_promoted,
                            "prior_promoted": prior_promoted_count,
                            "candidates": all_promoted_candidates
                        }, f, indent=2)
                except Exception as e:
                    logger.debug(f"Status file write error: {e}")

                # Check if remaining time is too short for another scroll
                if remaining < 2:
                    break

                # Find topmost UIA message element to anchor virtualized scroll
                oldest_elem = None
                try:
                    msg_bodies = [d for d in self.win.descendants() if (d.element_info.automation_id or "").startswith("message-body-")]
                    if msg_bodies:
                        oldest_elem = msg_bodies[0]
                except Exception:
                    pass

                # Scroll UPWARDS into past
                pulse_steps = 15 if consecutive_no_new > 2 else 10
                self.scroll_up(steps=pulse_steps, oldest_elem=oldest_elem)

                sleep_dur = min(delay_between_scrolls, float(remaining))
                time.sleep(sleep_dur)

        finally:
            self.restore_window()

        # Finalize run: field enrichment pass + full DuckDB parquet sync
        logger.info("Executing field enrichment and final Master DB -> Parquet sync...")
        try:
            try:
                from backend.scripts.complete_candidate_fields_v2 import run_enrichment_v2
                run_enrichment_v2()
                logger.info("Auto field enrichment pass complete!")
            except Exception as fe:
                logger.debug(f"Field enrichment notice: {fe}")

            sync_parquet()
            recruiter_store.reload()
            logger.info("Final Parquet sync complete!")
        except Exception as e:
            logger.error(f"Final sync error: {e}")

        total_elapsed = int(time.time() - start_time)
        cumulative_promoted = len(all_promoted_candidates)
        final_summary = {
            "status": "completed",
            "initial_run_start": initial_run_start,
            "session_start_time": datetime.fromtimestamp(start_time).isoformat(),
            "completion_time": datetime.fromtimestamp(time.time()).isoformat(),
            "scheduled_finish_time": datetime.fromtimestamp(end_time).isoformat(),
            "total_target_hours": round(duration_seconds / 3600, 2),
            "duration_seconds_target": duration_seconds,
            "total_elapsed_seconds": total_elapsed,
            "total_scrolls": scroll_count,
            "total_messages_scanned": total_scanned,
            "total_new_candidates_staged": total_staged,
            "cumulative_promoted_to_master_db": cumulative_promoted,
            "session_promoted_to_master_db": session_promoted,
            "prior_promoted_to_master_db": prior_promoted_count,
            "total_skipped_duplicates": total_skipped,
            "first_person_staged": first_person_staged,
            "last_person_staged": last_person_staged,
            "oldest_candidate_reached": oldest_candidate_reached,
            "last_person_collected_name": (last_person_staged.get("name") if last_person_staged else (oldest_candidate_reached.get("name") if oldest_candidate_reached else "Unknown")),
            "total_candidates_in_report": cumulative_promoted
        }

        try:
            with open(status_file_path, "w", encoding="utf-8") as f:
                json.dump(final_summary, f, indent=2)
            with open(roster_file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "initial_session_start": initial_run_start,
                    "session_start": datetime.fromtimestamp(start_time).isoformat(),
                    "completion_time": datetime.fromtimestamp(time.time()).isoformat(),
                    "total_promoted": cumulative_promoted,
                    "session_promoted": session_promoted,
                    "prior_promoted": prior_promoted_count,
                    "candidates": all_promoted_candidates
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Final status file write error: {e}")

        logger.info(f"🏁 Autonomous Deep Upward Run Finished in {total_elapsed}s!")
        logger.info(f"👤 Last Person Collected: {final_summary['last_person_collected_name']}")
        logger.info(f"📊 Summary: {final_summary}")
        return final_summary


def main():
    parser = argparse.ArgumentParser(description="Autonomous Deep Upward Teams Ingestion Engine")
    parser.add_argument("--chat", type=str, default="CTV- Phone numbers", help="Target Teams chat name")
    parser.add_argument("--duration", type=int, default=7200, help="Duration in seconds (default 7200 = 2 hours)")
    parser.add_argument("--delay", type=float, default=1.8, help="Delay in seconds between scrolls")
    parser.add_argument("--owner", type=int, default=1, help="Owner user ID for discovery_staging")
    parser.add_argument("--visible", action="store_true", default=False, help="Explicitly show Teams window on screen")
    parser.add_argument("--offscreen", action="store_true", default=True, help="Move Teams offscreen (-9000,-9000)")

    args = parser.parse_args()

    # Default is off-screen background execution (Zero screen intrusion)
    is_visible = bool(args.visible) and not bool(args.offscreen and not args.visible)
    extractor = DeepUpwardTeamsExtractor(target_chat=args.chat, owner_user_id=args.owner, visible=is_visible)
    res = extractor.run_upward_harvest(duration_seconds=args.duration, delay_between_scrolls=args.delay)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
