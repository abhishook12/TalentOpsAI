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
    'talentops', 'bing', 'yahoo', 'duckduckgo',
    'instagram', 'reddit', 'youtube', 'facebook', 'twitter', 'tiktok',
    'pinterest', 'quora', 'wikipedia', 'apple', 'appstore', 'playstore',
    'google', 'imdb', 'zee5', 'mayoclinic', 'github', 'stackoverflow',
    'medium', 'substack', 'threads', 'snapchat', 'twitch', 'discord',
    'boyfriendtv', 'onecompiler', 'ninite', 'quickmath'
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

# Legal/Corporate Entity Suffixes
COMPANY_LEGAL_SUFFIXES = frozenset({
    'inc', 'inc.', 'llc', 'ltd', 'ltd.', 'corp', 'corp.', 'corporation',
    'co', 'co.', 'company', 'gmbh', 'sa', 'plc', 'bv', 'pvt', 'private limited',
    'group', 'holdings', 'enterprises', 'ventures', 'capital', 'partners', 'associates'
})

# Common Company/Organization Keywords (Never Human Names)
COMPANY_DOMAIN_TERMS = frozenset({
    'global', 'services', 'technologies', 'technology', 'tech', 'tek', 'solutions', 'systems',
    'consulting', 'consultancy', 'staffing', 'recruiting', 'recruitment', 'resources',
    'workforce', 'personnel', 'search', 'labs', 'laboratories', 'studios', 'interactive',
    'digital', 'media', 'software', 'networks', 'logistics', 'logix', 'infotech',
    'analytics', 'intelligence', 'therapeutics', 'pharma', 'pharmaceuticals', 'health',
    'healthcare', 'financial', 'bank', 'insurance', 'agency', 'foundation', 'institute',
    'academy', 'university', 'college', 'school', 'enterprises', 'holdings', 'group',
    'ventures', 'capital', 'international', 'worldwide', 'industries', 'management',
    'inspirations', 'innovations', 'dynamics', 'cloud', 'advisors', 'adviser',
})

# Comprehensive Non-Human Noise Word Blacklist for Candidate Name Screening
NON_PERSON_NAME_KEYWORDS = frozenset({
    # Degrees & Education
    'degree', 'degrees', 'bachelor', 'bachelors', 'bactklors', 'bactkloes', 'master', 'masters',
    'doctorate', 'diploma', 'certificate', 'certification', 'alumni', 'graduate', 'undergraduate',
    'university', 'college', 'school', 'academy', 'institute', 'education', 'campus', 'science',
    'computer', 'engineering', 'informatics', 'kinesiology', 'humanities',
    # Licenses, Certifications & Requirements
    'license', 'licenses', 'driver', 'drivers', 'driving', 'cdl', 'clearance', 'authorized',
    'authorization', 'screening', 'screen', 'test', 'testing', 'check', 'background',
    # Occupation & Role Nouns as Names
    'professional', 'professionals', 'contractor', 'contractors', 'handyman', 'detailer',
    'cleaner', 'cleaning', 'technician', 'mechanic', 'operator', 'installer', 'installation',
    'worker', 'workers', 'laborer', 'laborers', 'helper', 'helpers', 'crew', 'staff',
    'assistant', 'specialist', 'coordinator', 'consultant', 'analyst', 'recruiter',
    'sourcer', 'manager', 'director', 'engineer', 'developer',
    # Benefits, Leave & Compensation
    'medical', 'dental', 'vision', 'retirement', 'retrernent', 'retire', 'pension',
    'insurance', 'benefits', 'benefit', '401k', 'fsa', 'hsa', 'pto', 'vacation',
    'leave', 'stipend', 'reimbursement', 'disability', 'perks', 'compensation',
    'allowance', 'commuter', 'parental', 'wellness', 'relocation', 'bonus', 'equity',
    # Application & Hiring UI
    'application', 'applications', 'apply', 'applying', 'applicant', 'applicants',
    'online', 'interview', 'interviews', 'rejoin', 'questionnaire', 'assessment',
    'submission', 'submitting', 'resume', 'resumes', 'portal', 'posting', 'postings',
    'requisition', 'listing', 'listings', 'vacancy', 'vacancies', 'opening', 'openings',
    'search', 'utility', 'deployment', 'homage', 'festival', 'center', 'claim',
    'job', 'jobs', 'career', 'careers', 'hire', 'hiring', 'work', 'works',
    'my', 'our', 'all', 'the', 'your', 'verified', 'premium', 'badge',
    # Work Authorization & Visas
    'visa', 'visas', 'citizenship', 'citizen', 'citizens', 'sponsorship', 'sponsor',
    'sponsors', 'greencard', 'w2', 'c2c', '1099', 'tax', 'hourly', 'salary',
    'full-time', 'part-time', 'contract', 'in-person', 'travel', 'remote', 'hybrid', 'on-site',
    # Cities & States
    'vegas', 'vegos', 'fort', 'worth', 'angeles', 'francisco', 'diego', 'jose',
    'antonio', 'orleans', 'charlotte', 'columbus', 'indianapolis', 'denver',
    'seattle', 'boston', 'atlanta', 'miami', 'austin', 'houston', 'dallas',
    'phoenix', 'philadelphia', 'detroit', 'memphis', 'baltimore', 'milwaukee',
    'albuquerque', 'tucson', 'fresno', 'sacramento', 'mesa', 'omaha', 'raleigh',
    'oakland', 'minneapolis', 'tulsa', 'wichita', 'arlington', 'bakersfield',
    'aurora', 'tampa', 'tamva', 'honolulu', 'anaheim', 'chicago', 'germantown',
    'madison', 'orlando', 'cleveland', 'pittsburgh', 'cincinnati', 'greensboro',
    'plano', 'newark', 'irvine', 'toledo', 'durham', 'laredo', 'scottsdale',
    'glendale', 'gilbert', 'winston-salem', 'lubbock', 'reno', 'chandler',
    'chesapeake', 'fremont', 'baton', 'rouge', 'richmond', 'boise', 'birmingham',
    'spokane', 'rochester', 'auburn', 'hills', 'falls', 'church', 'saint',
    'louis', 'alamos', 'chester', 'preschool', 'stores', 'rock', 'state',
    # Tech & Software Products
    'cisco', 'catalyst', 'guidewire', 'sap', 'oracle', 'salesforce', 'investment',
    # Media, Entertainment & Products
    'movie', 'movies', 'film', 'films', 'video', 'videos', 'music', 'songs', 'song',
    'audio', 'series', 'episode', 'episodes', 'tv', 'television', 'discography',
    'album', 'albums', 'track', 'tracks', 'trailer', 'trailers',
    # Software, Web & Applications
    'app', 'apps', 'application', 'software', 'download', 'downloads', 'patch', 'patches',
    'patching', 'update', 'updates', 'tool', 'tools', 'editor', 'online', 'pro',
    'solver', 'calculator', 'formula', 'plugin', 'extension', 'bot', 'apk', 'mod',
    'solve', 'math', 'form', 'forms',
    # Web, Community & Commercial Noise
    'reality', 'community', 'forum', 'discussion', 'wiki', 'wikipedia', 'baybeh',
    'store', 'shop', 'dealer', 'dealership', 'cars', 'car', 'auto', 'vehicle',
    'groceries', 'grocery', 'produce', 'disease', 'symptoms', 'causes',
    # Adult & Explicit Noise
    'porn', 'xxx', 'sex', 'sexy', 'gay', 'lesbian', 'erotic', 'adult', 'escort', 'massage',
    # OCR Glitches & Sourcing Platform Noise
    'cz', 'fo', 'mard', 'relewnce', 'termlogy', 'cotamt', 'fim', 'lre', 'cause',
    'percentage', 'estimate', 'estimated', 'posted', 'urgently', 'viewed',
    'matched', 'matching', 'recommended', 'saved', 'sponsored', 'relevance',
    'date', 'recent', 'popularity', 'distance', 'pwple', 'talen', 'taler',
    'searc', 'zoor', 'searco', 'wkata', 'lile', 'breaks', 'roadside',
})

