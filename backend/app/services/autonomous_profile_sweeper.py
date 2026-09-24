"""
Autonomous Profile Sweeper & Quality Healing Engine - TalentOps AI

Operates continuously in the background whenever the backend is live.
Enforces the strict daily operating schedule of 6:00 PM (18:00) to 4:00 AM (04:00)
local time (with configurable override/force mode).

Responsibilities:
1. Recruiter Name Cleaning & Noise Elimination:
   - Strips mailing list headers ('Name' via Group -> Name).
   - Strips DBA suffixes (Christopher Taylor Dba ... -> Christopher Taylor).
   - Removes stray single/double quotes around names while preserving internal apostrophes (O'Flynn, D'Estaing).
   - Identifies non-person corporate entities, newsletters, publications, and UI noise (DocuSign, Becker's Hospital Review, Sent Items, etc.) and deactivates them.
   - Recovers human recruiter names from email local parts when corporate agency names were entered in name fields (e.g. Express Employment Professionals + matt.helander@expresspros.com -> Matt Helander).
   - Reclassifies pure job titles erroneously stored in recruiter name fields.
2. Email Intelligence & Corporate Synthesis:
   - Identifies and flags mailing list / distribution groups (@googlegroups.com, @yahoogroups.com, etc.) as undeliverable.
   - Cleans fake/placeholder emails (missing.local, example.com, etc.).
   - Synthesizes and DNS MX-verifies corporate email addresses for genuine profiles missing contact data using EmailIntelligenceService.
   - Learns corporate domain patterns dynamically from valid recruiter emails.
3. State & Location Recovery:
   - Mines location, notes, raw data, and review reasons for standard US 2-letter state codes.
   - Normalizes job titles to standard enterprise recruiting taxonomy.
4. Dynamic Scoring & Dual-Persistence:
   - Recalculates completeness and quality scores dynamically.
   - Updates DuckDB Parquet dataset and synchronizes with PostgreSQL where applicable.
   - Reloads RecruiterStore and invalidates query caches so updates reflect immediately.
"""

import os
import re
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from collections import deque

import duckdb
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.models import Recruiter, Company, EnrichmentAudit
from .recruiter_store import _get_duckdb, PARQUET_FILE, recruiter_store
from .parquet_writer import parquet_writer
from .email_intelligence_service import email_intelligence, FREE_EMAIL_DOMAINS

logger = logging.getLogger("talentops.sweeper")

# ── Geographic and State Mapping ─────────────────────────────────────────────
STATE_MAP = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA',
    'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'ON', 'PE', 'QC', 'SK', 'UK', 'DE', 'FR', 'IN', 'AU', 'SG', 'IE'
}

# ── Standard Recruiting Job Taxonomy ──────────────────────────────────────────
TITLE_TAXONOMY = {
    'vp': 'VP of Talent Acquisition',
    'vice president': 'VP of Talent Acquisition',
    'director': 'Director of Talent Acquisition',
    'head of talent': 'Head of Talent Acquisition',
    'head of recruiting': 'Head of Recruiting',
    'principal': 'Principal Recruiter',
    'lead': 'Lead Technical Recruiter',
    'senior': 'Senior Technical Recruiter',
    'sr': 'Senior Technical Recruiter',
    'talent acquisition': 'Talent Acquisition Specialist',
    'technical recruiter': 'Technical Recruiter',
    'sourcer': 'Talent Sourcer',
    'recruiter': 'Recruiter',
}

# ── Non-human noise, CRM status notes & publication patterns ────────────────
NON_HUMAN_NAME_PATTERNS = [
    r'\bdocusign\b',
    r'\bshared document\b',
    r'\bamerica\'?s cup\b',
    r'\bdegree connection\b',
    r'\bhas a premium\b',
    r'\bsent items\b',
    r'\binbox\b',
    r'\bbasic text\b',
    r'\bask gemini\b',
    r'\bnew tab\b',
    r'\bsign in\b',
    r'\bsign up\b',
    r'\blogin\b',
    r'\bregister\b',
    r'\bview profile\b',
    r'\bunknown professional\b',
    r'\banonymous\b',
    r'\bhospital review\b',
    r'\burl preview\b',
    r'\bnotifications?\b',
    r'\bfrontdesk\b',
    r'\bbulletin\b',
    r'\bnewsletter\b',
    r'\bteam logicit\b',
    r'\bcorps team\b',
    # CRM status tags & notes saved in name field
    r'\balready added\b',
    r'\bworking with someone\b',
    r'\bdo not contact\b',
    r'\bnot interested\b',
    r'\bleft voicemail\b',
    r'\bfollow up\b',
    r'\bno response\b',
    r'\bcontacted\b',
    r'\bunsubscribed\b',
    r'\bbounced\b',
    r'\bopted out\b',
]

