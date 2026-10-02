"""
scout_desktop/extractor/entity_classifier.py — Desktop Scout Hard Entity Type Classification Engine.

Classifies every extracted observation into exactly ONE entity type
BEFORE any staging, queueing, or backend dispatch happens.

Entity Types:
  PERSON        — Individual human being (candidate, recruiter, contact)
  COMPANY       — Business organization, corporate employer, staffing agency
  JOB_POSTING   — Job listing, vacancy, hiring requirement
  CONTACT_INFO  — Generic contact page data (email/phone without person identity)
  MARKET_SIGNAL — Industry trend, hiring signal, market intelligence
  NOISE         — UI artifacts, platform chrome, navigation elements

Strict Mandates:
- Synchronized with backend/app/services/entity_classifier.py
- Hard separation: Companies never enter person pipelines; Jobs never create recruiter records
"""

from __future__ import annotations

import re
import logging
from typing import Optional, Dict, Any, List

from scout_desktop.extractor.patterns import (
    clean_person_name,
    is_valid_person_name,
    clean_company_name,
    is_valid_company_name,
    is_plausible_title,
    UI_ACTIONS,
    PLATFORM_NAMES,
    BROWSER_CHROME_NOISE,
    QUALIFICATION_AND_REQUIREMENT_WORDS,
    CHECKMARK_AND_STATUS_SYMBOLS,
    COMMERCIAL_LEGAL_AND_BIZ_MARKERS,
    KNOWN_STANDALONE_CORPS,
    DEPARTMENTS_AND_INDUSTRIES,
)

logger = logging.getLogger("scout.entity_classifier")

# ── Entity Type Constants ─────────────────────────────────────────────
ENTITY_PERSON = "PERSON"
ENTITY_COMPANY = "COMPANY"
ENTITY_JOB_POSTING = "JOB_POSTING"
ENTITY_CONTACT_INFO = "CONTACT_INFO"
ENTITY_MARKET_SIGNAL = "MARKET_SIGNAL"
ENTITY_NOISE = "NOISE"

ALL_ENTITY_TYPES = frozenset({
    ENTITY_PERSON,
    ENTITY_COMPANY,
    ENTITY_JOB_POSTING,
    ENTITY_CONTACT_INFO,
    ENTITY_MARKET_SIGNAL,
    ENTITY_NOISE,
})

# Job Role Nouns for Job Posting Title Detection
JOB_ROLE_NOUNS = frozenset({
    "engineer", "engineering", "developer", "recruiter", "recruiting", "sourcer",
    "manager", "management", "director", "officer", "lead", "architect",
    "scientist", "specialist", "consultant", "analyst", "administrator",
    "coordinator", "advisor", "technician", "intern", "associate", "vice president",
    "teacher", "instructor", "professor", "educator", "tutor", "trainer",
    "nurse", "phlebotomist", "therapist", "practitioner", "physician", "doctor",
    "assistant", "clerk", "operator", "driver", "courier", "dispatcher",
    "buyer", "planner", "estimator", "machinist", "mechanic", "electrician",
    "plumber", "carpenter", "welder", "worker", "laborer", "teller",
    "accountant", "auditor", "underwriter", "adjuster", "cashier", "cook",
    "chef", "barista", "server", "bartender", "housekeeper", "guard",
    "attendant", "stylist", "agent", "representative", "specialist", "executive",
})

# Generic Contact Names
GENERIC_CONTACT_NAMES = frozenset({
    "contact", "contact us", "get in touch", "reach us", "customer service",
    "support team", "help desk", "reception", "front desk", "switchboard",
    "main office", "headquarters", "general inquiries", "general inquiry",
    "client services", "customer support", "inquiries", "info desk",
})

# Generic Role Email Prefixes
GENERIC_EMAIL_PREFIXES = frozenset({
    "info", "contact", "careers", "jobs", "hr", "recruiting", "admin", "support",
    "sales", "marketing", "media", "press", "billing", "office", "team",
    "general", "reception", "help", "hello", "inquiries",
})