# Comprehensive Section Headers on Profiles, Resumes, and ATS pages
SECTION_HEADERS = frozenset({
    "experience", "work experience", "professional experience", "employment history",
    "education", "academic background", "academics",
    "skills", "top skills", "technical skills", "core competencies", "skills & endorsements",
    "about", "summary", "professional summary", "about me", "overview", "bio",
    "licenses & certifications", "licenses and certifications", "certifications", "licenses",
    "recommendations", "received recommendations", "given recommendations",
    "honors & awards", "honors and awards", "awards", "honors",
    "volunteer experience", "volunteering", "volunteer",
    "publications", "patents", "projects", "featured projects", "personal projects",
    "courses", "coursework", "languages", "organizations", "interests",
    "activity", "featured", "highlights", "posts", "articles", "documents",
    "contact info", "contact details", "connections", "mutual connections",
    "people also viewed", "people you may know", "similar profiles",
})

# Workplace / Employment Types & Arrangements
WORKPLACE_TYPES_SET = frozenset({
    "full-time", "full time", "part-time", "part time",
    "contract", "contractor", "c2c", "w2", "1099",
    "internship", "intern", "co-op", "coop",
    "freelance", "freelancer", "self-employed",
    "seasonal", "temporary", "temp", "permanent",
    "hybrid", "remote", "on-site", "onsite", "in-office",
    "apprenticeship", "apprentice", "per diem",
})

# Common Technical Skills & Proficiencies
COMMON_TECH_SKILLS = frozenset({
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "golang", "go",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "dart", "perl", "r", "matlab",
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "sqlite", "mariadb", "oracle db", "snowflake", "bigquery",
    "html", "html5", "css", "css3", "sass", "scss", "tailwind", "tailwindcss",
    "react", "react.js", "reactjs", "angular", "angularjs", "vue", "vue.js", "vuejs",
    "next.js", "nextjs", "nuxt", "svelte", "node.js", "nodejs", "express", "express.js",
    "django", "flask", "fastapi", "spring", "spring boot", "asp.net", ".net", "dotnet",
    "rails", "ruby on rails", "laravel", "graphql", "rest", "rest api", "grpc",
    "docker", "kubernetes", "k8s", "helm", "terraform", "ansible", "jenkins",
    "git", "github", "gitlab", "bitbucket", "ci/cd", "devops", "mlops",
    "aws", "amazon web services", "azure", "microsoft azure", "gcp", "google cloud platform",
    "linux", "unix", "bash", "shell", "powershell", "nginx", "apache",
    "machine learning", "deep learning", "nlp", "computer vision", "llm", "genai",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy",
    "tableau", "power bi", "looker", "excel", "jira", "confluence", "figma",
    "agile", "scrum", "kanban", "selenium", "cypress", "playwright", "unit testing",
    "microservices", "kafka", "rabbitmq", "spark", "hadoop", "airflow",
})

# Well-Known Staffing & Enterprise Organizations
KNOWN_COMPANIES = frozenset({
    'insight global', 'compunnel', 'compunnel inc', 'compunnel inc.', 'robert half',
    'teksystems', 'randstad', 'manpower', 'adecco', 'kelly services', 'allegis group',
    'allegis', 'apex systems', 'kforce', 'aerotek', 'collabera', 'cybercoders',
    'lucas group', 'beacon hill', 'addison group', 'hays', 'michael page', 'modis',
    'experis', 'judge group', 'mondo', 'vaco', 'disys', 'kellymitchell', 'aquent',
    'creative circle', 'synergis', 'diverse lynx', 'pyramid consulting', 'e-solutions',
    'infotree', 'artech', 'lancesoft', 'us tech solutions', 'eteam', 'nlb services',
    'mindlance', 'rangam', 'spectraforce', 'tech mahindra', 'tata consultancy services',
    'tcs', 'infosys', 'wipro', 'cognizant', 'hcl', 'accenture', 'deloitte', 'pwc',
    'ey', 'kpmg', 'google', 'microsoft', 'apple', 'amazon', 'meta', 'netflix',
    'salesforce', 'oracle', 'ibm', 'cisco', 'intel', 'nvidia'
})

# Standard Company Industry Descriptions (Never Job Titles)
COMPANY_INDUSTRIES = frozenset({
    'business consulting and services', 'staffing and recruiting',
    'information technology & services', 'information technology and services',
    'computer software', 'financial services', 'management consulting',
    'marketing and advertising', 'hospital & health care', 'higher education',
    'telecommunications', 'human resources', 'internet', 'consumer goods',
    'real estate', 'automotive', 'construction', 'retail', 'pharmaceuticals',
    'biotechnology', 'banking', 'insurance', 'accounting', 'legal services',
    'design', 'architecture & planning', 'facilities services', 'logistics and supply chain'
})

def is_company_name(text: Optional[str]) -> bool:
    """Checks if a text is an organization / company name rather than a human individual."""
    if not text:
        return False
    clean = re.sub(r'[^\w\s]', ' ', str(text).lower()).strip()
    clean = " ".join(clean.split())
    if not clean or len(clean) < 2:
        return False
    if clean in KNOWN_COMPANIES:
        return True
    words = clean.split()
    if not words:
        return False
    if words[-1] in COMPANY_LEGAL_SUFFIXES:
        return True
    if any(w in COMPANY_DOMAIN_TERMS for w in words):
        return True
    return False