# ── Generic corporate name indicators in recruiter_name field ────────────────
CORPORATE_INDICATORS_IN_NAME = [
    r'\bprofessionals?\b',
    r'\brecruiting team\b',
    r'\btalent team\b',
    r'\bstaffing\b',
    r'\bconsulting\b',
    r'\bservicesllc\b',
    r'\bsystem one\b',
    r'\bcareernet\b',
    r'\btechnologies\b',
    r'\bsolutions llc\b',
    r'\brapid response team\b',
    r'\bfacilities maintenance\b',
    r'\boperations and maintenance\b',
    r'\bsupply chain\b',
    r'\blogistics\b',
]

# ── Pure job titles in name field ─────────────────────────────────────────────
PURE_JOB_TITLE_KEYWORDS = {
    "recruiter", "technical recruiter", "senior recruiter", "lead recruiter",
    "principal recruiter", "talent acquisition", "sourcer", "recruiting specialist",
    "staffing specialist", "consultant", "human resources", "talent partner",
    "vice president", "director of recruiting", "recruiting manager", "hr specialist",
    "sales development representative", "sales representative", "business development representative",
    "business development executive", "business development executive sr", "account executive",
    "operations manager", "recruitment consultant", "head of people", "head of talent",
    "vice president of human resources", "director of talent acquisition"
}

# ── Professional credentials to strip from candidate names ───────────────────
CREDENTIALS_SUFFIX_PATTERN = r'\s+(?:m\.?b\.?a\.?|ph\.?d\.?|m\.?s\.?|b\.?s\.?|b\.?a\.?|cpa|pmp|cfa|sphr|phr|shrm-cp|shrm-scp|pe|eit|csc)\b\.?'
TRAILING_JOB_TITLE_PATTERN = r'\s+(?:data analyst|software engineer|technical recruiter|recruiter|developer|consultant|manager|specialist|lead|architect|analyst)\b.*$'



# ── Mailing list & generic role email prefixes ────────────────────────────────
ROLE_EMAIL_PREFIXES = {
    "news", "info", "contact", "support", "sales", "billing", "careers", "jobs",
    "hr", "admin", "administrator", "account", "accounts", "techteam", "team",
    "help", "office", "marketing", "hello", "general", "inquiries", "mail"
}

# ── Corporate & Non-Human Tokens (Prevent false name recovery from email) ──
NOT_HUMAN_NAME_TOKENS = {
    "consultants", "professionals", "consultant", "professional", "services",
    "solutions", "technologies", "technology", "partners", "recruitment",
    "recruiting", "staffing", "systems", "system", "resources", "group",
    "associates", "management", "holdings", "capital", "ventures", "enterprises",
    "team", "careernet", "university", "opportunities", "hospital", "healthcare",
    "review", "media", "agency", "network", "direct", "online", "global", "search",
    "talent", "people", "human", "placement", "advisors", "alliance", "international",
    "corp", "corporation", "company", "center", "centre", "division", "maintenance",
    "facility", "facilities", "supply", "supplies", "onboarding", "development", "strategic"
}

ROLE_OR_DEPT_WORDS = {
    "technical", "onboarding", "recruitment", "recruiting", "recruiter", "talent",
    "acquisition", "strategic", "sales", "sourcing", "sourcer", "staffing",
    "operations", "human", "resources", "hr", "people", "services", "solutions",
    "it", "executive", "lead", "specialist", "consultant", "manager", "director",
    "representative", "development", "business", "analyst", "engineering", "support",
    "salesforce", "recruiting", "recruiter", "staffin"
}

MAILING_LIST_DOMAINS = {"googlegroups.com", "yahoogroups.com", "groups.io"}