def is_job_posting_title(text: Optional[str]) -> bool:
    """
    Check if a text phrase represents a job posting title rather than a person name.
    e.g. 'High School Mathematics Teacher', 'Transmission Project Manager', 'Senior React Developer'
    """
    if not text:
        return False
    words = [w.lower().strip() for w in re.split(r"[\s\-_/,]+", str(text)) if w.strip()]
    if not words:
        return False

    has_role_noun = any(w in JOB_ROLE_NOUNS for w in words)
    has_discipline = any(w in {
        "senior", "junior", "lead", "principal", "staff", "head", "vp", "director",
        "specialist", "mathematics", "math", "science", "english", "project",
        "transmission", "cloud", "order", "servicenow", "developer", "phlebotomist",
        "collector", "specimen", "software", "data", "quality", "full-time",
        "part-time", "contract", "remote", "hybrid", "entry-level"
    } for w in words)

    if has_role_noun and has_discipline and len(words) >= 2:
        return True

    # Multi-word role phrases
    low = text.strip().lower()
    if any(phrase in low for phrase in [
        "we are hiring", "now hiring", "job opening", "immediate opening",
        "position available", "career opportunity", "vacancy for", "urgent requirement"
    ]):
        return True

    return False


def is_company_industry(text: Optional[str]) -> bool:
    """Checks if a text is a corporate industry descriptor rather than a person's title."""
    if not text:
        return False
    clean = re.sub(r"[^\w\s]", " ", str(text).lower()).strip()
    clean = " ".join(clean.split())
    if clean in DEPARTMENTS_AND_INDUSTRIES:
        return True
    if re.search(r"business consulting and services|staffing and recruiting|information technology|computer software|financial services|management consulting", clean):
        return True
    return False


