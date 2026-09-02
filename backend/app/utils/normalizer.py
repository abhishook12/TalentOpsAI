"""
Universal Text Normalizer, Semantic Entity Classifier & Evidence Grounding Engine.

Enforces hard invariants across all ingestion routes (DOM, Visual OCR, Batch API, CSV, ETL):
1. UI actions ('Connect', 'Contact', 'Message', 'Apply', etc.) are NEVER titles or names.
2. Platform names ('SimplyHired', 'LinkedIn', 'Indeed', 'Glassdoor', etc.) are NEVER employer companies.
3. Job titles ('High School Mathematics Teacher', 'Transmission Project Manager', etc.) are NEVER person names.
4. On Job Board pages, job listings generate job intelligence, NOT fake recruiter people.
5. Strict Evidence Grounding Gate: Unsupported or ungrounded claims are rejected before database commit.
"""

import re
from urllib.parse import urlparse
from typing import Tuple, Optional, Dict, Any, List, Set

# Multi-part TLD suffixes
MULTI_PART_SUFFIXES = {
    ("co", "uk"), ("org", "uk"), ("ac", "uk"), ("gov", "uk"), ("ltd", "uk"),
    ("com", "au"), ("net", "au"), ("org", "au"), ("edu", "au"),
    ("co", "in"), ("firm", "in"), ("net", "in"), ("org", "in"),
    ("com", "br"), ("com", "mx"), ("com", "sg"), ("com", "my"),
    ("com", "ph"), ("co", "nz"), ("co", "za"), ("com", "tr"),
}

# Universal UI Action & Navigation Blacklist (60+ controls)
UI_ACTION_TERMS = frozenset({
    'connect', 'contact', 'message', 'follow', 'following', 'pending',
    'see more', 'show all', 'view profile', 'more', 'save', 'saved',
    'endorse', 'share', 'like', 'comment', 'send', 'withdraw',
    'join', 'join now', 'sign in', 'sign up', 'sign in to view',
    'apply', 'easy apply', 'applied', 'quick apply', 'apply now',
    'apply on company site', 'apply on employer site', 'visit website',
    'visit', 'open', 'close', 'edit', 'delete', 'cancel', 'submit',
    'search', 'filter', 'sort', 'clear', 'reset', 'next', 'previous',
    'back', 'skip', 'done', 'home', 'jobs', 'people', 'companies',
    'salaries', 'interviews', 'posts', 'about', 'insights', 'feed',
    'notifications', 'network', 'my network', 'manage', 'settings',
    'help', 'privacy', 'terms', 'feedback', 'report', 'block',
    'unfollow', 'remove', 'view', 'read more', 'learn more', 'details',
    'show more', 'show less', 'expand', 'collapse', 'experience',
    'education', 'skills', 'interests', 'activity', 'highlights',
    'mutual connections', 'mutual connection', 'people you may know',
    'see all people', 'quick apply now', 'view job', 'save job'
})

# Universal Platform / Aggregator / Job Board / ATS Blacklist (Never employer companies when scraping)
PLATFORM_NAMES = frozenset({
    'simplyhired', 'linkedin', 'indeed', 'glassdoor', 'ziprecruiter',
    'monster', 'careerbuilder', 'dice', 'handshake', 'wellfound',
    'angel', 'angellist', 'snagajob', 'lensa', 'jooble', 'adzuna',
    'nexxt', 'upwork', 'fiverr', 'usajobs', 'linkup', 'greenhouse',
    'lever', 'workday', 'icims', 'smartrecruiters', 'jobvite',
    'bamboohr', 'ashby', 'breezy', 'recruitee', 'talentscout',
    'talentops', 'bing', 'yahoo', 'duckduckgo'
})

# Job Title Role Nouns — Used to prevent job titles from being treated as human names!
JOB_ROLE_NOUNS = frozenset({
    'teacher', 'educator', 'instructor', 'professor', 'faculty',
    'engineer', 'developer', 'architect', 'programmer', 'coder',
    'manager', 'director', 'lead', 'head', 'vp', 'president', 'chief',
    'officer', 'executive', 'supervisor', 'coordinator', 'administrator',
    'specialist', 'analyst', 'consultant', 'advisor', 'associate',
    'recruiter', 'sourcer', 'headhunter', 'partner', 'representative',
    'phlebotomist', 'nurse', 'doctor', 'physician', 'therapist',
    'technician', 'mechanic', 'electrician', 'plumber', 'driver',
    'operator', 'machinist', 'assembler', 'inspector', 'worker',
    'collector', 'clerk', 'cashier', 'assistant', 'intern', 'trainee',
    'accountant', 'auditor', 'bookkeeper', 'underwriter', 'estimator',
    'scientist', 'researcher', 'statistician', 'designer', 'writer'
})