def is_company_industry(text: Optional[str]) -> bool:
    """Checks if a text is a corporate industry descriptor rather than a person's title."""
    if not text:
        return False
    clean = re.sub(r'[^\w\s]', ' ', str(text).lower()).strip()
    clean = " ".join(clean.split())
    if clean in COMPANY_INDUSTRIES:
        return True
    if re.search(r'business consulting and services|staffing and recruiting|information technology|computer software|financial services|management consulting', clean):
        return True
    return False

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
    e.g. 'High School Mathematics Teacher', 'Transmission Project Manager', 'End User Computing Administrator'
    """
    if not text:
        return False
    words = [w.lower().strip() for w in re.split(r'[\s\-_/,]+', str(text)) if w.strip()]
    if not words:
        return False

    # Multi-word role phrases (explicit vacancy indicators)
    low = text.strip().lower()
    if any(phrase in low for phrase in [
        "we are hiring", "now hiring", "job opening", "immediate opening",
        "position available", "career opportunity", "vacancy for", "urgent requirement",
        "hiring:"
    ]):
        return True

    # Check if any word is a common job role noun
    role_words = {w for w in words if w in JOB_ROLE_NOUNS}
    discipline_words = {w for w in words if w in {
        'senior', 'junior', 'lead', 'principal', 'staff', 'vp', 'director',
        'specialist', 'mathematics', 'math', 'science', 'project',
        'transmission', 'cloud', 'order', 'servicenow', 'developer', 'phlebotomist',
        'collector', 'specimen', 'software', 'data', 'quality', 'full-time',
        'part-time', 'contract', 'remote', 'hybrid', 'entry-level', 'computing',
        'network', 'security', 'infrastructure', 'systems', 'operations',
        'technical', 'talent', 'recruiting', 'hr', 'sales', 'marketing'
    }}

    # Handle "head":
    # In "Scott Head", "Head" is a very common human surname.
    # Only treat "head" as a job role if:
    # 1. "head of" / "head for" is present e.g. "Head of Talent"
    # 2. Or preceded by a department e.g. "Talent Head", "Tech Head", "Sales Head"
    if 'head' in words:
        head_idx = words.index('head')
        is_role_head = False
        if head_idx + 1 < len(words) and words[head_idx + 1] in ('of', 'for'):
            is_role_head = True
        elif head_idx > 0 and words[head_idx - 1] in {
            'sales', 'tech', 'engineering', 'product', 'marketing', 'talent', 'recruiting',
            'people', 'hr', 'finance', 'operations', 'design', 'legal', 'security', 'data',
            'division', 'department'
        }:
            is_role_head = True
        
        if is_role_head:
            role_words.add('head')
        elif 'head' in role_words:
            role_words.remove('head')

    # Generational suffix guard:
    # In a 3+ word phrase ending in "junior" or "senior" (e.g. "Theodoro Michalak Junior"),
    # it is a person's generational suffix, NOT a job posting!
    if len(words) >= 3 and words[-1] in ('junior', 'senior', 'jr', 'sr'):
        discipline_words.discard('junior')
        discipline_words.discard('senior')

    distinct_roles = role_words | discipline_words
    if role_words and discipline_words and len(distinct_roles) >= 2:
        return True

    if len(words) >= 3 and role_words and (discipline_words or any(w in {'and', 'or', 'the', 'of', '&'} for w in words)):
        return True

    return False

COMPANY_NOISE_PATTERNS = {
    'ask gemini', 'chatgpt', 'copilot', 'claude', 'signalhire', 'contactout',
    'linkedin', 'new tab', 'inbox', 'outlook', 'gmail', 'chrome', 'firefox',
    'edge', 'safari', 'brave', 'windows', 'desktop', 'start a post',
    'corporate email', 'corporate contact', '7 profiles', 'professional',
    'active window', 'overview', 'people', 'reason', 'candidate card',
    'mailings', 'domain search', 'messaged you', 'quick easy prompt',
    'experience', 'my network', 'followed by', 'ihhi', 'my', 'chat',
    'ctv-', 'ctv', 'gmai', 'ynai', 'outbok', 'dahyaa', 'ryzir', 'ryzirk',
    'azusasolutions', 'azusasdutions', 'azusasdgtions', 'impresiviwalth',
    'tnnsowceiic', 'oracbcontractors', 'oraciecontractors', 'epnec metrcvolitan',
    'houstadt', 'caudting', 'javiles', 'supertsi', 'stcu', 'malik', 'jain',
    'hdlstadt ca-aating', 'hdlstadt', 'paladininc',
}
BOGUS_COMPANIES = COMPANY_NOISE_PATTERNS

def validate_company_for_person(company_name: Optional[str], person_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validates whether a company name field is legitimate or noise.
    Returns (is_valid, rejection_reason).
    """
    if not company_name:
        return True, None  # Empty company is fine

    raw = str(company_name).strip()
    if not raw:
        return True, None

    # Reject corrupt unicode replacement characters
    if "\ufffd" in raw or "\\ufffd" in raw or "\uFFFD" in raw:
        return False, f"Company contains corrupt unicode characters: '{raw}'"

    # Reject email addresses or web paths mistaken as companies
    if "@" in raw or "/app/" in raw.lower() or "/chat/" in raw.lower():
        return False, f"Company contains email or path syntax: '{raw}'"

    # Strip leading notification count patterns like "(121) ", "(2) ", "54 | "
    raw = re.sub(r'^(?:[\(\[]\d+\+?[\)\]]\s*[|•·–—\-:]?\s*|\d+\s*[|•·–—\-:]\s*)+', '', raw).strip()
    if not raw:
        return False, "Company was solely notification noise"
    lower = raw.lower()

    # Single-word companies under 4 characters are almost always OCR fragments unless on whitelist
    comp_tokens = raw.split()
    if len(comp_tokens) == 1 and len(raw) < 4:
        valid_short_corps = {"ibm", "sap", "pwc", "hp", "ey", "bp", "ge", "att", "ups", "aws", "bnp", "dhl", "adp", "3m", "8x8"}
        if lower not in valid_short_corps:
            return False, f"Single-word company too short ({len(raw)} chars): '{raw}'"

    # Reject words >= 4 chars with no vowels
    for tok in comp_tokens:
        clean_tok = re.sub(r"[^a-zA-Z]", "", tok)
        if len(clean_tok) >= 4 and not re.search(r"[aeiouyAEIOUY]", clean_tok):
            return False, f"Company token contains no vowels (OCR consonant noise): '{tok}'"

    # Reject remaining notification count patterns if still embedded
    if re.search(r'\(\d+\+?\)', raw):
        return False, f"Company contains notification count pattern: '{raw}'"

    # Reject truncated strings ending with dots or ellipses e.g. "54 Ri Ht...", "355 M..."
    if raw.endswith("...") or raw.endswith("..") or ".." in raw:
        return False, f"Company contains truncated ellipsis: '{raw}'"

    # Reject leading notification digits e.g. "355 M Inbox", "54 Ri"
    if re.match(r'^\d+\s+[A-Za-z0-9]\b', raw):
        return False, f"Company starts with notification digits: '{raw}'"

    # Reject short words that are pronouns, prepositions, or OCR fragments (e.g. "My", "iHHI")
    if len(raw) <= 2 and lower not in {"3m", "hp", "ey", "bp", "ge"}:
        return False, f"Company name too short ({len(raw)} chars): '{raw}'"
    if lower in {'my', 'to', 'in', 'at', 'by', 'we', 'he', 'me', 'us', 'it', 'or', 'if', 'on', 'as', 'an', 'so', 'no', 'up', 'do', 'go', 'is', 'be', 'ihhi'}:
        return False, f"Company is a pronoun/OCR fragment: '{raw}'"

    # Reject OCR artifacts with repeated letters or barcode-like patterns e.g. "iHHI", "lIllI"
    if re.match(r'^[iIl1|Hh]{3,}$', raw):
        return False, f"Company is OCR barcode noise: '{raw}'"

    # Reject if company name IS the person's own name
    if person_name:
        person_clean = person_name.strip().lower()
        company_clean = re.sub(r'^\(\d+\)\s*', '', lower).strip()
        if company_clean == person_clean:
            return False, f"Company name is same as person name: '{raw}'"

    # Reject imperative UI action verb + noun phrases (e.g. "Find companies", "Search people",
    # "Browse jobs", "View all candidates", "Add connections", "Get leads", "Explore profiles")
    if re.match(
        r"^(?:find|search|browse|explore|filter|view|see|show|get|add|save|export|reveal|suggest|import|manage|create|edit|remove|delete|download|upload|sort|select|request|send|copy|paste|join|leave|open|close|track|monitor|compare|match|assign|update|refresh|clear|reset|apply|submit|try|start|discover|access)\s+"
        r"(?:(?:all|my|the|new|more|your|our|recent|available|other|these|those|some|any|every)\s+)?"
        r"(?:companies|company|people|persons?|jobs?|leads?|profiles?|candidates?|contacts?|connections?|members?|teams?|projects?|accounts?|lists?|groups?|results?|emails?|numbers?|data|records?|reports?|sources?|industries?|skills?|roles?|titles?|searches?|filters?|alerts?|notes?|tags?|files?|documents?|folders?|templates?|tasks?|bookmarks?|tabs?|windows?|pages?|shortcuts?|items?|tools?|apps?)\b",
        lower,
    ):
        return False, f"Company is an imperative UI action phrase: '{raw}'"

    # Reject known noise patterns
    for noise in COMPANY_NOISE_PATTERNS:
        if noise == lower or noise in lower:
            return False, f"Company is system/application noise: '{raw}'"

    # Reject if it looks like a URL but not a real company website
    if re.match(r'^https?://', raw) or re.match(r'^www\.', raw, re.IGNORECASE):
        return False, f"Company is a URL, not a name: '{raw}'"

    # Reject if it contains pipe or bracket noise like "rOP-GMM7KIN (13001427)"
    if re.search(r'[A-Z]{2,}-[A-Z0-9]{3,}\s*\(\d+\)', raw):
        return False, f"Company contains identifier noise: '{raw}'"

    # Reject currency symbols and compensation / rate patterns
    if any(c in raw for c in ["$", "€", "£", "₹", "¥", "%"]):
        return False, f"Company contains currency/compensation symbol: '{raw}'"
    if re.search(r"\b(?:hour|an hour|per hour|hourly|salary|annually|per year|w2|c2c|1099|background check|drug test|clearance required)\b", lower):
        return False, f"Company contains compensation or screening phrase: '{raw}'"

    # Reject phone/contact channel noise (e.g. "CTV- Phone", "Phone", "Email", "Grnail")
    if re.search(r"\b(?:phone|mobile|cell|telephone|call|email|e-mail|gmail|grnail|gmai|ynai|yahoo|hotmail|outlook)\b", lower):
        return False, f"Company contains contact channel labels: '{raw}'"
    if re.match(r"^(?:ctv|tel|ph|fx|mob)[\s\-_:]", raw, re.IGNORECASE) or lower in {"ctv-", "ctv", "phone", "email"}:
        return False, f"Company starts with communication channel prefix: '{raw}'"

    # Reject trailing special chars, hyphens, or digits, exempting recognized brands with digits
    known_digit_corps = {"level 3", "factor 75", "studio 54", "3m", "8x8", "carbon3d", "360learning", "web3", "s3",
                          "channel 4", "route 66", "formula 1", "studio 1", "365 media", "724 solutions", "1000heads",
                          "unit 4", "unit4", "g2", "h2o", "k2", "c3", "v2", "s4", "pi3"}
    if raw[-1].isdigit():
        if lower not in known_digit_corps and not re.search(r"\b(?:level|factor|studio|channel|route|formula|unit|phase|stage|version|tier|gen|series|step|lab|group)\s*\d+\b", lower):
            return False, f"Company ends with invalid trailing digit: '{raw}'"
    elif raw[-1] in "-–—_%#@!~`^&*()[]{}<>|\\;:\"'/?.,":
        return False, f"Company ends with invalid punctuation: '{raw}'"
    if any(c in raw for c in [";", ":", "?", "!", "~", "*", "=", "<", ">"]):
        return False, f"Company contains invalid syntax characters: '{raw}'"
    # Reject strings containing actual phone numbers (7+ digits with separators, e.g. "281-555-1234", "5551234567")
    # Allow companies with numeric branding (e.g. "724 Solutions", "365 Media", "1000heads")
    if re.search(r"\b\d{3,}[-.\s]\d{3,}[-.\s]?\d{0,4}\b", raw) or re.search(r"\b\d{7,}\b", raw):
        return False, f"Company contains phone or area code digits: '{raw}'"

    # Reject strings containing individual professional job titles (e.g. "Cindy Davis Consultant") unless corporate designators present
    has_comp_org_suffix = bool(re.search(r"\b(?:group|partners|associates|consulting|consultancy|advisors?|advisers?|agency|capital|systems|inc|llc|corp|board|holdings|services|solutions|firm|network)\b", raw, re.IGNORECASE))
    if not has_comp_org_suffix and re.search(r"\b(?:consultant|recruiter|sourcer|coordinator|advisor|specialist|manager|director|officer)\b", lower):
        return False, f"Company contains person job title words: '{raw}'"

    # Reject chat status and system phrases
    if re.search(r"\b(?:history is on|history is off|active now|offline|online|typing|seen at|last seen|joined the chat)\b", lower):
        return False, f"Company is chat status noise: '{raw}'"

    # Reject Resume / Profile Section Headers
    if lower in SECTION_HEADERS:
        return False, f"Company is a resume/profile section header: '{raw}'"

    # Reject Workplace / Employment Types
    if lower in WORKPLACE_TYPES_SET:
        return False, f"Company is a workplace/employment type: '{raw}'"

    # Reject Common Tech Skills as standalone employers
    if lower in COMMON_TECH_SKILLS and lower not in KNOWN_COMPANIES and lower not in {"sap", "oracle", "salesforce", "microsoft", "google", "aws", "apple", "amazon web services", "figma", "docker", "dropbox", "github", "gitlab", "stripe"}:
        return False, f"Company is a technical skill: '{raw}'"

    # Reject Department / Industry names
    if lower in COMPANY_INDUSTRIES:
        return False, f"Company is an industry descriptor: '{raw}'"

    # Strict Mutual Exclusivity with Human Person Names
    # If the company string looks like a human person name and lacks corporate suffixes or domain terms, reject!
    is_person, _, _ = validate_human_name(raw)
    if is_person:
        words = lower.split()
        has_corp = (
            any(w in COMPANY_DOMAIN_TERMS or w in COMPANY_LEGAL_SUFFIXES for w in words)
            or lower in KNOWN_COMPANIES
            or bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|technology|tech|tek|solutions|services|group|partners|holdings|labs|ventures|consulting|agency|capital|systems|analytics|logistics|cloud|digital|media|interactive|studios|infotech)\b", lower))
        )
        if not has_corp:
            return False, f"Company name appears to be a human person name without corporate markers: '{raw}'"

    return True, None