class DesktopEntityTypeClassifier:
    """
    Deterministic Entity Type Classifier for Desktop Scout.
    
    Uses cascading gates (no ML):
    1. NOISE detection (UI artifacts, platform chrome, navigation elements)
    2. COMPANY detection (legal suffixes, /company/ URL, overview title, generic email)
    3. JOB_POSTING detection (job title patterns, /jobs/ URL, hiring keywords)
    4. CONTACT_INFO detection (generic contact names, support email/phone)
    5. MARKET_SIGNAL detection (hiring trends, layoffs, reports)
    6. Default: PERSON (with strict human name validation)
    """

    def classify(
        self,
        raw_name: Optional[str],
        raw_title: Optional[str] = None,
        raw_company: Optional[str] = None,
        raw_email: Optional[str] = None,
        raw_phone: Optional[str] = None,
        source_url: Optional[str] = None,
        source_page_title: Optional[str] = None,
        extraction_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Classifies an extracted desktop observation into exactly one entity type.
        """
        signals = []
        name = (raw_name or "").strip()
        # Clean relative timestamp noise e.g. "Fineta Consulting · 20 minutes ago"
        name = re.sub(r"\s*[·•|]\s*\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|secs?|mins?|hrs?|d|w|m|h|y)\s*ago.*$", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\s*[·•|]\s*(?:reposted|shared|liked|commented).*$", "", name, flags=re.IGNORECASE).strip()
        # Clean page header prefixes e.g. "About A3 Staffing Solutions" -> "A3 Staffing Solutions"
        name = re.sub(r"^(?:about|overview of|welcome to)\s+", "", name, flags=re.IGNORECASE).strip()

        title = (raw_title or "").strip()
        company = (raw_company or "").strip()
        email = (raw_email or "").strip().lower()
        url = (source_url or "").strip().lower()
        page_title = (source_page_title or "").strip().lower()

        name_lower = name.lower()
        title_lower = title.lower()

        # ── GATE 1: NOISE Detection ───────────────────────────────────
        noise_res = self._check_noise(name, name_lower, title_lower, url, page_title, signals)
        if noise_res:
            return noise_res

        # ── GATE 2: JOB_POSTING Detection (Prioritized so Job Titles are not classified as Companies) ──
        job_res = self._check_job_posting(name, name_lower, title, title_lower, url, page_title, signals)
        if job_res:
            return job_res

        # ── GATE 3: CONTACT_INFO Detection (Prioritized so Generic Desks are classified as Contacts) ────
        contact_res = self._check_contact_info(name, name_lower, title_lower, email, raw_phone, url, signals)
        if contact_res:
            return contact_res

        # ── GATE 4: COMPANY Detection ─────────────────────────────────
        comp_res = self._check_company(name, name_lower, title, title_lower, company, email, url, page_title, signals)
        if comp_res:
            return comp_res

        # ── GATE 5: MARKET_SIGNAL Detection ───────────────────────────
        sig_res = self._check_market_signal(name, name_lower, title, title_lower, url, page_title, signals)
        if sig_res:
            return sig_res

        # ── GATE 6: PERSON (Default) ──────────────────────────────────
        c_name = clean_person_name(name)
        if c_name and is_valid_person_name(c_name):
            signals.append("valid_human_name")
            return {
                "entity_type": ENTITY_PERSON,
                "confidence": 0.90,
                "reason": f"Valid human name: {c_name}",
                "signals": signals,
                "clean_name": c_name,
            }

        # ── CamelCase & Mashed Username Recovery ─────────────────────
        if len(name.split()) == 1 and len(name) >= 5:
            # Step 1: Try CamelCase split
            camel_parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            if len(camel_parts.split()) >= 2:
                c_cc = clean_person_name(camel_parts)
                if c_cc and is_valid_person_name(c_cc):
                    signals.append("camelcase_name_recovered")
                    return {
                        "entity_type": ENTITY_PERSON,
                        "confidence": 0.85,
                        "reason": f"CamelCase username recovered: {c_cc}",
                        "signals": signals,
                        "clean_name": c_cc,
                    }

            # Step 2: Try common given name split for mashed handles e.g. "Lucasleverett" -> "Lucas Leverett"
            COMMON_GIVEN_NAMES = {
                'adam', 'alex', 'andrew', 'anthony', 'ben', 'brian', 'chris', 'dan', 'daniel',
                'david', 'eric', 'gary', 'greg', 'james', 'jason', 'jeff', 'joe', 'john',
                'justin', 'kevin', 'lucas', 'mark', 'matt', 'matthew', 'michael', 'nick',
                'paul', 'peter', 'richard', 'rob', 'robert', 'ryan', 'sam', 'sarah', 'scott',
                'steve', 'steven', 'tim', 'tom', 'thomas', 'will', 'william'
            }
            n_low = name.lower()
            for gn in sorted(COMMON_GIVEN_NAMES, key=len, reverse=True):
                if n_low.startswith(gn) and len(n_low) >= len(gn) + 3:
                    candidate_split = f"{name[:len(gn)].capitalize()} {name[len(gn):].capitalize()}"
                    c_m = clean_person_name(candidate_split)
                    if c_m and is_valid_person_name(c_m):
                        signals.append("mashed_handle_recovered")
                        return {
                            "entity_type": ENTITY_PERSON,
                            "confidence": 0.80,
                            "reason": f"Mashed handle recovered: {c_m}",
                            "signals": signals,
                            "clean_name": c_m,
                        }

        # Fallback check: Did a company name slip through without legal suffix?
        if is_valid_company_name(name):
            signals.append("fallback_company_name_detected")
            return {
                "entity_type": ENTITY_COMPANY,
                "confidence": 0.80,
                "reason": f"Fallback company detection: {name}",
                "signals": signals,
            }

        # Failed all gates — route to NOISE
        signals.append("unclassifiable_text")
        return {
            "entity_type": ENTITY_NOISE,
            "confidence": 0.60,
            "reason": f"Text failed all entity gates: {name}",
            "signals": signals,
        }

    def _check_noise(
        self,
        name: str,
        name_lower: str,
        title_lower: str,
        url: str,
        page_title: str,
        signals: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Detect UI artifacts, platform chrome, navigation noise."""
        if not name or len(name) < 2:
            signals.append("empty_or_short_name")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 1.0,
                "reason": "Empty or too-short name",
                "signals": signals,
            }

        if UI_ACTIONS.match(name) or name_lower in UI_ACTIONS.pattern:
            signals.append("ui_action_name")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 0.98,
                "reason": f"Name is UI action: {name}",
                "signals": signals,
            }

        if name_lower in PLATFORM_NAMES:
            signals.append("platform_name")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 0.98,
                "reason": f"Name is platform name: {name}",
                "signals": signals,
            }

        if name_lower in BROWSER_CHROME_NOISE or re.match(r"^(?:all|every|other|another|any)\s+(?:bookmarks?|tabs?|windows?|files?|profiles?|candidates?|pages?|apps?|tools?|items?|results?|shortcuts?|folders?)$", name_lower):
            signals.append("browser_chrome_noise")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 0.99,
                "reason": f"Browser chrome noise: {name}",
                "signals": signals,
            }

        if any(c in CHECKMARK_AND_STATUS_SYMBOLS for c in name) or name_lower in QUALIFICATION_AND_REQUIREMENT_WORDS:
            signals.append("qualification_noise")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 0.95,
                "reason": f"Qualification checkbox noise: {name}",
                "signals": signals,
            }

        # Check notification / feed noise
        # Check notification / feed / CTA noise
        NOISE_PATTERNS = [
            r"^\d+\s+(?:new|unread|notification|update|result)",
            r"(?:accepted your|sent you|shared a|reacted to|messaged you)",
            r"^(?:sign in|join now|log in|sign up|create account)",
            r"^(?:see all|show more|load more|view all|more results)",
            r"^(?:cookie|privacy|terms|disclaimer|all rights reserved)",
            r"^(?:unlock|discover|explore|learn more|get started|try|start|find out|check out)\b.{5,}",
            r"^(?:insights? on|overview of|about us|who we are)\b",
            r"^(?:sponsored|promoted|advertisement|ad)\b",
            r"^(?:subscribe|follow us|join our|stay updated)\b",
            r"^(?:trending|popular|recommended for you)\b",
            r"^(?:upgrade to|switch to|try sales navigator|try premium)\b",
            r"^(?:feed post|more groups|people also viewed|people you may know)\b",
            r"^(?:add to|remove from|save to|bookmark)\b",
            r"\b(?:current openings|job openings|career opportunities|latest openings)\b",
            # Chat presence, activity status & system indicators
            r"\b(?:status is (?:offline|online|away|busy|available|dnd|inactive)|active (?:now|\d+m ago)|(?:last|recently) seen)\b",
            # Social / company profile counts & aggregated indicators
            r"^\d+\s+(?:associated\s+members?|employees?|alumni|followers?|connections?|members?)\b",
        ]
        for pat in NOISE_PATTERNS:
            if re.search(pat, name_lower):
                signals.append(f"noise_pattern:{pat}")
                return {
                    "entity_type": ENTITY_NOISE,
                    "confidence": 0.95,
                    "reason": f"Name matches noise pattern: {name}",
                    "signals": signals,
                }

        # Check for names that are too long to be a person or company (likely sentences/descriptions)
        # Market signals can be 6-7 words (e.g. 'Tech Hiring Surge in Q3 2026')
        word_count = len(name.split())
        if word_count >= 8:
            signals.append("sentence_length_name")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 0.90,
                "reason": f"Name is too long ({word_count} words), likely a description: {name}",
                "signals": signals,
            }

        # Check for URL / domain / search snippet noise
        if re.search(r"(?:https?://|www\.|httpswww|\.com/|\.org/|\.net/|\.io/|zhihu\.com|youtube\.com|instagram\.com|justanswer\.com|microsoft\.com|hindustantimes)", name_lower):
            signals.append("url_or_web_snippet_noise")
            return {
                "entity_type": ENTITY_NOISE,
                "confidence": 1.0,
                "reason": f"Name contains URL or search snippet artifacts: {name}",
                "signals": signals,
            }

        return None

    def _check_company(
        self,
        name: str,
        name_lower: str,
        title: str,
        title_lower: str,
        company: str,
        email: str,
        url: str,
        page_title: str,
        signals: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Detect company/organization entities."""
        tokens = [re.sub(r"[^a-zA-Z0-9]", "", tok).lower() for tok in name.split() if tok]

        has_biz_marker = (
            any(tok in COMMERCIAL_LEGAL_AND_BIZ_MARKERS for tok in tokens)
            or bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|solutions|services|group|partners|associates|holdings|labs|ventures|consulting|agency|capital|systems|analytics)\b", name_lower))
        )

        # GUARD: If the name is definitively a valid human name and does NOT have explicit corporate markers,
        # it cannot be a company even if viewed on a company page / feed!
        c_name = clean_person_name(name)
        if c_name and is_valid_person_name(c_name) and not has_biz_marker and name_lower not in KNOWN_STANDALONE_CORPS:
            return None

        confidence = 0.0
        reasons = []

        # Signal 1: Name matches known company or has commercial markers
        if has_biz_marker and is_valid_company_name(name):
            confidence += 0.50
            reasons.append("has commercial business designators")
            signals.append("company_markers")

        if name_lower in KNOWN_STANDALONE_CORPS:
            confidence += 0.60
            reasons.append(f"known corporate enterprise brand: {name}")
            signals.append("known_standalone_corp")

        # Signal 2: Source URL is a company page
        if url and ("/company/" in url or "/school/" in url):
            confidence += 0.30
            reasons.append("URL is /company/ or /school/ path")
            signals.append("company_url")

        # Signal 3: Page title indicates company page
        if page_title and any(p in page_title for p in [": overview", ": people", ": jobs", ": life", ": about", "company profile", "about us", "our team", "leadership team"]):
            confidence += 0.20
            reasons.append("page title indicates company profile")
            signals.append("company_page_title")

        # Signal 4: Title is an industry descriptor
        if title and is_company_industry(title):
            confidence += 0.20
            reasons.append("title is industry descriptor")
            signals.append("industry_title")

        # Signal 5: Generic role email address
        if email:
            local_part = email.split("@")[0] if "@" in email else ""
            if local_part.lower() in GENERIC_EMAIL_PREFIXES:
                confidence += 0.20
                reasons.append(f"generic role email: {local_part}")
                signals.append("generic_email")

        # Signal 6: Name contains TLD
        if re.search(r"\.(com|net|org|io|co|biz|info|edu|gov)\b", name_lower):
            confidence += 0.35
            reasons.append("name contains web TLD")
            signals.append("tld_in_name")

        if confidence >= 0.40:
            return {
                "entity_type": ENTITY_COMPANY,
                "confidence": min(confidence, 1.0),
                "reason": "; ".join(reasons),
                "signals": signals,
            }

        return None

    def _check_job_posting(
        self,
        name: str,
        name_lower: str,
        title: str,
        title_lower: str,
        url: str,
        page_title: str,
        signals: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Detect job posting / requisition entities."""
        confidence = 0.0
        reasons = []

        if is_job_posting_title(name_lower):
            confidence += 0.55
            reasons.append(f"name is a job posting title: {name}")
            signals.append("job_title_as_name")

        JOB_URL_PATTERNS = ["/jobs/", "/job/", "/career", "/vacancy", "/opening", "/apply/", "/position/"]
        if url and any(p in url for p in JOB_URL_PATTERNS):
            confidence += 0.30
            reasons.append("URL indicates job requisition page")
            signals.append("job_url")

        if page_title and any(p in page_title for p in ["job listing", "job opening", "career opportunity", "hiring", "apply now", "job description", "job details"]):
            confidence += 0.20
            reasons.append("page title indicates job listing")
            signals.append("job_page_title")

        JOB_KEYWORDS = ["hiring", "we are hiring", "now hiring", "job opening", "vacancy", "position available", "apply now", "immediate opening"]
        if any(kw in name_lower for kw in JOB_KEYWORDS):
            confidence += 0.35
            reasons.append("name contains hiring keywords")
            signals.append("hiring_keywords")

        if confidence >= 0.40:
            return {
                "entity_type": ENTITY_JOB_POSTING,
                "confidence": min(confidence, 1.0),
                "reason": "; ".join(reasons),
                "signals": signals,
            }

        return None

    def _check_contact_info(
        self,
        name: str,
        name_lower: str,
        title_lower: str,
        email: str,
        phone: Optional[str],
        url: str,
        signals: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Detect generic contact information entries."""
        confidence = 0.0
        reasons = []

        if name_lower in GENERIC_CONTACT_NAMES:
            confidence += 0.50
            reasons.append(f"generic contact name: {name}")
            signals.append("generic_contact_name")

        if title_lower in ("contact", "contact us", "general contact", "main contact", "office contact"):
            confidence += 0.25
            reasons.append("generic contact title")
            signals.append("generic_contact_title")

        if (email or phone) and confidence > 0:
            confidence += 0.15
            reasons.append("contact channels present with generic label")
            signals.append("contact_with_generic_identity")

        if url and any(p in url for p in ["/contact", "/reach-us", "/get-in-touch"]):
            confidence += 0.15
            reasons.append("contact page URL")
            signals.append("contact_url")

        if confidence >= 0.40:
            return {
                "entity_type": ENTITY_CONTACT_INFO,
                "confidence": min(confidence, 1.0),
                "reason": "; ".join(reasons),
                "signals": signals,
            }

        return None

    def _check_market_signal(
        self,
        name: str,
        name_lower: str,
        title: str,
        title_lower: str,
        url: str,
        page_title: str,
        signals: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Detect market intelligence and industry trend entities."""
        confidence = 0.0
        reasons = []

        SIGNAL_PATTERNS = [
            r"hiring\s+(?:\d+|surge|trend|freeze|spree)",
            r"(?:layoffs?|restructuring|downsizing|expansion)",
            r"(?:market\s+(?:report|analysis|trend|outlook))",
            r"(?:industry\s+(?:report|analysis|trend|outlook|news))",
            r"(?:salary\s+(?:survey|data|report|guide))",
            r"(?:workforce\s+(?:report|trend|data|planning))",
        ]
        for pat in SIGNAL_PATTERNS:
            if re.search(pat, name_lower):
                confidence += 0.45
                reasons.append("matches market signal phrase")
                signals.append(f"signal_pattern:{pat}")
                break

        if page_title and any(p in page_title for p in ["press release", "news", "blog", "report", "whitepaper", "research"]):
            confidence += 0.15
            reasons.append("news/report page title")
            signals.append("news_page")

        if confidence >= 0.40:
            return {
                "entity_type": ENTITY_MARKET_SIGNAL,
                "confidence": min(confidence, 1.0),
                "reason": "; ".join(reasons),
                "signals": signals,
            }

        return None


# Singleton instance
desktop_entity_classifier = DesktopEntityTypeClassifier()