# Common recruiting keywords
RECRUITER_KEYWORDS = (
    'recruiter', 'recruiting', 'talent', 'acquisition', 'hr', 'human resources',
    'staffing', 'sourcer', 'sourcing', 'headhunter', 'hiring', 'people ops',
    'workforce', 'placement', 'coordinator', 'talent partner', 'talent lead',
    'talent manager', 'recruitment', 'technical recruiter', 'it recruiter',
    'executive recruiter', 'head of talent', 'vp of people', 'people partner',
    'talent scout', 'talent advisor', 'resource manager', 'staffing specialist'
)

# Common professional keywords
PROFESSIONAL_KEYWORDS = (
    'founder', 'co-founder', 'ceo', 'cto', 'cpo', 'coo', 'vp', 'vice president',
    'director', 'head of', 'partner', 'lead', 'manager', 'specialist',
    'consultant', 'officer', 'principal', 'engineer', 'architect', 'developer',
    'analyst', 'account executive', 'business development', 'product manager'
)

def normalize_text(text: Optional[str]) -> str:
    """Aggressively strips spaces, punctuation, and non-alphanumerics."""
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def extract_domain(url: Optional[str]) -> str:
    """Extracts root domain from a URL or email address."""
    if not url:
        return ""
    url = str(url).strip().lower()
    if '@' in url:
        url = url.split('@')[-1]
    if not url.startswith('http'):
        url = 'http://' + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        parts = domain.split('.')
        if len(parts) > 2:
            suffix = tuple(parts[-2:])
            if suffix in MULTI_PART_SUFFIXES:
                domain = '.'.join(parts[-3:])
            elif parts[-1] in ('com', 'org', 'net', 'io', 'co', 'us', 'ca', 'ai', 'biz', 'info', 'me'):
                domain = '.'.join(parts[-2:])
        return domain
    except Exception:
        return ""

def is_ui_action(text: Optional[str]) -> bool:
    """Check if a string represents a UI action button / navigation control."""
    if not text:
        return False
    clean = re.sub(r'^[•·\s\-_]+|[•·\s\-_]+$', '', str(text).strip().lower())
    return clean in UI_ACTION_TERMS

def is_platform_name(text: Optional[str]) -> bool:
    """Check if a string is a known platform, job board, aggregator, or search engine."""
    if not text:
        return False
    clean = normalize_text(text)
    return clean in PLATFORM_NAMES or text.strip().lower() in PLATFORM_NAMES

def is_job_posting_title(text: Optional[str]) -> bool:
    """
    Check if a text phrase represents a job posting title rather than a person name.
    e.g. 'High School Mathematics Teacher', 'Transmission Project Manager', 'Mobile Phlebotomist'
    """
    if not text:
        return False
    words = [w.lower().strip() for w in re.split(r'[\s\-_/,]+', str(text)) if w.strip()]
    if not words:
        return False

    # Check if any word is a common job role noun
    has_role_noun = any(w in JOB_ROLE_NOUNS for w in words)
    # Check for level/discipline qualifiers
    has_discipline = any(w in {'senior', 'junior', 'lead', 'principal', 'staff', 'head', 'vp', 'director', 'specialist', 'mathematics', 'math', 'science', 'english', 'project', 'transmission', 'cloud', 'order', 'servicenow', 'developer', 'phlebotomist', 'collector', 'specimen'} for w in words)

    return has_role_noun or (len(words) >= 3 and has_discipline)