class AutonomousProfileSweeper:
    """
    Autonomous Background Quality Healing, Sanitization & Enrichment Engine.
    Executes profile-by-profile verification and repair in scheduled overnight windows
    (18:00 - 04:00) or continuously when active.
    """

    def __init__(self):
        self.running: bool = False
        self.force_active: bool = os.getenv("AUTONOMOUS_SWEEPER_FORCE_ACTIVE", "false").lower() in ("1", "true", "yes", "on")
        self.enabled: bool = os.getenv("AUTONOMOUS_SWEEPER_ENABLED", "true").lower() in ("1", "true", "yes", "on")
        self.batch_size: int = int(os.getenv("AUTONOMOUS_SWEEPER_BATCH_SIZE", "100"))
        self.batch_delay: float = float(os.getenv("AUTONOMOUS_SWEEPER_BATCH_DELAY", "1.0"))
        
        # Schedule window settings (18:00 to 04:00 daily)
        self.start_hour: int = 18  # 6:00 PM
        self.end_hour: int = 4     # 4:00 AM
        
        # In-memory operational metrics
        self.stats = {
            "total_checked": 0,
            "total_repaired": 0,
            "names_repaired": 0,
            "non_persons_purged": 0,
            "names_recovered_from_email": 0,
            "job_titles_reclassified": 0,
            "mailing_lists_flagged": 0,
            "emails_synthesized": 0,
            "states_resolved": 0,
            "titles_normalized": 0,
            "scores_recalculated": 0,
            "batches_processed": 0,
            "last_sweep_at": None,
            "last_batch_duration_sec": 0.0,
            "start_time": None,
        }
        
        # Live audit log deque (last 100 actions for telemetry)
        self.recent_actions: deque = deque(maxlen=100)
        self._loop_task: Optional[asyncio.Task] = None
        self._companies_cache: Dict[str, str] = {}

    def is_in_sweep_window(self) -> bool:
        """Checks if current local server time is within the 18:00 to 04:00 window."""
        now = datetime.now()
        hour = now.hour
        # Active between 18:00 (inclusive) and 23:59, OR between 00:00 (inclusive) and 04:00 (exclusive)
        return hour >= self.start_hour or hour < self.end_hour

    @property
    def is_window_active(self) -> bool:
        """Returns True if the engine is currently allowed to sweep."""
        return self.force_active or self.is_in_sweep_window()

    def get_company_name_by_id(self, company_id: Any, db: Optional[Session] = None) -> Optional[str]:
        """Resolves company name from cache or DB."""
        if not company_id:
            return None
        c_str = str(company_id).strip()
        if c_str in self._companies_cache:
            return self._companies_cache[c_str]
            
        # Try integer query if applicable
        if db:
            try:
                if c_str.isdigit():
                    comp = db.query(Company).filter(Company.company_id == int(c_str)).first()
                    if comp and comp.company_name:
                        self._companies_cache[c_str] = comp.company_name
                        return comp.company_name
            except Exception:
                pass
                
        # Fallback: company_id itself is often capitalized name string in parquet
        if not c_str.isdigit() and len(c_str) > 2:
            self._companies_cache[c_str] = c_str
            return c_str

        return None

    def inspect_and_clean_profile(
        self,
        record: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Deeply inspects an individual recruiter profile and repairs any data quality defects.
        Returns:
            (is_modified: bool, updated_record: Dict, actions_taken: List[str])
        """
        recruiter_id = record.get("recruiter_id")
        orig_name = record.get("recruiter_name")
        orig_email = record.get("email")
        orig_title = record.get("title")
        orig_state = record.get("state")
        orig_active = record.get("is_active", True)
        
        updated = dict(record)
        actions = []
        is_modified = False

        # ─────────────────────────────────────────────────────────────────────
        # 1. NAME SANITIZATION & NOISE PURGING
        # ─────────────────────────────────────────────────────────────────────
        name_str = str(orig_name).strip() if orig_name is not None else ""
        name_lower = name_str.lower()
        
        # A. Detect Non-Person Entities & Mailbox Noise
        is_non_human = False
        for pat in NON_HUMAN_NAME_PATTERNS:
            if re.search(pat, name_str, re.IGNORECASE):
                is_non_human = True
                break
                
        if is_non_human:
            updated["is_active"] = False
            updated["needs_review"] = True
            updated["review_reason"] = "PURGED_NON_PERSON_METADATA"
            updated["recruiter_name"] = None
            updated["normalized_recruiter_name"] = None
            is_modified = True
            actions.append(f"PURGED_NON_PERSON_METADATA: '{name_str}'")
            self.stats["non_persons_purged"] += 1

        else:
            # B. Corporate / Agency Name in Name Field
            is_corp_name = any(re.search(pat, name_str, re.IGNORECASE) for pat in CORPORATE_INDICATORS_IN_NAME)
            if is_corp_name:
                # Check if we can recover human name from email (e.g. matt.helander@expresspros.com)
                recovered_human = None
                if orig_email and "@" in str(orig_email):
                    local_part = str(orig_email).split("@")[0].lower()
                    local_clean = re.sub(r'\+.*', '', local_part)
                    local_clean = re.sub(r'\d+$', '', local_clean)
                    if "." in local_clean:
                        parts = local_clean.split(".")
                        if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts):
                            p0_lower, p1_lower = parts[0].lower(), parts[1].lower()
                            if (
                                p0_lower not in ROLE_EMAIL_PREFIXES and p1_lower not in ROLE_EMAIL_PREFIXES
                                and p0_lower not in NOT_HUMAN_NAME_TOKENS and p1_lower not in NOT_HUMAN_NAME_TOKENS
                            ):
                                recovered_human = f"{parts[0].title()} {parts[1].title()}"
                
                if recovered_human:
                    updated["recruiter_name"] = recovered_human
                    updated["normalized_recruiter_name"] = recovered_human.lower()
                    # Preserve agency as company if company is empty
                    if not updated.get("company_id") or str(updated.get("company_id")) == "None":
                        updated["company_id"] = name_str
                    is_modified = True
                    actions.append(f"RECOVERED_NAME_FROM_EMAIL: '{name_str}' -> '{recovered_human}'")
                    self.stats["names_recovered_from_email"] += 1
                    name_str = recovered_human
                    name_lower = name_str.lower()
                else:
                    # Deactivate corporate entity / branch office mailbox
                    updated["is_active"] = False
                    updated["needs_review"] = True
                    updated["review_reason"] = "BRANCH_OFFICE_OR_CORPORATE_ENTITY"
                    is_modified = True
                    actions.append(f"FLAGGED_CORPORATE_ENTITY_NAME: '{name_str}'")
                    self.stats["non_persons_purged"] += 1

            # C. Mailing List Headers ("Name" via Mailing Group)
            if " via " in name_lower:
                via_match = re.match(r'^[\'"]?([^\'"]+?)[\'"]?\s+\bvia\b\s+', name_str, flags=re.IGNORECASE)
                if via_match:
                    clean = via_match.group(1).strip().strip('"\'')
                    if clean and clean != name_str:
                        updated["recruiter_name"] = clean.title()
                        updated["normalized_recruiter_name"] = clean.lower()
                        is_modified = True
                        actions.append(f"STRIPPED_MAILING_LIST_HEADER: '{name_str}' -> '{clean.title()}'")
                        self.stats["names_repaired"] += 1
                        name_str = clean.title()
                        name_lower = name_str.lower()

            # D. DBA (Doing Business As) & Professional Suffixes
            if re.search(r'\s+\bd/?b/?a\b\s+', name_str, flags=re.IGNORECASE):
                parts = re.split(r'\s+d/?b/?a\s+', name_str, flags=re.IGNORECASE)
                clean = parts[0].strip().strip('"\'')
                if clean and clean != name_str:
                    updated["recruiter_name"] = clean.title()
                    updated["normalized_recruiter_name"] = clean.lower()
                    is_modified = True
                    actions.append(f"STRIPPED_DBA_SUFFIX: '{name_str}' -> '{clean.title()}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean.title()
                    name_lower = name_str.lower()

            # E. Stray Quotes Around Name (while preserving O'Flynn, D'Estaing)
            if name_str.startswith(('"', "'")) or name_str.endswith(('"', "'")):
                clean = name_str.strip('"\' ')
                if clean and clean != name_str:
                    updated["recruiter_name"] = clean
                    updated["normalized_recruiter_name"] = clean.lower()
                    is_modified = True
                    actions.append(f"STRIPPED_STRAY_QUOTES: '{name_str}' -> '{clean}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean
                    name_lower = name_str.lower()

            # F. Strip Professional Credentials (CPA, PMP, PhD, etc.)
            if re.search(CREDENTIALS_SUFFIX_PATTERN, name_str, flags=re.IGNORECASE):
                clean_cred = re.sub(CREDENTIALS_SUFFIX_PATTERN, '', name_str, flags=re.IGNORECASE).strip()
                if clean_cred and clean_cred != name_str:
                    updated["recruiter_name"] = clean_cred
                    updated["normalized_recruiter_name"] = clean_cred.lower()
                    is_modified = True
                    actions.append(f"STRIPPED_CREDENTIALS_SUFFIX: '{name_str}' -> '{clean_cred}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean_cred
                    name_lower = name_str.lower()

            # G. Deduplicate Repeated Name Tokens (e.g. Jim Bright Jim Bright Jim.Bright -> Jim Bright)
            name_words = re.sub(r'([a-zA-Z])\.([a-zA-Z])', r'\1 \2', name_str).split()
            if len(name_words) >= 4:
                half = len(name_words) // 2
                if [w.lower() for w in name_words[:half]] == [w.lower() for w in name_words[half:half*2]]:
                    clean_rep = " ".join(name_words[:half])
                    updated["recruiter_name"] = clean_rep
                    updated["normalized_recruiter_name"] = clean_rep.lower()
                    is_modified = True
                    actions.append(f"DEDUPED_NAME_REPETITION: '{name_str}' -> '{clean_rep}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean_rep
                    name_lower = name_str.lower()
                elif len(name_words) >= 4 and name_words[0].lower() == name_words[2].lower() and name_words[1].lower() == name_words[3].lower():
                    clean_rep = f"{name_words[0]} {name_words[1]}"
                    updated["recruiter_name"] = clean_rep
                    updated["normalized_recruiter_name"] = clean_rep.lower()
                    is_modified = True
                    actions.append(f"DEDUPED_NAME_REPETITION: '{name_str}' -> '{clean_rep}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean_rep
                    name_lower = name_str.lower()

            # H. Trailing Job Title Appended to Name (e.g. Allen Chao Hsuan Chi Data Analyst -> Allen Chao Hsuan Chi)
            if re.search(TRAILING_JOB_TITLE_PATTERN, name_str, flags=re.IGNORECASE):
                clean_name_lead = re.sub(TRAILING_JOB_TITLE_PATTERN, '', name_str, flags=re.IGNORECASE).strip()
                lead_words = clean_name_lead.split()
                if len(lead_words) >= 2 and all(len(w) >= 2 for w in lead_words):
                    m_title = re.search(TRAILING_JOB_TITLE_PATTERN, name_str, flags=re.IGNORECASE)
                    if m_title:
                        ext_title = m_title.group(0).strip().title()
                        if not orig_title or str(orig_title).lower() in ("none", "nan", "professional", "recruiter"):
                            updated["title"] = ext_title
                    updated["recruiter_name"] = clean_name_lead
                    updated["normalized_recruiter_name"] = clean_name_lead.lower()
                    is_modified = True
                    actions.append(f"STRIPPED_TRAILING_TITLE: '{name_str}' -> '{clean_name_lead}'")
                    self.stats["names_repaired"] += 1
                    name_str = clean_name_lead
                    name_lower = name_str.lower()

            # I. Pure Job Titles Erroneously Stored as Name
            name_words = name_lower.split()
            is_pure_title = False
            if name_lower in PURE_JOB_TITLE_KEYWORDS:
                is_pure_title = True
            elif len(name_words) >= 2 and all(w in ROLE_OR_DEPT_WORDS for w in name_words):
                is_pure_title = True
            elif any(name_lower.startswith(ts) for ts in ["recruiter -", "recruiter,", "lead recruiter", "talent acquisition specialist", "sales development representative", "sales representative"]):
                is_pure_title = True

            if is_pure_title:
                if not orig_title or str(orig_title).lower() in ("none", "nan", "professional", "recruiter"):
                    updated["title"] = name_str.title()
                updated["recruiter_name"] = None
                updated["normalized_recruiter_name"] = None
                updated["needs_review"] = True
                updated["review_reason"] = "JOB_TITLE_IN_NAME_FIELD"
                is_modified = True
                actions.append(f"RECLASSIFIED_JOB_TITLE_FROM_NAME: '{name_str}' -> title")
                self.stats["job_titles_reclassified"] += 1

        # ─────────────────────────────────────────────────────────────────────
        # 2. EMAIL SANITIZATION & CORPORATE SYNTHESIS
        # ─────────────────────────────────────────────────────────────────────
        email_str = str(orig_email).strip().lower() if orig_email is not None else ""
        
        # A. Invalidate Mailing List Groups (@googlegroups.com, etc.)
        if "googlegroups.com" in email_str or "yahoogroups.com" in email_str or "groups.io" in email_str:
            if updated.get("is_deliverable", True):
                updated["is_deliverable"] = False
                updated["email_status"] = "mailing_list_group"
                is_modified = True
                actions.append(f"FLAGGED_MAILING_LIST_EMAIL: {email_str}")
                self.stats["mailing_lists_flagged"] += 1

        # B. Clean Placeholder / Fake Emails
        elif any(fake in email_str for fake in ["missing.local", "example.com", "test@test.com", "none@none.com"]):
            updated["email"] = None
            updated["is_deliverable"] = False
            updated["email_status"] = "missing"
            is_modified = True
            actions.append(f"CLEARED_PLACEHOLDER_EMAIL: {email_str}")
            email_str = ""

        # C. Missing or Clean Candidate Email Synthesis
        # If candidate has clean human name and known company, synthesize corporate email!
        current_name = updated.get("recruiter_name")
        current_email = updated.get("email")
        if (
            updated.get("is_active", True)
            and current_name
            and len(current_name) > 3
            and (not current_email or str(current_email).strip() == "" or str(current_email).lower() in ("none", "nan"))
        ):
            comp_name = self.get_company_name_by_id(updated.get("company_id"), db=db)
            if comp_name and len(comp_name) >= 2:
                try:
                    synth_res = email_intelligence.resolve_and_enrich_candidate(
                        full_name=current_name,
                        company_name=comp_name,
                        db=db
                    )
                    if synth_res.get("email") and synth_res.get("has_mx"):
                        updated["email"] = synth_res["email"]
                        updated["email_status"] = "synthesized_mx_verified"
                        updated["email_confidence"] = int(synth_res.get("confidence", 0.9) * 100)
                        updated["is_deliverable"] = True
                        updated["email_source"] = "email_intelligence_sweeper"
                        updated["email_verified_at"] = datetime.now(timezone.utc).isoformat()
                        updated["email_generated"] = True
                        is_modified = True
                        actions.append(f"SYNTHESIZED_CORPORATE_EMAIL: {synth_res['email']} ({synth_res.get('provider')})")
                        self.stats["emails_synthesized"] += 1
                except Exception as synth_err:
                    logger.debug("Email synthesis error for %s: %s", current_name, synth_err)

        # D. Learn Company Pattern from Observed Valid Corporate Email
        elif current_name and current_email and "@" in str(current_email):
            dom = str(current_email).split("@")[1].lower()
            if dom not in FREE_EMAIL_DOMAINS and dom not in MAILING_LIST_DOMAINS and "." in dom:
                try:
                    email_intelligence.learn_pattern_from_email(
                        email=str(current_email),
                        full_name=current_name,
                        company_name=self.get_company_name_by_id(updated.get("company_id"), db=db),
                        db=db
                    )
                except Exception:
                    pass

        # ─────────────────────────────────────────────────────────────────────
        # 3. STATE & LOCATION RECOVERY
        # ─────────────────────────────────────────────────────────────────────
        if updated.get("is_active", True) and (not orig_state or str(orig_state).strip() == "" or str(orig_state).lower() == "nan"):
            notes_val = str(record.get("notes") or "")
            raw_val = str(record.get("raw_data") or "")
            loc_val = str(record.get("location") or "")
            rev_val = str(record.get("review_reason") or "")
            combined_text = f"{loc_val} {notes_val} {raw_val} {rev_val}".upper()
            
            resolved_st = None
            for token in re.findall(r'\b[A-Z]{2}\b', combined_text):
                if token in STATE_MAP:
                    resolved_st = token
                    break
                    
            if resolved_st:
                updated["state"] = resolved_st
                updated["state_source"] = "sweeper_deep_text_mining"
                updated["state_confidence"] = "high"
                is_modified = True
                actions.append(f"RESOLVED_STATE: {resolved_st}")
                self.stats["states_resolved"] += 1

        # ─────────────────────────────────────────────────────────────────────
        # 4. JOB TITLE TAXONOMY NORMALIZATION
        # ─────────────────────────────────────────────────────────────────────
        current_title = updated.get("title")
        if current_title and str(current_title).strip() and str(current_title).lower() not in ("none", "nan"):
            t_raw = str(current_title).strip().lower()
            clean_t = None
            for k, v in TITLE_TAXONOMY.items():
                if re.search(rf'\b{k}\b', t_raw):
                    clean_t = v
                    break
            if clean_t and clean_t != current_title:
                updated["title"] = clean_t
                is_modified = True
                actions.append(f"STANDARDIZED_TITLE: '{current_title}' -> '{clean_t}'")
                self.stats["titles_normalized"] += 1

        # ─────────────────────────────────────────────────────────────────────
        # 5. DYNAMIC COMPLETENESS & QUALITY SCORING
        # ─────────────────────────────────────────────────────────────────────
        sc = 10
        cur_email = updated.get("email")
        if cur_email and "@" in str(cur_email) and "missing" not in str(cur_email):
            sc += 35
        cur_phone = updated.get("phone")
        if cur_phone and len(re.sub(r'[^\d]', '', str(cur_phone))) >= 10:
            sc += 25
        if updated.get("company_id") and str(updated.get("company_id")) != "None":
            sc += 15
        if updated.get("state") and updated.get("state") in STATE_MAP:
            sc += 10
        if updated.get("title") and len(str(updated.get("title"))) > 2:
            sc += 5

        new_score = min(sc, 100)
        if new_score != record.get("completeness_score"):
            updated["completeness_score"] = new_score
            is_modified = True
            self.stats["scores_recalculated"] += 1

        # Always mark sweep scan timestamp and status
        updated["last_scan_at"] = datetime.now(timezone.utc).isoformat()
        updated["sentinel_status"] = "swept_clean"
        is_modified = True  # Status stamp marks record as verified clean

        return is_modified, updated, actions

    def sweep_batch(self, limit: int = 100) -> Dict[str, Any]:
        """
        Executes one atomic batch sweep:
        1. Selects priority dirty records or unscanned records from Parquet.
        2. Applies profile-by-profile inspection and healing.
        3. Persists repairs to Parquet via DuckDB / ParquetWriter.
        4. Synchronizes affected PostgreSQL recruiter records.
        """
        t0 = time.time()
        duck = _get_duckdb()
        con = duck.connect()
        
        target_file = PARQUET_FILE.replace(os.sep, "/")
        
        # Sequential Profile-by-Profile Quality Sweeper:
        # Traverses all recruiter profiles in the dataset, inspecting each for defects.
        # Once swept, records are stamped sentinel_status = 'swept_clean'.
        query = f"""
            SELECT * FROM read_parquet('{target_file}')
            WHERE (sentinel_status IS NULL OR sentinel_status != 'swept_clean')
            ORDER BY recruiter_id ASC
            LIMIT {limit}
        """
        
        try:
            df = con.execute(query).fetchdf()
        except Exception as e:
            logger.error("Error querying parquet batch in sweeper: %s", e)
            con.close()
            return {"count": 0, "repaired": 0, "duration": round(time.time() - t0, 3)}
            
        con.close()

        if df.empty:
            return {"count": 0, "repaired": 0, "duration": round(time.time() - t0, 3)}

        records = df.to_dict(orient="records")
        updated_records = []
        actual_repairs = 0

        # Open DB session for company lookup and candidate enrichment
        db = None
        try:
            db = SessionLocal()
        except Exception as e:
            logger.warning("Could not establish Postgres session for sweeper: %s", e)

        try:
            for rec in records:
                self.stats["total_checked"] += 1
                is_mod, clean_rec, acts = self.inspect_and_clean_profile(rec, db=db)
                if is_mod:
                    updated_records.append(clean_rec)
                    if acts:
                        actual_repairs += 1
                        self.stats["total_repaired"] += 1
                        for a in acts:
                            log_entry = f"[{time.strftime('%X')}] Recruiter #{clean_rec['recruiter_id']}: {a}"
                            self.recent_actions.append(log_entry)
                            logger.info(log_entry)
                            
                        # Also sync to Postgres if session is live
                        if db and clean_rec.get("recruiter_id"):
                            try:
                                pg_r = db.query(Recruiter).filter(Recruiter.recruiter_id == clean_rec["recruiter_id"]).first()
                                if pg_r:
                                    if clean_rec.get("recruiter_name"):
                                        pg_r.recruiter_name = clean_rec["recruiter_name"]
                                    if clean_rec.get("email"):
                                        pg_r.email = clean_rec["email"]
                                    if clean_rec.get("title"):
                                        pg_r.title = clean_rec["title"]
                                    if clean_rec.get("state"):
                                        pg_r.state = clean_rec["state"]
                                    if "is_active" in clean_rec:
                                        pg_r.is_active = clean_rec["is_active"]
                                    if "needs_review" in clean_rec:
                                        pg_r.needs_review = clean_rec["needs_review"]
                                    if clean_rec.get("review_reason"):
                                        pg_r.review_reason = clean_rec["review_reason"]
                                    pg_r.completeness_score = clean_rec.get("completeness_score", 0)
                                    db.add(pg_r)
                            except Exception:
                                pass

            # Commit Postgres changes if any
            if db:
                try:
                    db.commit()
                except Exception as commit_err:
                    logger.debug("Postgres commit note in sweeper: %s", commit_err)
                    db.rollback()

            # Write updates back to Parquet
            if updated_records:
                parquet_writer.update_records(updated_records)
                recruiter_store.reload()

        finally:
            if db:
                db.close()

        duration = round(time.time() - t0, 3)
        self.stats["batches_processed"] += 1
        self.stats["last_sweep_at"] = datetime.now(timezone.utc).isoformat()
        self.stats["last_batch_duration_sec"] = duration

        return {
            "count": len(records),
            "repaired": actual_repairs,
            "duration": duration,
        }

    async def run_loop(self):
        """Asynchronous execution loop triggered during backend lifespan."""
        self.stats["start_time"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "[NIGHT SWEEPER] AUTONOMOUS NIGHT SWEEPER ACTIVE | Operating Window: %02d:00 - %02d:00 daily | Force Mode: %s",
            self.start_hour, self.end_hour, self.force_active
        )
        
        while self.running:
            if self.is_window_active:
                try:
                    res = await asyncio.to_thread(self.sweep_batch, self.batch_size)
                    if res["count"] > 0:
                        # Sleep controlled batch delay to prevent CPU spike
                        await asyncio.sleep(self.batch_delay)
                    else:
                        # No dirty or unscanned records remaining in dataset; idle for 30s
                        await asyncio.sleep(30.0)
                except Exception as e:
                    logger.error("Error in autonomous sweeper loop: %s", e)
                    await asyncio.sleep(10.0)
            else:
                # Outside active window (e.g. daytime 04:00 - 18:00): sleep 60s and check again
                now_str = datetime.now().strftime("%H:%M")
                logger.debug(
                    "Autonomous sweeper outside active window (18:00 - 04:00). Current time: %s. Sleeping 60s.",
                    now_str
                )
                await asyncio.sleep(60.0)

    def start(self):
        """Starts the autonomous sweeper worker in the background."""
        if not self.enabled:
            logger.info("Autonomous sweeper is disabled via AUTONOMOUS_SWEEPER_ENABLED=false")
            return
            
        if self.running:
            logger.info("Autonomous sweeper is already running.")
            return

        self.running = True
        self._loop_task = asyncio.create_task(self.run_loop())
        logger.info("Autonomous profile sweeper background task successfully initialized.")

    def stop(self):
        """Stops the autonomous sweeper worker gracefully."""
        self.running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("Autonomous profile sweeper stopped gracefully.")

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides full operational telemetry for UI dashboards and health checks."""
        now = datetime.now()
        return {
            "is_running": self.running,
            "is_window_active": self.is_window_active,
            "force_active": self.force_active,
            "operating_window": f"{self.start_hour:02d}:00 to {self.end_hour:02d}:00 daily",
            "server_local_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "current_hour": now.hour,
            "stats": dict(self.stats),
            "recent_actions": list(self.recent_actions),
        }


# Global Singleton Instance
autonomous_sweeper = AutonomousProfileSweeper()