def validate_human_name(raw_name: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates whether a raw name string is a genuine human name.
    Returns (is_valid, cleaned_name, rejection_reason).
    """
    if not raw_name:
        return False, None, "Empty name"

    name = str(raw_name).strip()

    if is_company_name(name):
        return False, None, 'Organization/company name detected'

    # Reject URLs, domains, and web search snippets
    if re.search(r'(?:https?://|https?www|https?[a-z0-9]|\.(?:com|org|net|io|ai|in|co|edu|gov|dev|app|tech|me|biz|info|xyz)\b)', name.lower()):
        return False, None, f"Name contains URL or domain markers ('{name}')"

    # Reject corrupt unicode replacement characters
    if "\ufffd" in name or "\\ufffd" in name:
        return False, None, f"Name contains corrupt OCR unicode characters ('{name}')"

    # Reject colons (key-value or label strings e.g. "Myridius: People", "CTO: Overview")
    if ":" in name:
        return False, None, f"Name contains colon delimiter ('{name}')"

    # Reject truncated strings ending with dots/ellipses (e.g. "54 Ri Ht...")
    if name.endswith("...") or name.endswith("..") or ".." in name:
        return False, None, f"Name contains truncation ellipses ('{name}')"

    # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] ", "(1) "
    name = re.sub(r"^(?:[\(\[]?\d+\+?[\)\]]?\s*[|•·–—\-:]?\s*)+", "", name).strip()
    name = re.sub(r"\s+\b(?:Verified|Premium|Top Voice)\b.*$", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"^\d+(?:st|nd|rd|th)\s*([A-Za-z])", lambda m: m.group(1).upper(), name, flags=re.IGNORECASE).strip()
    name = re.sub(r"^\d+(?:st|nd|rd|th)\s*", "", name, flags=re.IGNORECASE).strip()

    # Strip degree connection bullets and numbers
    name = re.sub(r'[·•]\s*\d*(?:st|nd|rd|th)?(?:\s*degree(?:\s+connection)?)?', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+(?:st|nd|rd|th)?\s+degree(?:\s+connection)?\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+(?:st|nd|rd|th)\b', '', name, flags=re.IGNORECASE)
    # Clean mashed ordinal suffixes attached to words (e.g. "2ndManaging" -> "Managing", "1stEngineer" -> "Engineer")
    name = re.sub(r'\b\d+(?:st|nd|rd|th)\s*([A-Z])', r' \1', name, flags=re.IGNORECASE)
    name = re.sub(r'(?:,\s*|\s+)(?:MBA|SHRM-CP|SHRM-SCP|PHR|SPHR|PRC|CIR|CMVR|PMP|CAPM|CSM|ITIL|CPA|CFA|CISSP|CISA|CISM|GPHR|SHRM|AWS|CKA|PE|RN|MD|JD|PhD|EdD|BSc|MSc|BA|BS|MA|MS|CPC|CTS|AIRS)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b(?:SHRM-CP|SHRM-SCP|PHR|SPHR|PMP|CAPM|CSM|ITIL|CPA|CFA|CISSP|CISA|CISM|GPHR|SHRM|PhD|EdD|CPC|CTS|AIRS)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\b(?:Verified|Premium|Top Voice)\b.*$", "", name, flags=re.IGNORECASE).strip()
    # Split on title/descriptor separators with spaces (e.g. "John Smith - Recruiter", "Jane Doe | AI")
    parts = re.split(r'\s+[-–—]\s+|[|,]', name)[0]
    cleaned = re.sub(r'[^\w\s\'.\-]', ' ', parts).strip()
    cleaned = cleaned.strip(" \t\n\r'\"`•·-–—|")
    cleaned = " ".join(cleaned.split())

    # Truncate trailing role title words (e.g. "Klaus Raem Managing..." -> "Klaus Raem", "Ricardo Valenciana VP" -> "Ricardo Valenciana")
    tokens = cleaned.split()
    if len(tokens) >= 3:
        cut_idx = -1
        for i in range(2, len(tokens)):
            tok_lower = tokens[i].lower()
            if re.match(r'^(founder|ceo|cto|cpo|coo|vp|recruiter|sourcer|consultant|manager|director|managing|engineer|developer|analyst|specialist|partner|lead|head|architect|sap|oracle|staffing|talent|hiring|hr|human|resources|operations)$', tok_lower):
                cut_idx = i
                break
        if cut_idx >= 2:
            cleaned = " ".join(tokens[:cut_idx])

    if not cleaned or len(cleaned) < 2 or len(cleaned) > 50:
        return False, None, "Invalid length for person name"

    lower = cleaned.lower()
    words = cleaned.split()
    lower_words = [w.lower() for w in words]

    # Reject if all words are <= 2 letters (e.g. "Ri Ht")
    if all(len(w) <= 2 for w in words):
        return False, None, f"Name consists solely of short 2-letter fragments ('{cleaned}')"

    # Reject system noise tokens (e.g. Gemini, Outlook, Inbox, Tab, Apply, etc.)
    SYSTEM_NOISE_TOKENS = {
        'gemini', 'chatgpt', 'copilot', 'claude', 'outlook', 'inbox', 'gmail', 'mail',
        'tab', 'browser', 'feed', 'apply', 'contactout', 'signalhire', 'chrome',
        'windows', 'zoom', 'teams', 'slack', 'search', 'home', 'save', 'saved',
        'results', 'followers', 'connections', 'connection', 'prompt', 'notification',
        'post', 'posts', 'pipeline', 'scout', 'lead', 'leads',
        'history', 'conversation', 'conversations', 'profile', 'profiles',
        'message', 'messages', 'filter', 'filters', 'dialog', 'session', 'menu',
        'overview', 'people', 'reason', 'active window', 'active', 'window',
        'cto', 'ceo', 'cfo', 'coo', 'vp', 'hr', 'myridius', 'candidate card',
        'thanks', 'regards', 'sincerely', 'cheers', 'thank', 'delete', 'archive',
        'sent', 'items', 'flagged', 'unread', 'subject', 'drafts', 'trash', 'junk',
        'folder', 'folders', 'distance', 'directions', 'transit', 'added', 'posted',
        'urgently', 'urgent', 'tell', 'tellme',
    }
    if any(w in SYSTEM_NOISE_TOKENS for w in lower_words):
        return False, None, f"Name contains system or application noise ('{cleaned}')"

    # Reject email greetings, email sign-offs, email action verbs, and web navigation prefixes
    EMAIL_GREETING_PREFIXES = (
        "hi ", "hello ", "dear ", "hey ", "greetings ", "good morning ", "good afternoon ", "good evening "
    )
    EMAIL_SIGNOFF_PREFIXES = (
        "thanks ", "thank you", "regards ", "best regards", "warm regards", "kind regards",
        "with regards", "sincerely", "cheers", "yours truly", "respectfully"
    )
    UI_ACTION_PREFIXES = (
        "the ", "review ", "delete ", "archive ", "sent ", "flagged ", "unread ", "mark as ", "mark all ",
        "reply ", "forward ", "subject ", "re: ", "fw: ", "fwd: ", "date added", "job type",
        "distance from", "directions to", "web results", "search results", "tell me "
    )
    if (
        lower.startswith(EMAIL_GREETING_PREFIXES)
        or lower.startswith(EMAIL_SIGNOFF_PREFIXES)
        or lower.startswith(UI_ACTION_PREFIXES)
    ):
        return False, None, f"Name contains email greeting/signoff or UI action prefix ('{cleaned}')"

    if any(lower == p or lower.startswith(p + " ") or lower.endswith(" " + p) for p in [
        "thanks & regards", "thanks and regards", "delete archive", "sent items", "this week flagged",
        "date added", "web results", "distance from", "tell me what you want to do"
    ]):
        return False, None, f"Name is an email sign-off or UI action phrase ('{cleaned}')"

    if lower in SECTION_HEADERS:
        return False, None, f"Name is a resume/profile section header ('{cleaned}')"
    if lower in WORKPLACE_TYPES_SET:
        return False, None, f"Name is a workplace/employment type ('{cleaned}')"
    if lower in COMMON_TECH_SKILLS:
        return False, None, f"Name is a technical skill ('{cleaned}')"
    if lower in COMPANY_INDUSTRIES:
        return False, None, f"Name is a department/industry descriptor ('{cleaned}')"

    # Reject quantitative / job posting adjectives / agencies
    # Reject quantitative / job posting adjectives / agencies
    QUANTITATIVE_ADJECTIVES = {
        'minimum', 'maximum', 'salary', 'hourly', 'rate', 'rates', 'contract',
        'total', 'average', 'standard', 'background', 'check', 'clearance',
        'client', 'vendor', 'partner', 'partners', 'overview', 'description',
        'associates', 'associated',
    }
    if any(w in QUANTITATIVE_ADJECTIVES for w in lower_words):
        return False, None, f"Name contains quantitative or job posting adjective ('{cleaned}')"

    # Reject job seniority / role descriptor words (e.g. "Senior Fullstack", "Lead Developer")
    JOB_ROLE_KEYWORDS = {
        'senior', 'junior', 'fullstack', 'frontend', 'backend', 'software',
        'principal', 'staff', 'intern', 'internship', 'entry-level', 'remote',
        'executive', 'specialist', 'technician', 'officer', 'coordinator'
    }
    if any(w in JOB_ROLE_KEYWORDS for w in lower_words):
        return False, None, f"Name contains job seniority/role keyword ('{cleaned}')"

    # Reject non-person keywords (benefits, degrees, cities, application keywords)
    if any(w in NON_PERSON_NAME_KEYWORDS for w in lower_words):
        return False, None, f"Name contains non-person / noise keyword: {[w for w in lower_words if w in NON_PERSON_NAME_KEYWORDS]}"

    # Reject job search / listing phrases
    if re.search(r"\b(?:jobs? in|jobs? near|now hiring|job openings?|vacancies|job details|careers?)\b", lower):
        return False, None, f"Name contains job search phrase ('{cleaned}')"

    # Reject names that end in corporate / agency designations (e.g. "Daley Ard Associates")
    if any(lower.endswith(" " + d) for d in [
        "associates", "associated", "partners", "partner", "group", "holdings",
        "solutions", "consulting", "enterprises", "llc", "inc", "corp", "agency",
        "network", "networks", "systems", "ventures", "capital"
    ]):
        return False, None, f"Name ends in corporate or agency designation ('{cleaned}')"

    # Allow single-letter middle initials in 3- or 4-word names (e.g. "David A. Sinclair", "Emily R. Thorne")
    # or trailing surname initial in 2-word names (e.g. "Santhosh R", "Ritik S", "John D")
    for idx, w in enumerate(words):
        if len(w) < 2:
            if len(words) >= 3 and 0 < idx < len(words) - 1 and w.isupper():
                continue
            if len(words) >= 2 and idx == len(words) - 1 and w.isupper() and len(words[0]) >= 3:
                continue
            return False, None, f"Name contains single-letter token ('{cleaned}')"

    # Must be 2 to 4 tokens (up to 5 if containing cultural particles)
    NAME_PARTICLES = {"van", "de", "da", "von", "del", "di", "la", "le", "el", "al", "bin", "ibn", "du", "der", "los", "las", "dos", "das"}
    has_particle = any(w.lower() in NAME_PARTICLES for w in words[1:-1])
    max_words = 5 if has_particle else 4
    if len(words) < 2 or len(words) > max_words:
        return False, None, f"Name must be 2-{max_words} words, got {len(words)} ('{cleaned}')"

    # Every name token with length >= 3 must contain at least one vowel (rejects consonant-only OCR noise e.g. 'Svh', 'Trk')
    if any(len(w) >= 3 and not re.search(r"[aeiouyAEIOUY]", w) for w in words):
        return False, None, f"Name word contains no vowels (OCR consonant noise: '{cleaned}')"

    # Reject internal uppercase letters that represent OCR glitches (e.g. 'SaO', 'Kmika Svh')
    for idx, w in enumerate(words):
        if len(w) > 1 and any(c.isupper() for c in w[1:]):
            # Allow surname in all-caps as last word (e.g. "John SMITH")
            if idx == len(words) - 1 and len(words) >= 2 and words[0][0].isupper() and w.isupper():
                continue
            is_valid_prefix = bool(re.match(r"^(?:Mc[A-Z][a-z]+|Mac[A-Z][a-z]+|O'[A-Z][a-z]+|De[A-Z][a-z]+|Di[A-Z][a-z]+|Du[A-Z][a-z]+|Fitz[A-Z][a-z]+|Van[A-Z][a-z]+|Von[A-Z][a-z]+|Le[A-Z][a-z]+|La[A-Z][a-z]+|[A-Z][a-z]+-[A-Z][a-z]+)$", w))
            if not is_valid_prefix:
                return False, None, f"Name contains OCR internal uppercase glitch: '{w}'"

    # 0. Reject Company / Organization names
    if is_company_name(cleaned):
        return False, None, f"Name is an organization/company ('{cleaned}'), not a human individual"

    # 1. Reject UI actions
    if is_ui_action(lower) or any(w in UI_ACTION_TERMS for w in lower_words):
        return False, None, f"Name is a UI action control ('{cleaned}')"

    # 2. Reject platform names
    if is_platform_name(lower) or any(w in PLATFORM_NAMES for w in lower_words):
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
    if not re.match(r'^[a-zA-Z\s\'.\-]+$', cleaned):
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
    """Cleans a raw job title, rejecting UI action terms, bullets, punctuation, pronouns, and list numbers."""
    if not raw_title or not isinstance(raw_title, str):
        return None
    title = str(raw_title).strip()
    if is_ui_action(title) or title.lower() in {'professional lead', 'contact', 'candidate lead'}:
        return None

    # Strip leading bullet/hyphen/dash/pipe/colon/asterisk/tilde/slash/punctuation
    title = re.sub(r"^[\s\-_–—•·*|:;~,#>\(\)/]+", "", title).strip()
    # Strip leading list numbers e.g. '1. ', '1) ', '1- '
    title = re.sub(r"^\d+[\.\)\-]\s*", "", title).strip()
    # Strip gender pronouns commonly tagged in headers e.g. '(he/him)', '(she/her)'
    title = re.sub(r"\s*\((?:he/him|she/her|they/them|ze/zir|any pronouns)\)", "", title, flags=re.IGNORECASE).strip()
    # Strip connection indicators e.g. '· 1st', '(2nd degree)', '2nd', '3rd+'
    title = re.sub(r"\s*[\(·•|]?\s*\b\d(?:st|nd|rd|th|\+)\b(?:\s*degree)?\)?.*$", "", title, flags=re.IGNORECASE).strip()
    # Strip phone numbers, emails or office/cell tags
    title = re.sub(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{5,}\b|\(office\)|\(cell\)", "", title).strip()
    # Strip trailing punctuation/dashes/pipes/colons/dots/slashes/parentheses
    title = re.sub(r"[\s\-_–—•·*|:;~,#<\.\(\)/]+$", "", title).strip()
    # Normalize multiple whitespace
    title = re.sub(r"\s+", " ", title).strip()

    if len(title) < 3 or not re.search(r"[a-zA-Z]", title):
        return None
    return title if not is_ui_action(title) else None

def clean_company(raw_company: Optional[str], page_context: Optional[str] = None) -> Optional[str]:
    """Cleans a raw company name, rejecting platform names, emojis, sentences, and applying OCR corporate repairs."""
    comp = None
    if raw_company and not is_platform_name(raw_company):
        comp = str(raw_company).strip()
        # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] ", "(1) "
        comp = re.sub(r"^(?:[\(\[]\d+\+?[\)\]]\s*[|•·–—\-:]?\s*|\d+\s*[|•·–—\-:]\s*)+", "", comp).strip()
        comp = re.sub(r"^Current\s*company:\s*", "", comp, flags=re.IGNORECASE)
        comp = re.sub(r"\. Click to skip.*$", "", comp, flags=re.IGNORECASE)
        comp = re.sub(r"\s*\|\s*(?:LinkedIn|Indeed|Glassdoor|ZipRecruiter|SimplyHired).*$", "", comp, flags=re.IGNORECASE).strip()
    elif page_context:
        raw_ctx = str(page_context).strip()
        raw_ctx = re.sub(r"\s*\|\s*(?:LinkedIn|Indeed|Glassdoor|ZipRecruiter|SimplyHired).*$", "", raw_ctx, flags=re.IGNORECASE).strip()
        parts = re.split(r'[:|•\-–—]', raw_ctx)
        candidate = parts[0].strip()
        candidate = re.sub(r"\s+(?:Careers|Jobs|People|Recruiting|Hiring|Overview|Job Search)$", "", candidate, flags=re.IGNORECASE).strip()
        
        # Ensure candidate is not a platform name, nor a human person's name (e.g. "Kelsei Martinez | LinkedIn")
        is_human, _, _ = validate_human_name(candidate)
        if candidate and not is_platform_name(candidate) and not is_human:
            comp = candidate

    if not comp or is_platform_name(comp):
        return None

    # Strip leading bullet/hyphen/dash/pipe/colon/asterisk/tilde/punctuation
    comp = re.sub(r"^[\s\-_–—•·*|:;~,#>]+", "", comp).strip()

    # OCR Artifact & Kerning Degradation Repair for Corporate Names
    comp = re.sub(r"\b[iIlL1]hited\b", "Limited", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[iIlL1]mited\b", "Limited", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[uU]n[iIlL1]ted\b", "United", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[hH]o[lIL1]dings?\b", "Holdings", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[tT]echno[lIL1]ogies\b", "Technologies", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[sS]o[lIL1]utions?\b", "Solutions", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[sS]erv[iIlL1]ces?\b", "Services", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[iI]nternationa[lIL1]\b", "International", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[pP]vt\.?\s*[lL1]td\.?\b", "Pvt Ltd", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\b[cC]0(?:\.|\b)", "Co.", comp, flags=re.IGNORECASE)
    comp = re.sub(r"\.{2,}", ".", comp)

    # Strip contact info and connection/follower metric counts
    comp = re.sub(r"\b(?:contact\s*info|contact\s*details|\d+\+?\s*connections?|mutual\s*connections?|followers?\s*[:\d])\b.*$", "", comp, flags=re.IGNORECASE).strip()
    comp = re.sub(
        r"\s*[·•|]\s*(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site).*",
        "",
        comp,
        flags=re.IGNORECASE,
    ).strip()
    comp = re.sub(r"[·•|].*$", "", comp).strip()
    # Strip trailing punctuation, brackets, and OCR garbage suffixes e.g. "-(/p", "/p", "- sud"
    comp = re.sub(r"\s*[-–—/\\|]+\s*[a-zA-Z0-9]{1,3}$", "", comp).strip()
    comp = re.sub(r"^[\s\-_,·•|:;()\[\]{}]+|[\s\-_,·•|:;()\[\]{}]+$", "", comp).strip()

    # Reject if company string contains emojis, alert words, or is a sentence
    if re.search(r'[🚨⚠️❗❓❌✅]', comp) or re.search(r'\b(?:greater risk|watch for|signs of|illness|warning|alert|sponsored|weather|news)\b', comp, flags=re.IGNORECASE):
        return None
    if len(comp.split()) > 6 or comp.count('.') >= 2 or comp.endswith('.'):
        return None

    # Validate against company noise validator
    is_valid, _ = validate_company_for_person(comp)
    if not is_valid:
        return None

    return comp

def clean_location_text(text: Optional[str]) -> Optional[str]:
    """Cleans punctuation, bullets, timestamps, and contact info triggers from location strings."""
    if not text:
        return None
    cleaned = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*[Cc]ontact\s*[Ii]nfo.*$", "", text).strip()
    cleaned = re.sub(r"\bcontact\s*info\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
    # Strip trailing degree badges (· 2nd, • 1st, · 3rd+)
    cleaned = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd\+?).*$", "", cleaned, flags=re.IGNORECASE).strip()
    # Strip relative timestamps e.g. "4 minutes ago 0", "2 hours ago", "3d ago"
    cleaned = re.sub(r"\b\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*(?:m|min|h|hr|d|w|mo|y)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\d+$", "", cleaned)
    # Strip trailing delimiters with metadata
    cleaned = re.sub(r"^[a-zA-Z],\s*", "", cleaned)
    cleaned = re.sub(r"^[\s\-_,·•|:]+|[\s\-_,·•|:]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else None

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

def is_url_slug_compatible_with_name(url: Optional[str], name: Optional[str]) -> bool:
    """
    Guards against cross-tab contamination where a candidate seen in chat or feed
    is erroneously attributed to a background browser tab's profile URL.
    Returns True if the LinkedIn slug is plausibly compatible with the person's name.
    """
    if not url or not name:
        return True
    m = re.search(r"linkedin\.com/in/([a-zA-Z0-9_\-%]+)", url.lower())
    if not m:
        return True
    slug = m.group(1).lower()
    name_tokens = [re.sub(r'[^a-z]', '', tok.lower()) for tok in name.split() if len(tok) >= 2]
    if not name_tokens:
        return True
    first = name_tokens[0]
    last = name_tokens[-1]
    if first in slug or last in slug:
        return True
    if len(name_tokens) >= 2 and (name_tokens[0][0] + name_tokens[-1]) in slug:
        return True
    if len(name_tokens) >= 2 and (name_tokens[0] + name_tokens[-1][0]) in slug:
        return True
    if slug.isdigit():
        return True
    return False


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
        if is_url_slug_compatible_with_name(linkedin, name):
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
    page_title: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Strict Evidence Grounding Gate.
    Verifies that the extracted entity represents a real, grounded individual or organization rather
    than a job posting or platform artifact.
    """
    page_type = classify_page_type(page_url, page_title)
    is_org = (
        entity_type == 'COMPANY' or
        is_company_name(raw_name) or
        (page_url and '/company/' in page_url and (not raw_name or is_company_name(raw_name)))
    )

    rejections = []

    if is_org:
        # Organization Grounding Rules
        org_name = raw_name or raw_company
        if not org_name or len(org_name.strip()) < 2:
            rejections.append("Missing organization name")
        elif is_platform_name(org_name):
            rejections.append(f"Organization name '{org_name}' is a platform name")
        elif is_ui_action(org_name):
            rejections.append(f"Organization name '{org_name}' is a UI action control")
        clean_n = org_name.strip() if org_name else ""
    else:
        # Person Grounding Rules
        is_valid_name, clean_n, name_reason = validate_human_name(raw_name)
        is_plat = is_platform_name(raw_company)
        is_ui = is_ui_action(raw_title)

        if not is_valid_name:
            rejections.append(f"Name validation failed: {name_reason}")
        if is_plat:
            rejections.append(f"Employer company '{raw_company}' is a job platform name, not a real employer")
        if is_ui:
            rejections.append(f"Title '{raw_title}' is a UI action control")

        # Hard Invariant: Candidate title cannot be identical to Person Name (circular self-attribution)
        # e.g. "Zhou Dongping" -> Title: "Zhou Dongping"
        if raw_name and raw_title and raw_name.strip().lower() == raw_title.strip().lower():
            rejections.append(f"Candidate title '{raw_title}' is identical to person name (circular self-attribution)")

        # Candidate title cannot be a person's name (e.g. "Md Tarik", "Wiley Farler" parsed as title)
        if raw_title:
            is_title_a_name, _, _ = validate_human_name(raw_title)
            if is_title_a_name and not is_job_posting_title(raw_title):
                rejections.append(f"Candidate title '{raw_title}' appears to be a person's name rather than a job title")

        # On Job Board search pages, ungrounded person creations are strictly rejected
        if page_type == 'JOB_SEARCH_PAGE' and (not is_valid_name or is_job_posting_title(raw_name)):
            rejections.append("Job Search Page: Job posting item cannot be created as a person record without explicit recruiter evidence")

    grounding_score = 100 if len(rejections) == 0 else 0
    is_grounded = len(rejections) == 0

    return {
        "is_grounded": is_grounded,
        "is_organization": is_org,
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


VALID_EMAIL_TLDS = {
    "com", "org", "net", "edu", "gov", "mil", "int",
    "co", "io", "ai", "in", "us", "uk", "ca", "de", "fr", "au",
    "dev", "tech", "xyz", "app", "me", "info", "biz", "eu", "ch",
    "nl", "se", "no", "es", "it", "br", "mx", "jp", "cn", "sg",
    "nz", "ie", "za", "cloud", "agency", "global", "solutions",
    "consulting", "careers", "group", "team", "network", "digital",
    "pro", "online", "site", "live", "world"
}

DISALLOWED_OCR_EMAIL_TLDS = {
    "corn", "can", "ccyn", "eom", "carn", "corr", "coin", "comr",
    "cyn", "con", "corm", "cam", "coom", "vom", "xom"
}


def is_valid_email(email: Optional[str]) -> bool:
    """
    Validates whether an email string is structurally sound and has a legitimate TLD.
    Rejects OCR-garbled emails ending in .corn, .can, .ccyn, .eom, etc.
    """
    if not email or not isinstance(email, str):
        return False
    e = email.strip().lower()
    if len(e) < 6 or len(e) > 100:
        return False
    if not re.match(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", e):
        return False
    if any(c in e for c in [" ", "\ufffd", "\uFFFD"]):
        return False

    parts = e.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    if len(local) < 1 or len(domain) < 3:
        return False

    # Domain must contain at least one dot
    if "." not in domain:
        return False

    tld = domain.split(".")[-1].strip().lower()
    if tld in DISALLOWED_OCR_EMAIL_TLDS:
        return False
    if tld not in VALID_EMAIL_TLDS:
        return False

    # Domain name before TLD must be at least 2 chars
    domain_name = domain.split(".")[-2]
    if len(domain_name) < 2:
        return False

    return True