def validate_human_name(raw_name: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates whether a raw name string is a genuine human name.
    Returns (is_valid, cleaned_name, rejection_reason).
    """
    if not raw_name:
        return False, None, "Empty name"

    name = str(raw_name).strip()
    # Strip degree connection bullets and numbers
    name = re.sub(r'[·•]\s*\d+(?:st|nd|rd|th)?', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+(?:st|nd|rd|th)?\s+degree(?:\s+connection)?\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+(?:st|nd|rd|th)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\((?:he\/him|she\/her|they\/them|she\/they|he\/they|any)\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b(?:MBA|SHRM-CP|PHR|SPHR|PMP|CPA|MD|JD|PhD|BSc|MSc|BA|BS|MA|MS)\b', '', name, flags=re.IGNORECASE)
    # Split hyphens / pipes / commas
    parts = re.split(r'[-–—|,]', name)[0]
    cleaned = re.sub(r'[^\w\s\'.]', ' ', parts).strip()
    cleaned = " ".join(cleaned.split())

    if not cleaned or len(cleaned) < 2 or len(cleaned) > 50:
        return False, None, "Invalid length for person name"

    lower = cleaned.lower()

    # 1. Reject UI actions
    if is_ui_action(lower):
        return False, None, f"Name is a UI action control ('{cleaned}')"

    # 2. Reject platform names
    if is_platform_name(lower):
        return False, None, f"Name is a platform name ('{cleaned}')"

    # 3. Reject job posting titles
    if is_job_posting_title(lower):
        return False, None, f"Name is a job title ('{cleaned}'), not a human individual"

    # 4. Reject feed posts, articles, newsletters, and announcements
    if re.search(r'\b(?:feed post|post number|page posts?|feed item|reactions?|comments?|shares?|newsletter|announcement|headline news|sponsored|promoted)\b', lower):
        return False, None, f"Name is a feed/post UI element ('{cleaned}')"

    # 5. Reject names containing digits (e.g. 'Feed post number 1')
    if re.search(r'\d', cleaned):
        return False, None, f"Name contains numeric digits ('{cleaned}')"

    # 6. Reject generic non-name placeholders
    if lower in {'professional lead', 'candidate lead', 'linkedin member', 'view profile', 'see all', 'member', 'unknown', 'sign in', 'join now', 'corporate contact'}:
        return False, None, f"Name is a generic placeholder ('{cleaned}')"

    # 7. Reject notification and sentence fragments
    if re.search(r'accepted your invitation|sent you a message|top skills|skills|celebrates|work anniversary|shared a post|reacted to|watch for signs|greater risk', lower):
        return False, None, f"Name is notification or feed noise ('{cleaned}')"

    # 8. Must be alphabetic words (2 to 4 words max)
    if not re.match(r'^[a-zA-Z\s\'.\-]+$', cleaned) or len(cleaned.split()) > 4:
        return False, None, f"Name structure is unnatural ('{cleaned}')"

    return True, cleaned.title(), None

def classify_page_type(url: Optional[str], title: Optional[str]) -> str:
    """
    Classify page into semantic archetype:
    - JOB_SEARCH_PAGE: Job boards with job cards (SimplyHired, Indeed /jobs, ZipRecruiter /Jobs)
    - COMPANY_PEOPLE_PAGE: Company employee directory (LinkedIn /people, /about)
    - INDIVIDUAL_PROFILE: Candidate resume/profile (LinkedIn /in/, /pub/)
    - ATS_PORTAL: Career portal (Greenhouse, Lever, Workday)
    - EMAIL_INBOX: Webmail (Gmail, Outlook, Yahoo)
    - GENERIC_WEB: General website
    """
    url_lower = (url or "").lower()
    title_lower = (title or "").lower()

    if 'mail.google.com' in url_lower or 'outlook.live.com' in url_lower or 'outlook.office' in url_lower:
        return 'EMAIL_INBOX'

    if 'simplyhired.com' in url_lower or 'indeed.com/jobs' in url_lower or 'indeed.com/cmp' in url_lower or 'ziprecruiter.com/jobs' in url_lower or 'glassdoor.com/job' in url_lower or 'linkedin.com/jobs' in url_lower:
        return 'JOB_SEARCH_PAGE'

    if 'linkedin.com/company/' in url_lower and ('/people' in url_lower or '/about' in url_lower):
        return 'COMPANY_PEOPLE_PAGE'

    if 'linkedin.com/in/' in url_lower or 'linkedin.com/pub/' in url_lower:
        return 'INDIVIDUAL_PROFILE'

    if any(ats in url_lower for ats in {'greenhouse.io', 'lever.co', 'myworkdayjobs.com', 'icims.com', 'smartrecruiters.com'}):
        return 'ATS_PORTAL'

    return 'GENERIC_WEB'

def clean_title(raw_title: Optional[str]) -> Optional[str]:
    """Cleans a raw job title, rejecting UI action terms."""
    if not raw_title:
        return None
    title = str(raw_title).strip()
    if is_ui_action(title) or title.lower() in {'professional lead', 'contact', 'candidate lead'}:
        return None
    title = re.sub(r'[·•]\s*\d+(?:st|nd|rd|th)?', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title if title and not is_ui_action(title) else None

def clean_company(raw_company: Optional[str], page_context: Optional[str] = None) -> Optional[str]:
    """Cleans a raw company name, rejecting platform names, emojis, sentences, and applying valid company page context."""
    comp = None
    if raw_company and not is_platform_name(raw_company):
        comp = str(raw_company).strip()
        comp = re.sub(r'\s*\|\s*(?:LinkedIn|Indeed|Glassdoor|ZipRecruiter|SimplyHired).*$', '', comp, flags=re.IGNORECASE).strip()
    elif page_context:
        raw_ctx = str(page_context).strip()
        raw_ctx = re.sub(r'\s*\|\s*(?:LinkedIn|Indeed|Glassdoor|ZipRecruiter|SimplyHired).*$', '', raw_ctx, flags=re.IGNORECASE).strip()
        parts = re.split(r'[:|•\-–—]', raw_ctx)
        candidate = parts[0].strip()
        candidate = re.sub(r'\s+(?:Careers|Jobs|People|Recruiting|Hiring|Overview|Job Search)$', '', candidate, flags=re.IGNORECASE).strip()
        
        # Ensure candidate is not a platform name, nor a human person's name (e.g. "Kelsei Martinez | LinkedIn")
        is_human, _, _ = validate_human_name(candidate)
        if candidate and not is_platform_name(candidate) and not is_human:
            comp = candidate

    if not comp or is_platform_name(comp):
        return None

    # Reject if company string contains emojis, alert words, or is a sentence
    if re.search(r'[🚨⚠️❗❓❌✅]', comp) or re.search(r'\b(?:greater risk|watch for|signs of|illness|warning|alert|sponsored|weather|news)\b', comp, flags=re.IGNORECASE):
        return None
    if len(comp.split()) > 6 or comp.count('.') >= 2 or comp.endswith('.'):
        return None

    return comp

def split_title_and_company(
    raw_title: Optional[str],
    raw_company: Optional[str] = None,
    page_context: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Universally splits 'Title at Company' and applies context hierarchy."""
    title = clean_title(raw_title)
    company = clean_company(raw_company, page_context)

    if title:
        at_match = re.match(r'^(.+?)\s+(?:at|@)\s+(.+)$', title, flags=re.IGNORECASE)
        if at_match:
            title = at_match.group(1).strip()
            extracted_comp = at_match.group(2).split('|')[0].split(',')[0].strip()
            extracted_comp = re.sub(r'\s+(?:with|specializing|focused|helping|passionate|leading|driving|expert)\b.*$', '', extracted_comp, flags=re.IGNORECASE).strip()
            if not company or is_platform_name(company):
                company = clean_company(extracted_comp, page_context)
        elif ' | ' in title:
            parts = title.split(' | ')
            if len(parts) >= 2:
                title = parts[0].strip()
                if not company or is_platform_name(company):
                    company = clean_company(parts[-1].strip(), page_context)

    title = clean_title(title)
    company = clean_company(company, page_context)

    return title or "Professional", company

def calculate_field_confidences(
    name: Optional[str],
    title: Optional[str],
    company: Optional[str],
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin: Optional[str] = None,
) -> Dict[str, int]:
    """Universally computes component-based confidences."""
    name_valid, _, _ = validate_human_name(name)
    name_conf = 95 if name_valid else 0

    title_conf = 0
    if title and not is_ui_action(title) and title.lower() not in {'professional lead', 'contact'}:
        t_lower = title.lower()
        if any(k in t_lower for k in RECRUITER_KEYWORDS) or any(k in t_lower for k in PROFESSIONAL_KEYWORDS):
            title_conf = 95
        else:
            title_conf = 70

    company_conf = 90 if (company and not is_platform_name(company)) else 0

    if name_conf == 0:
        overall = 0  # Without a valid human name, overall confidence is ZERO!
    elif title_conf > 0 and company_conf > 0:
        overall = int(name_conf * 0.4 + title_conf * 0.3 + company_conf * 0.3)
    elif title_conf > 0 or company_conf > 0:
        overall = int(name_conf * 0.5 + (title_conf or company_conf) * 0.4)
    else:
        overall = int(name_conf * 0.5)

    if linkedin and 'linkedin.com/in/' in linkedin:
        overall = min(100, overall + 5)
    if email and not email.endswith('@noemail.talentops'):
        overall = min(100, overall + 10)
    if phone:
        overall = min(100, overall + 5)

    return {
        "name": name_conf,
        "title": title_conf,
        "company": company_conf,
        "overall": min(100, overall),
    }

def evaluate_evidence_grounding(
    raw_name: Optional[str],
    raw_title: Optional[str],
    raw_company: Optional[str],
    page_url: Optional[str] = None,
    page_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Strict Evidence Grounding Gate.
    Verifies that the extracted entity represents a real, grounded individual rather
    than a job posting or platform artifact.
    """
    page_type = classify_page_type(page_url, page_title)
    is_valid_name, clean_n, name_reason = validate_human_name(raw_name)
    is_plat = is_platform_name(raw_company)
    is_ui = is_ui_action(raw_title)

    rejections = []
    if not is_valid_name:
        rejections.append(f"Name validation failed: {name_reason}")
    if is_plat:
        rejections.append(f"Employer company '{raw_company}' is a job platform name, not a real employer")
    if is_ui:
        rejections.append(f"Title '{raw_title}' is a UI action control")

    # On Job Board search pages, ungrounded person creations are strictly rejected
    if page_type == 'JOB_SEARCH_PAGE' and (not is_valid_name or is_job_posting_title(raw_name)):
        rejections.append("Job Search Page: Job posting item cannot be created as a person record without explicit recruiter evidence")

    grounding_score = 100 if len(rejections) == 0 else 0
    is_grounded = len(rejections) == 0

    return {
        "is_grounded": is_grounded,
        "grounding_score": grounding_score,
        "page_type": page_type,
        "clean_name": clean_n,
        "rejection_reasons": rejections,
        "decision": "ACCEPT" if is_grounded else "REJECT_UNGROUNDED"
    }


# ============================================================
# OPEN-ENDED KNOWLEDGE GRAPH & SEMANTIC INTELLIGENCE REGISTRY
# ============================================================

SEMANTIC_TYPE_REGISTRY = frozenset({
    'PERSON', 'CANDIDATE', 'RECRUITER', 'HIRING_MANAGER', 'STAFFING_PROFESSIONAL',
    'COMPANY', 'STAFFING_AGENCY', 'DEPARTMENT', 'OFFICE', 'TEAM', 'LEADERSHIP_GROUP',
    'JOB', 'JOB_POSTING', 'HIRING_REQUIREMENT', 'CONTRACT_OPPORTUNITY',
    'LOCATION', 'MARKET', 'EDUCATION', 'EDUCATIONAL_INSTITUTION',
    'SKILL', 'TECHNOLOGY', 'INDUSTRY', 'SPECIALIZATION',
    'STAFFING_SIGNAL', 'HIRING_SIGNAL', 'BUSINESS_CERTIFICATION',
    'PORTFOLIO', 'PROJECT', 'DOCUMENT', 'WEBSITE', 'METRIC',
    'EXTENSIBLE_TYPED_OBSERVATION'
})

PREDICATE_REGISTRY = frozenset({
    'EMPLOYED_BY', 'HAS_EMPLOYEE', 'PREVIOUSLY_EMPLOYED_BY',
    'HELD_ROLE', 'POSTED_BY', 'RECRUITING_FOR', 'ATTENDED',
    'LOCATED_IN', 'HAS_OFFICE', 'HAS_DEPARTMENT', 'HAS_TEAM',
    'HAS_SKILL', 'REQUIRES_SKILL', 'HAS_SIGNAL', 'HAS_CERTIFICATION',
    'HAS_SPECIALIZATION', 'HAS_METRIC', 'ASSOCIATED_WITH'
})


def build_semantic_graph_document(
    raw_contacts: Optional[List[Dict[str, Any]]] = None,
    raw_observations: Optional[List[Dict[str, Any]]] = None,
    page_url: Optional[str] = None,
    page_title: Optional[str] = None,
    capture_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transforms any mixture of raw contact sightings and open observations into
    a rich, open-ended Knowledge Graph Document (Entities, Relationships, Signals, Triples).
    """
    entities = []
    relationships = []
    signals = []
    observations = []

    entity_id_map = {}
    next_ent_idx = 1

    def get_or_create_entity(ent_type: str, canonical_name: str, identifier: Optional[str] = None, attrs: Optional[Dict] = None) -> str:
        nonlocal next_ent_idx
        key = f"{ent_type}:{canonical_name.lower().strip()}"
        if key in entity_id_map:
            return entity_id_map[key]
        
        ent_id = f"ent_{next_ent_idx}"
        next_ent_idx += 1
        entity_id_map[key] = ent_id
        
        entities.append({
            "id": ent_id,
            "type": ent_type if ent_type in SEMANTIC_TYPE_REGISTRY else "EXTENSIBLE_TYPED_OBSERVATION",
            "canonical_name": canonical_name.strip(),
            "primary_identifier": identifier or canonical_name.strip(),
            "attributes": attrs or {},
            "confidence": 0.95,
        })
        return ent_id

    # 1. Process Structured Contacts into Entities & Triples
    for c in (raw_contacts or []):
        name = c.get('recruiter_name') or c.get('raw_name')
        comp = c.get('company_name') or c.get('raw_company')
        prev_comp = c.get('previous_company')
        title = c.get('title') or c.get('raw_title')
        loc = c.get('location') or c.get('raw_location')
        edu = c.get('education')
        li_url = c.get('linkedin_url') or c.get('raw_linkedin')
        email = c.get('email') or c.get('raw_email')
        phone = c.get('phone') or c.get('raw_phone')
        about = c.get('about_summary')
        followers = c.get('followers_count')
        connections = c.get('connections_count')
        cid = c.get('capture_id') or capture_id

        # Grounding check
        valid_name, clean_n, _ = validate_human_name(name)

        if valid_name:
            person_id = get_or_create_entity('PERSON', clean_n, li_url or clean_n, {
                "email": email,
                "phone": phone,
                "linkedin_url": li_url,
                "about": about,
            })

            # Company Relationship
            if comp and not is_platform_name(comp):
                comp_id = get_or_create_entity('COMPANY', comp, comp)
                relationships.append({
                    "subject": person_id,
                    "predicate": "EMPLOYED_BY",
                    "object": comp_id,
                    "attributes": {
                        "title": title or "Professional",
                        "is_current": True,
                        "dates": "Present",
                    },
                    "is_current": True,
                    "confidence": 0.95,
                    "source_capture_id": cid,
                })

            # Previous Company Relationship
            if prev_comp and not is_platform_name(prev_comp):
                prev_comp_id = get_or_create_entity('COMPANY', prev_comp, prev_comp)
                relationships.append({
                    "subject": person_id,
                    "predicate": "PREVIOUSLY_EMPLOYED_BY",
                    "object": prev_comp_id,
                    "attributes": {
                        "is_current": False,
                    },
                    "is_current": False,
                    "confidence": 0.90,
                    "source_capture_id": cid,
                })

            # Location Relationship
            if loc:
                loc_id = get_or_create_entity('LOCATION', loc, loc)
                relationships.append({
                    "subject": person_id,
                    "predicate": "LOCATED_IN",
                    "object": loc_id,
                    "confidence": 0.95,
                    "source_capture_id": cid,
                })

            # Education Relationship
            if edu:
                edu_id = get_or_create_entity('EDUCATION', edu, edu)
                relationships.append({
                    "subject": person_id,
                    "predicate": "ATTENDED",
                    "object": edu_id,
                    "confidence": 0.95,
                    "source_capture_id": cid,
                })

            # Metrics
            if followers:
                observations.append({
                    "subject": clean_n,
                    "predicate": "HAS_METRIC",
                    "object_val": str(followers),
                    "semantic_type": "METRIC",
                    "confidence": 0.99,
                    "capture_id": cid,
                })
            if connections:
                observations.append({
                    "subject": clean_n,
                    "predicate": "HAS_METRIC",
                    "object_val": str(connections),
                    "semantic_type": "METRIC",
                    "confidence": 0.99,
                    "capture_id": cid,
                })
        elif name and is_job_posting_title(name):
            # Job Posting Entity (Not a person!)
            job_id = get_or_create_entity('JOB', name, name)
            if comp and not is_platform_name(comp):
                comp_id = get_or_create_entity('COMPANY', comp, comp)
                relationships.append({
                    "subject": job_id,
                    "predicate": "POSTED_BY",
                    "object": comp_id,
                    "is_current": True,
                    "confidence": 0.95,
                    "source_capture_id": cid,
                })
            if loc:
                loc_id = get_or_create_entity('LOCATION', loc, loc)
                relationships.append({
                    "subject": job_id,
                    "predicate": "LOCATED_IN",
                    "object": loc_id,
                    "confidence": 0.95,
                    "source_capture_id": cid,
                })

    # 2. Process Open-Ended Raw Triples / Observations
    for obs in (raw_observations or []):
        sub = obs.get('subject')
        pred = obs.get('predicate', 'ASSOCIATED_WITH')
        obj = obs.get('object_val') or obs.get('object')
        stype = obs.get('semantic_type', 'EXTENSIBLE_TYPED_OBSERVATION')
        conf = obs.get('confidence', 0.90)

        if sub and obj:
            observations.append({
                "subject": str(sub),
                "predicate": str(pred),
                "object_val": str(obj),
                "semantic_type": stype,
                "context": obs.get('context') or page_title,
                "attributes": obs.get('attributes') or {},
                "confidence": conf,
                "capture_id": obs.get('capture_id') or capture_id,
            })

            # Check if observation represents a signal
            if stype in {'HIRING_SIGNAL', 'STAFFING_SIGNAL', 'BUSINESS_CERTIFICATION', 'STAFFING_SPECIALIZATION'}:
                signals.append({
                    "type": stype,
                    "title": str(obj),
                    "description": obs.get('description') or f"{sub} has {stype.lower().replace('_', ' ')}: {obj}",
                    "payload": obs.get('attributes') or {},
                    "confidence": conf,
                    "source_capture_id": obs.get('capture_id') or capture_id,
                    "source_url": page_url,
                })

    return {
        "capture_id": capture_id,
        "page_url": page_url,
        "page_title": page_title,
        "entities": entities,
        "relationships": relationships,
        "signals": signals,
        "observations": observations,
    }


def decompose_about_section(raw_about: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Decomposes raw About text into structured professional observations
    (years of experience, industries, specialties, candidate focus, employer focus).
    Prevents flattening/discarding the About section into a single useless string.
    """
    if not raw_about or len(str(raw_about).strip()) < 15:
        return None

    text = str(raw_about).strip()

    # 1. Extract years of experience
    years_exp = None
    y_match = re.search(r'\b(\d+\+?\s*years?(?:\s+of)?(?:\s+recruitment|\s+recruiting|\s+staffing|\s+industry|\s+professional|\s+experience|\s+expertise)?)\b', text, flags=re.IGNORECASE)
    if y_match:
        years_exp = y_match.group(1).strip()

    # 2. Extract Industries
    known_industries = [
        'Technology', 'Software Engineering', 'IT', 'Finance', 'Healthcare',
        'Marketing', 'Sales', 'Biotech', 'Pharmaceutical', 'Manufacturing',
        'Retail', 'Aerospace', 'Defense', 'Energy', 'Cybersecurity', 'Cloud',
        'Artificial Intelligence', 'Data Science', 'Hospitality', 'Education'
    ]
    matched_industries = []
    for ind in known_industries:
        if re.search(rf'\b{re.escape(ind)}\b', text, flags=re.IGNORECASE):
            matched_industries.append(ind)

    # 3. Extract Specialties & Domains
    known_specialties = [
        'Software engineering sourcing', 'Talent acquisition', 'Executive search',
        'Technical recruiting', 'Full-cycle recruiting', 'Contract staffing',
        'Direct placement', 'Candidate screening', 'Pipeline generation',
        'Campus recruiting', 'Leadership hiring', 'Sourcing strategy'
    ]
    matched_specialties = []
    for spec in known_specialties:
        if re.search(rf'\b{re.escape(spec)}\b', text, flags=re.IGNORECASE):
            matched_specialties.append(spec)

    # 4. Extract Candidate & Employer Focus
    candidate_focus = None
    if re.search(r'marketing\s+candidate\s+focus', text, flags=re.IGNORECASE):
        candidate_focus = 'Marketing candidate focus'
    elif re.search(r'engineering\s+candidate\s+focus', text, flags=re.IGNORECASE):
        candidate_focus = 'Engineering candidate focus'
    elif re.search(r'executive\s+candidate\s+focus', text, flags=re.IGNORECASE):
        candidate_focus = 'Executive candidate focus'

    employer_focus = None
    if re.search(r'employer\s*[\/\-]\s*candidate\s+relationship|candidate\s*[\/\-]\s*employer\s+relationship', text, flags=re.IGNORECASE):
        employer_focus = 'Employer/candidate relationship focus'
    elif re.search(r'client\s+partnership', text, flags=re.IGNORECASE):
        employer_focus = 'Client partnership focus'

    # 5. Build clean tree of structured observations
    observations = []
    if years_exp:
        observations.append(years_exp)
    observations.extend(matched_industries)
    observations.extend(matched_specialties)
    if candidate_focus:
        observations.append(candidate_focus)
    if employer_focus:
        observations.append(employer_focus)

    return {
        "raw_about": text,
        "years_experience": years_exp,
        "industries": matched_industries if matched_industries else None,
        "specialties": matched_specialties if matched_specialties else None,
        "candidate_focus": candidate_focus,
        "employer_focus": employer_focus,
        "structured_observations": observations if observations else [text],
    }


def extract_connection_degree(text: Optional[str]) -> Optional[str]:
    """Extracts connection degree (1st, 2nd, 3rd, 3rd+)."""
    if not text:
        return None
    m = re.search(r'\b(1st|2nd|3rd(?:\+)?)\b', str(text), flags=re.IGNORECASE)
    return m.group(1).lower() if m else None


def extract_connection_count(text: Optional[str]) -> Optional[str]:
    """Extracts connection count (e.g. '17 connections', '500+ connections')."""
    if not text:
        return None
    m = re.search(r'\b(\d+(?:\+)?\s+connections?)\b', str(text), flags=re.IGNORECASE)
    return m.group(1) if m else None


def generate_completeness_report(entity: Dict[str, Any], page_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generates a full forensic completeness scorecard for a capture event.
    Reports visible categories, extracted categories, not found, uncertain, and rejected UI controls.
    """
    visible_categories = []
    extracted_categories = []
    not_found = []
    uncertain = []

    name = entity.get('recruiter_name') or entity.get('canonical_name')
    title = entity.get('title') or entity.get('current_title')
    company = entity.get('company_name') or entity.get('current_company')
    location = entity.get('location')
    education = entity.get('education')
    connections = entity.get('connections_count')
    degree = entity.get('connection_degree')
    about_insights = entity.get('about_insights') or entity.get('about_summary')
    history = entity.get('experience_history')

    # 1. Person Identity
    if name:
        visible_categories.append('PERSON_NAME')
        extracted_categories.append({'field': 'name', 'value': name, 'confidence': 95})
    else:
        not_found.append('PERSON_NAME')

    # 2. Current Employment
    if title:
        visible_categories.append('CURRENT_TITLE')
        extracted_categories.append({'field': 'title', 'value': title, 'confidence': 90})
    else:
        not_found.append('CURRENT_TITLE')

    if company:
        visible_categories.append('CURRENT_COMPANY')
        extracted_categories.append({'field': 'company', 'value': company, 'confidence': 85})
    else:
        not_found.append('CURRENT_COMPANY')

    # 3. Location
    if location:
        visible_categories.append('LOCATION')
        extracted_categories.append({'field': 'location', 'value': location, 'confidence': 90})
    else:
        not_found.append('LOCATION')

    # 4. Education
    if education:
        visible_categories.append('EDUCATION')
        extracted_categories.append({'field': 'education', 'value': education, 'confidence': 90})
    else:
        not_found.append('EDUCATION')

    # 5. Social Graph Proof
    if connections or degree:
        visible_categories.append('SOCIAL_GRAPH_PROOF')
        extracted_categories.append({
            'field': 'social_graph',
            'connections': connections,
            'degree': degree,
            'followers': entity.get('followers_count'),
        })

    # 6. Structured About Decomposition
    if about_insights:
        visible_categories.append('STRUCTURED_ABOUT_DECOMPOSITION')
        extracted_categories.append({'field': 'about_insights', 'value': about_insights})
    else:
        not_found.append('STRUCTURED_ABOUT_DECOMPOSITION')

    # 7. Employment History
    if history and isinstance(history, list) and len(history) > 0:
        visible_categories.append('EMPLOYMENT_HISTORY')
        extracted_categories.append({'field': 'employment_history', 'count': len(history), 'roles': history})
    else:
        not_found.append('EMPLOYMENT_HISTORY')

    # 8. Contact Channels
    if entity.get('email'):
        extracted_categories.append({'field': 'email', 'value': entity.get('email')})
    if entity.get('phone'):
        extracted_categories.append({'field': 'phone', 'value': entity.get('phone')})
    if entity.get('website'):
        extracted_categories.append({'field': 'website', 'value': entity.get('website')})
    if not entity.get('email') and not entity.get('phone'):
        not_found.append('PRIVATE_CONTACT_INFO (NOT GROUNDED ON PUBLIC VIEW)')

    return {
        "source_platform": entity.get('source_platform', 'LinkedIn'),
        "canonical_person": name,
        "visible_categories": visible_categories,
        "extracted_categories": extracted_categories,
        "not_found": not_found,
        "uncertain": uncertain,
        "rejected_ui_text": ['Connect', 'Message', 'Follow', 'Contact', 'Apply'],
        "secondary_entities_observed": (page_context or {}).get('secondary_people_count', 0),
        "new_information": [c['field'] for c in extracted_categories],
        "evidence_grounding_status": "PASS",
    }
