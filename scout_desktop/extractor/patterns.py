"""
extractor/patterns.py — Semantic Validation & Extraction Regex Engine

Translates and enhances validated extraction algorithms from the TalentScout core.
Includes strict location validation, title/company separation, degree markers,
and school detection.
"""

import re
from typing import Optional, Tuple, List, Dict, Any, Set

# Rejection keywords for locations (prevents "Power Engineering" distractor bug and educational institute overlap)
LOCATION_REJECT_TERMS = re.compile(
    r"\b(?:engineer|engineering|developer|recruiter|recruiting|talent|manager|"
    r"consultant|analyst|specialist|officer|director|lead|head|vp|president|"
    r"designer|scientist|marketing|sales|architect|intern|assistant|advisor|"
    r"technician|contract|full-time|part-time|corp|corporation|inc|"
    r"llc|ltd|gmbh|technologies|technology|tech|solutions|services|group|holdings|"
    r"university|college|institute|school|academy|polytechnic|alumni|student|"
    r"bachelor|master|doctor|phd|degree)\b",
    re.IGNORECASE,
)

# Comprehensive geographic indicators (US States, Countries, Major Global Tech Metro Hubs)
GEO_INDICATORS = re.compile(
    r"\b(?:area|greater|city|county|region|metro|metropolitan|district|remote|"
    r"united states|united kingdom|usa|uk|canada|india|australia|germany|france|"
    r"netherlands|singapore|brazil|spain|italy|ireland|switzerland|sweden|japan|"
    r"uae|dubai|mexico|poland|philippines|alabama|alaska|arizona|arkansas|california|"
    r"colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|"
    r"iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nv|new hampshire|new jersey|new mexico|"
    r"new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|"
    r"south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|"
    r"west virginia|wisconsin|wyoming|england|scotland|wales|london|boston|chicago|seattle|"
    r"austin|san francisco|sf bay|los angeles|atlanta|dallas|houston|denver|phoenix|"
    r"philadelphia|san diego|miami|portland|toronto|vancouver|berlin|paris|amsterdam|"
    r"tokyo|sydney|melbourne|bangalore|bengaluru|mumbai|hyderabad|pune|chennai|delhi|"
    r"noida|gurgaon|raleigh|durham|chapel hill|san jose|salt lake city|dallas-fort worth|"
    r"ontario|british columbia|quebec|alberta|montreal|montréal|calgary|ottawa|"
    r"karnataka|tamil nadu|gujarat|kolkata|ahmedabad|kerala|munich|frankfurt|barcelona|"
    r"lisbon|milan|dublin|zurich|zürich|stockholm|oslo|copenhagen|vienna|brussels|warsaw|"
    r"manchester|birmingham|leeds|edinburgh|bristol|são paulo|sao paulo|buenos aires|bogotá|bogota)\b",
    re.IGNORECASE,
)

# Strict uppercase 2-letter US state code requiring preceding city name of >= 2 characters
US_STATE_POSTAL_REGEX = re.compile(
    r"^[A-Za-z\s.-]{2,},\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)$"
)

UI_ACTIONS = re.compile(
    r"^(?:message|connect|follow|more|save|share|view|endorse|view profile|"
    r"open to work|hiring|verified|contact info|"
    r"export|suggest update|reveal|contact profile|contact details|"
    r"contact management|similar companies|overview|employees|premium features|"
    r"scheduled emails|web visits|crm integrations|zoominfo lite|zoominfo|homepage|quick search|"
    r"home|feed|jobs|messaging|notifications|my network|business|learning|work|sent items|address book|"
    r"glassdoor|wellfound|dice|hired|lever|apply now|easy apply|save job|"
    r"refer & earn|refer and earn|refer a friend|referral program|referrals)$",
    re.IGNORECASE,
)

PRONOUNS = re.compile(
    r"^(?:he/him|she/her|they/them|she/they|he/they)$",
    re.IGNORECASE,
)

METRICS = re.compile(
    r"\b(?:followers?|connections?|mutual|following|network)\b",
    re.IGNORECASE,
)

SCHOOL_KEYWORDS = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic|penn state|"
    r"harvard|stanford|mit|oxford|cambridge|alabama|berkeley|ucla|nyu|purdue|"
    r"columbia|cornell|umass|massachusetts|bachelor|master|mba|ph\.?d|b\.?s\b|b\.?a\b|"
    r"iit\b|bits\b|caltech|insead|notre dame|virginia tech|uiuc\b|georgia tech|"
    r"usc\b|carnegie mellon|cmu\b|waterloo|imperial college|lse\b|london business school|"
    r"eth zurich|tsinghua|wharton|dartmouth|amherst|williams|yale|princeton|duke|"
    r"northwestern|vanderbilt|rice|emory|georgetown|johns hopkins|uc berkeley|"
    r"university of [a-zA-Z\s]+|[a-zA-Z\s]+ university|[a-zA-Z\s]+ institute of technology)\b",
    re.IGNORECASE,
)

DEGREE_KEYWORDS = re.compile(
    r"\b(?:bachelor(?:'s)?|master(?:'s)?|doctor(?:ate)?|ph\.?d|dphil|b\.?s\b|b\.?a\b|b\.?sc\b|b\.?eng\b|"
    r"b\.?tech\b|b\.?e\b|m\.?s\b|m\.?a\b|m\.?sc\b|m\.?eng\b|m\.?tech\b|m\.?b\.?a\b|mba\b|"
    r"associate(?:'s)?|diploma|certificate|juris doctor|j\.?d\b|m\.?d\b)\b",
    re.IGNORECASE,
)

TITLE_KEYWORDS = re.compile(
    r"\b(?:director|manager|recruiter|recruiting|sourcer|engineer|engineering|"
    r"developer|specialist|consultant|analyst|officer|lead|head|vp|president|"
    r"designer|scientist|architect|advisor|partner|technician|intern|assistant|"
    r"chairman|chairperson|chair|executive|founder|co-founder|chief|ceo|cto|cfo|coo|cro|cmo|"
    r"principal|fellow|associate|administrator|coordinator|strategist|leader|counsel|"
    r"supervisor|expert|educator|instructor|teacher|professor|trainer|coach|"
    r"writer|editor|producer|artist|marketer|accountant|auditor|lawyer|attorney|"
    r"physician|doctor|nurse|therapist|pharmacist|practitioner|operator|representative|"
    r"advocate|agent|buyer|trader|underwriter|broker|investor|statistician|economist|researcher|scholar)\b",
    re.IGNORECASE,
)

# ==============================================================================
# AUTHORITATIVE SEMANTIC KNOWLEDGE DICTIONARIES & TAXONOMIES
# ==============================================================================

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

# Common Technical Skills & Proficiencies (Must NOT be treated as candidate names or standalone employers)
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

# Business Departments, Disciplines & Industry Categories (Never Human Names or Commercial Employers)
DEPARTMENTS_AND_INDUSTRIES = frozenset({
    "human resources", "hr", "talent acquisition", "people operations", "people & culture",
    "information technology", "it", "technical support", "tech support",
    "quality assurance", "qa", "software quality assurance", "quality engineering",
    "software engineering", "software development", "web development", "mobile development",
    "data science", "data engineering", "data analytics", "business intelligence",
    "product management", "project management", "program management",
    "customer service", "customer support", "customer success", "client services",
    "sales & marketing", "marketing & advertising", "sales operations",
    "business development", "account management", "public relations",
    "finance & accounting", "financial services", "accounting & finance",
    "legal services", "legal & compliance", "corporate communications",
    "supply chain", "logistics and supply chain", "facilities services",
    "management consulting", "staffing & recruiting", "staffing and recruiting",
    "computer software", "internet", "consumer goods", "retail", "healthcare",
    "higher education", "hospital & health care", "telecommunications",
})

# UI Badges, Actions, and Navigation Elements
UI_BADGES_AND_ACTIONS = frozenset({
    "open to work", "open to", "actively looking", "seeking opportunities",
    "hiring", "actively hiring", "we're hiring", "were hiring",
    "linkedin member", "premium", "verified", "top voice",
    "save to pdf", "print profile", "view in sales navigator", "save in sales navigator",
    "save", "saved", "share", "follow", "following", "unfollow",
    "connect", "connected", "pending", "message", "send message", "inmail",
    "endorse", "endorsements", "recommend", "show all", "see all",
    "more", "more actions", "view profile", "view full profile",
    "apply now", "easy apply", "apply", "save job",
})

# Corporate Suffixes, Business Markers & Legal Forms
EXPANDED_CORP_DESIGNATORS = frozenset({
    "inc", "inc.", "llc", "ltd", "ltd.", "corp", "corp.", "corporation",
    "co", "co.", "company", "companies", "gmbh", "sa", "plc", "bv", "pvt",
    "private limited", "group", "holdings", "enterprises", "ventures", "capital",
    "partners", "associates", "technologies", "technology", "tech", "tek",
    "solutions", "services", "consulting", "consultancy", "staffing", "recruitment",
    "recruiting", "resources", "workforce", "personnel", "labs", "laboratories",
    "studio", "studios", "interactive", "digital", "media", "software", "networks",
    "network", "systems", "system", "logistics", "logix", "infotech", "analytics",
    "intelligence", "inspirations", "innovations", "dynamics", "global", "international",
    "worldwide", "industries", "management", "financial", "advisors", "cloud",
    "communications", "telecom", "pharma", "pharmaceuticals", "therapeutics",
    "biotech", "biosciences", "bank", "banking", "investments", "securities",
    "insurance", "hospital", "healthcare", "health", "foundation", "institute",
    "academy", "polytechnic", "college", "university", "school",
})

# Commercial-Only Corporate Designators (Excludes Academic and Educational institutions)
COMMERCIAL_CORP_DESIGNATORS = frozenset({
    "inc", "inc.", "llc", "ltd", "ltd.", "corp", "corp.", "corporation",
    "co", "co.", "company", "companies", "gmbh", "sa", "plc", "bv", "pvt",
    "private limited", "group", "holdings", "enterprises", "ventures", "capital",
    "partners", "associates", "technologies", "technology", "tech", "tek",
    "solutions", "services", "consulting", "consultancy", "staffing", "recruitment",
    "recruiting", "resources", "workforce", "personnel", "labs", "laboratories",
    "studio", "studios", "interactive", "digital", "media", "software", "networks",
    "network", "systems", "system", "logistics", "logix", "infotech", "analytics",
    "intelligence", "inspirations", "innovations", "dynamics", "global", "international",
    "worldwide", "industries", "management", "financial", "advisors", "advisers", "cloud",
    "communications", "telecom", "pharma", "pharmaceuticals", "therapeutics",
    "biotech", "biosciences", "bank", "banking", "investments", "securities",
})

# Commercial Corporate Legal Forms and Advisory/Consultancy Markers
# Entities containing these are strictly commercial businesses and never academic institutions
COMMERCIAL_LEGAL_AND_BIZ_MARKERS = frozenset({
    "inc", "inc.", "llc", "ltd", "ltd.", "corp", "corp.", "corporation",
    "gmbh", "sa", "plc", "bv", "pvt", "private limited", "co", "co.", "company", "companies",
    "group", "holdings", "enterprises", "ventures", "capital", "partners", "associates",
    "advisors", "advisers", "consulting", "consultancy", "solutions", "services", "staffing",
    "recruitment", "recruiting", "studios", "logistics", "firm",
})

# Prominent Corporate Brands
KNOWN_STANDALONE_CORPS = frozenset({
    "google", "microsoft", "apple", "amazon", "meta", "netflix", "salesforce",
    "oracle", "ibm", "cisco", "intel", "nvidia", "adobe", "sap", "pwc", "deloitte",
    "ey", "kpmg", "accenture", "uber", "airbnb", "stripe", "spotify", "twitter", "x",
    "linkedin", "zoominfo", "apollo", "indeed", "glassdoor", "tek inspirations",
    "kochar tech", "infosys", "wipro", "tcs", "tata consultancy services",
    "cognizant", "hcl", "tech mahindra", "capgemini", "mindtree", "l&t",
    "randstad", "robert half", "allegis", "teksystems", "apex systems", "aerotek",
    "insight global", "collabera", "kforce", "manpower", "adecco", "kelly services",
    "amazon web services", "aws", "figma", "docker", "dropbox", "github", "gitlab",
    "atlassian", "snowflake", "mongodb", "datadog", "elastic",
})

# Thread-safe Dynamic Runtime Knowledge Sets (Synchronized from Fleet AI Teacher without app restart)
DYNAMIC_CORPS: Set[str] = set()
DYNAMIC_NOISE: Set[str] = set()
DYNAMIC_SKILLS: Set[str] = set()
DYNAMIC_TITLES: Set[str] = set()
DYNAMIC_PERSONS: Set[str] = set()


def register_learned_entity(entity_type: str, name: str) -> bool:
    """
    Registers an autonomously learned entity from the Fleet Cloud Teacher
    into local Desktop Scout runtime memory without requiring an application restart.
    """
    if not name or not isinstance(name, str):
        return False
    clean = name.strip().lower()
    if not clean or len(clean) < 2:
        return False
    etype = entity_type.strip().upper()
    if etype == "COMPANY":
        if clean in SECTION_HEADERS or clean in WORKPLACE_TYPES_SET or clean in UI_BADGES_AND_ACTIONS:
            return False
        DYNAMIC_CORPS.add(clean)
        return True
    elif etype == "UI_NOISE":
        DYNAMIC_NOISE.add(clean)
        return True
    elif etype == "SKILL":
        DYNAMIC_SKILLS.add(clean)
        return True
    elif etype == "JOB_TITLE":
        DYNAMIC_TITLES.add(clean)
        return True
    elif etype == "PERSON":
        DYNAMIC_PERSONS.add(clean)
        return True
    return False


def get_learned_entities_stats() -> Dict[str, int]:
    """Returns counts of dynamically learned entities currently in runtime memory."""
    return {
        "companies": len(DYNAMIC_CORPS),
        "corps_count": len(DYNAMIC_CORPS),
        "ui_noise": len(DYNAMIC_NOISE),
        "skills": len(DYNAMIC_SKILLS),
        "titles": len(DYNAMIC_TITLES),
        "persons": len(DYNAMIC_PERSONS),
        "total": len(DYNAMIC_CORPS) + len(DYNAMIC_NOISE) + len(DYNAMIC_SKILLS) + len(DYNAMIC_TITLES) + len(DYNAMIC_PERSONS),
    }


def is_plausible_school(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents a legitimate educational institution."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 90:
        return False
    if is_noise_text(t) or is_valid_location(t):
        return False
    return bool(SCHOOL_KEYWORDS.search(t))


def is_plausible_degree(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents an academic degree or field of study."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 100:
        return False
    return bool(DEGREE_KEYWORDS.search(t))


def is_plausible_title(text: Optional[str]) -> bool:
    """Detects whether a candidate line represents a professional job title."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 75:
        return False
    return bool(TITLE_KEYWORDS.search(t))


def clean_location_text(text: Optional[str]) -> Optional[str]:
    """Cleans punctuation, bullets, timestamps, and contact info triggers from location strings."""
    if not text:
        return None
    cleaned = re.sub(r"\bcontact\s*info\b", "", text, flags=re.IGNORECASE)
    # Strip relative timestamps e.g. "4 minutes ago 0", "2 hours ago", "3d ago"
    cleaned = re.sub(r"\b\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d+\s*(?:m|min|h|hr|d|w|mo|y)\s*ago\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\d+$", "", cleaned)
    # Strip trailing delimiters with metadata, but preserve internal hyphens / en-dashes (e.g. Dallas-Fort Worth, Winston-Salem)
    cleaned = re.sub(r"(?:[·•\u00B7\u2022\u2219\u25E6|]|\s+[-–—\u2013\u2014]\s+).*$", "", cleaned)
    # Strip trailing hyphen/dash fragments e.g. " - sud", " - ntu"
    cleaned = re.sub(r"\s*[-–—]\s*[a-zA-Z]{1,4}$", "", cleaned)
    # Strip single-letter prefix before comma e.g. "D, "
    cleaned = re.sub(r"^[a-zA-Z],\s*", "", cleaned)
    cleaned = re.sub(r"^[\s\-_,·•|:]+|[\s\-_,·•|:]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else None


def is_valid_location(text: Optional[str]) -> bool:
    """
    Strict Semantic Location Validation.
    Rejects titles, industries, company suffixes, credentials, pronouns, metrics,
    and corrupted OCR fragments (e.g. 'D,id - sud', 'San ntu').
    Requires genuine geographic indicators or standard city, state/country syntax.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 3 or len(t) > 80:
        return False

    # Reject OCR artifacts with internal comma without whitespace (e.g. "D,id", "San,Jose")
    if re.search(r"[a-zA-Z],[a-zA-Z]", t):
        return False

    # Reject single-letter tokens immediately before a comma (e.g. "D, id", "A, NY")
    if re.search(r"\b[a-zA-Z],\s*", t):
        return False

    # Reject dangling hyphens or fragments (e.g. "- sud", "sud -") at ends of string
    if re.search(r"\s+[-–—]\s*[a-zA-Z]{1,3}$", t) or t.startswith("-") or t.endswith("-"):
        return False

    # Reject strings with non-standard punctuation chaos or replacement chars
    if any(c in t for c in [";", ":", "?", "!", "~", "*", "=", "<", ">", "%", "\ufffd"]):
        return False

    # Words in location must be plausible words (not all short fragments)
    tokens = [tok for tok in re.split(r"[\s,.-]+", t) if tok]
    if not tokens or all(len(tok) < 3 for tok in tokens):
        return False

    # Reject pronouns & metrics
    if PRONOUNS.match(t) or METRICS.search(t):
        return False

    # Reject connection degrees (1st, 2nd, 3rd)
    if re.match(r"^[·•\s]*\d*(?:st|nd|rd|th)?(?:\s*degree)?$", t, re.IGNORECASE):
        return False

    # Reject UI actions
    if UI_ACTIONS.match(t):
        return False

    # Reject pure numbers or dates
    if re.match(r"^\d+$", t) or re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b", t, re.IGNORECASE):
        return False

    # Reject job roles, disciplines, industries, and company suffix words
    if LOCATION_REJECT_TERMS.search(t):
        return False

    # Strict US State Postal abbreviation (e.g. "San Francisco, CA", "Boise, ID")
    if US_STATE_POSTAL_REGEX.match(t):
        return True

    # Must match genuine geographic keyword
    if GEO_INDICATORS.search(t):
        return True

    # Standard "City, State/Country" with 2-letter state code or standard comma separation (supporting Latin Extended diacritics)
    if re.match(r"^[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s.-]+,\s*[A-Z]{2}$", t):
        return True
    if re.match(r"^[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s.-]+,\s*[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s.-]+(?:,\s*[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F\s.-]+)?$", t):
        return True

    return False


def extract_connection_degree(text: Optional[str]) -> Optional[str]:
    """Extracts connection degree (1st, 2nd, 3rd, 3rd+)."""
    if not text:
        return None
    m = re.search(r"\b(1st|2nd|3rd(?:\+)?)(?!\w)", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def clean_title_and_company(headline: Optional[str], raw_company: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Decomposes headline into clean title and employer when connected by '@', 'at', '|'.
    Example: 'Senior Talent Partner @ Cyberdyne Systems | AI Engineering'
      -> Title: 'Senior Talent Partner', Company: 'Cyberdyne Systems'
    """
    if not headline:
        return None, raw_company

    title = headline.strip()
    company = raw_company

    # Split on ' @ ' or ' at ' (supporting leading '@ ' when headline is wrapped across lines)
    if re.search(r"(?:^|\s+)@\s+", title):
        parts = re.split(r"(?:^|\s+)@\s+", title, maxsplit=1)
        if not parts[0].strip() and len(parts) > 1:
            comp_part = parts[1].split("|")[0].split("•")[0].strip()
            if comp_part and not company:
                company = comp_part
            title = None
        else:
            title = parts[0].strip()
            comp_part = parts[1].split("|")[0].split("•")[0].strip()
            if comp_part and not company:
                company = comp_part
    elif re.search(r"\s+at\s+", title, re.IGNORECASE):
        parts = re.split(r"\s+at\s+", title, maxsplit=1, flags=re.IGNORECASE)
        title = parts[0].strip()
        comp_part = parts[1].split("|")[0].split("•")[0].strip()
        if comp_part and not company:
            company = comp_part

    # Clean separators from title
    if title:
        title = re.split(r"\s*[|•·]\s*", title)[0].strip()

    if company:
        company = re.sub(r"^Current\s*company:\s*", "", company, flags=re.IGNORECASE)
        company = re.sub(r"\. Click to skip.*$", "", company, flags=re.IGNORECASE)
        company = re.sub(r"[·•|].*$", "", company).strip()

    return title or None, company or None


DATE_RANGE_PATTERN = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4})\b.*\b(?:present|\d{4})\b",
    re.IGNORECASE,
)

WORKPLACE_TYPES = re.compile(
    r"\b(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site)\b",
    re.IGNORECASE,
)


def clean_company_name(comp: Optional[str]) -> Optional[str]:
    """Cleans employment type, bullets, contact info, and UI triggers from company strings."""
    if not comp:
        return None
    cleaned = comp.strip()
    # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] ", "(1) "
    cleaned = re.sub(r"^(?:[\(\[]\d+\+?[\)\]]\s*[|•·–—\-:]?\s*|\d+\s*[|•·–—\-:]\s*)+", "", cleaned).strip()
    cleaned = re.sub(r"^Current\s*company:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\. Click to skip.*$", "", cleaned, flags=re.IGNORECASE)
    # Strip contact info and connection/follower metric counts without stripping brand names containing 'Connections' (e.g. Business Connections Inc)
    cleaned = re.sub(r"\b(?:contact\s*info|contact\s*details|\d+\+?\s*connections?|mutual\s*connections?|followers?\s*[:\d])\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"\s*[·•|]\s*(?:full-time|contract|part-time|internship|freelance|apprenticeship|seasonal|hybrid|remote|on-site).*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"[·•|].*$", "", cleaned).strip()
    # Strip trailing punctuation, brackets, and OCR garbage suffixes e.g. "-(/p", "/p", "- sud"
    cleaned = re.sub(r"\s*[-–—/\\|]+\s*[a-zA-Z0-9]{1,3}$", "", cleaned).strip()
    cleaned = re.sub(r"^[\s\-_,·•|:;()\[\]{}]+|[\s\-_,·•|:;()\[\]{}]+$", "", cleaned).strip()
    return cleaned if len(cleaned) >= 2 else None


def is_valid_company_name(text: Optional[str]) -> bool:
    """Validates whether a candidate string is a plausible company name."""
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 60:
        return False

    t_lower = t.lower()

    # 1. Reject disallowed special characters that never belong in corporate entity names
    disallowed_chars = set(r"{}\|<>+*~`^$%;?")
    if any(c in disallowed_chars for c in t):
        return False

    # 2. Reject unbalanced parentheses or brackets (e.g. "IAou-(/p", "Google (US", "Acme]")
    if t.count("(") != t.count(")") or t.count("[") != t.count("]"):
        return False

    # 3. Reject consecutive punctuation or punctuation salad (e.g. "-(/p", "--", "..", "-[", "]/")
    if re.search(r"[-–—/()\[\]#@!~*^<>_+=:;?]{2,}", t):
        return False

    # 4. Reject invalid forward slash usage (e.g. "-(/p", "/p", "Acme/")
    if "/" in t:
        if re.search(r"/[^\w\s]|[^\w\s]/|/\w{1,2}\b|/\s*$|^\s*/", t):
            return False
        if not re.search(r"\b[A-Za-z0-9]+\s*/\s*[A-Za-z0-9]+\b", t):
            return False

    # 5. Reject punctuation glued to letters without proper formatting (e.g. "-(/p", "Acme[p")
    if re.search(r"[-–—/\\(]\w$", t) or re.search(r"[a-zA-Z][\[/][a-zA-Z]", t) or re.search(r"[\]/][a-zA-Z]", t):
        return False

    # 6. Punctuation ratio: non-alphanumeric, non-space characters cannot exceed 22% of total length
    punct_count = sum(1 for c in t if not c.isalnum() and not c.isspace())
    if len(t) > 0 and (punct_count / len(t)) > 0.22:
        return False

    # Reject window titles, platform URLs, and navigation/inbox patterns
    if " | linkedin" in t_lower or " - linkedin" in t_lower or t_lower.endswith("linkedin") or "linkedin.com" in t_lower:
        return False

    # Reject email/inbox, mailings, and chat/message titles
    if any(m in t_lower for m in ["inbox", "mailings", "domain search", "messaged you", "active window", "overview", "candidate card", "quick easy prompt"]):
        return False

    # Reject notification counters e.g. (121), (2), (54)
    if re.search(r"\(\d+\+?\)", t):
        return False

    # Reject truncated strings ending with ellipses e.g. "54 Ri Ht...", "abhish..."
    if t.endswith("...") or t.endswith("..") or re.search(r"\.{2,}", t):
        return False

    # Reject leading notification digits e.g. "355 M Inbox", "54 Ri"
    if re.match(r"^\d+\s+[A-Za-z0-9]\b", t):
        return False

    # Reject short words that are pronouns, prepositions, or OCR fragments (e.g. "My", "In", "At", "By", "To", "iHHI")
    # Exempt globally recognized 2-letter corporations (3M, HP, EY, BP, GE)
    if len(t) <= 2 and t_lower not in {"3m", "hp", "ey", "bp", "ge"}:
        return False
    if t_lower in {"my", "to", "in", "at", "by", "we", "he", "me", "us", "it", "or", "if", "on", "as", "an", "so", "no", "up", "do", "go", "is", "be"}:
        return False

    # Reject common filler words or pronouns as standalone company names
    if t_lower in {"any", "some", "every", "all", "none", "each", "both", "either", "neither", "other", "another"}:
        return False

    # Reject OCR artifacts with repeated letters or barcode-like patterns e.g. "iHHI", "lIllI", "|||"
    if re.match(r"^[iIl1|Hh]{3,}$", t):
        return False

    # Reject unicode replacement character
    if "\ufffd" in t or "\\ufffd" in t or "\uFFFD" in t:
        return False

    # Reject email addresses or web paths mistaken as companies
    if "@" in t or "http://" in t or "https://" in t or "www." in t or "/app/" in t_lower or "/chat/" in t_lower:
        return False

    # ===== Strict OCR Corruption & Mixed Casing Glitch Filter =====
    # Real company names do NOT have lowercase followed by multiple uppercase letters (e.g. "cotAMt")
    # Real company names do NOT end with a single uppercase letter after lowercase (e.g. "fiM")
    comp_tokens = t.split()
    for tok in comp_tokens:
        clean_tok = re.sub(r"[^a-zA-Z]", "", tok)
        if not clean_tok:
            continue
        # Lowercase followed by 2+ uppercase letters (e.g. "cotAMt", "teSTing"), exempting AI brandings (e.g. "OpenAI")
        if re.search(r"[a-z]+[A-Z]{2,}", clean_tok):
            if not (clean_tok.endswith("AI") and re.match(r"^[A-Za-z][a-z]+AI$", clean_tok)):
                return False
        # 2+ lowercase letters followed by single uppercase at end (e.g. "fiM", "producT")
        if len(clean_tok) >= 3 and re.search(r"^[a-z]{2,}[A-Z]$", clean_tok):
            return False
        # Interior uppercase alternation chaos (e.g. "cOtAmT")
        if re.search(r"[a-z][A-Z][a-z][A-Z]", clean_tok):
            return False
        # Starts with lowercase then 2+ uppercase (e.g. "cOTamt")
        if re.search(r"^[a-z][A-Z]{2,}", clean_tok):
            return False
        # Word starting with 2+ uppercase followed by 2+ lowercase (OCR glyph noise like "IAou", "GBre", "ZXop")
        if re.match(r"^[A-Z]{2,}[a-z]{2,}$", clean_tok):
            if clean_tok.lower() not in {"unesco", "unicef", "naacp", "unhcr"}:
                return False

    # Reject if ALL tokens are short filler words or OCR fragments (e.g. "cotamt fim any")
    if all(tok.lower() in {"cotamt", "fim", "any", "the", "and", "or", "in", "of", "to", "a", "an", "is", "for"} for tok in comp_tokens):
        return False

    # Reject OCR misreadings of "Contact info" or LinkedIn UI text
    if any(phrase in t_lower for phrase in [
        "cotamt", "fim any", "cotamt fim", "contact info", "cotamt fim any",
        "contact details", "contact profile", "mutual connections",
        "see all connections", "people also viewed",
    ]):
        return False

    # ===== Chrome / Browser / System UI Noise Blocklist =====
    # These are UI elements that OCR frequently misreads as company names
    chrome_ui_noise = {
        "ask gemini", "gemini", "apps", "search", "more tools", "new tab",
        "bookmarks", "downloads", "history", "extensions", "settings",
        "reading list", "side panel", "tab groups", "chrome web store",
        "customize chrome", "incognito", "cast", "print", "find",
        "zoom", "translate", "passwords", "autofill", "privacy",
        "sync", "about chrome", "help", "exit", "quit",
        "admin settings", "find people", "more actions",
        # LinkedIn UI noise
        "rmt (you)", "(you)", "connect", "message", "follow",
        "linkedin premium", "linkedin recruiter", "try premium",
        "cotamt", "cotamt fim any", "cotamt fim", "fim any", "fim",
        "contact info", "contact details", "contact management",
        # System / taskbar noise
        "ultraviewer", "teamviewer", "anydesk", "task manager",
        "file explorer", "command prompt", "powershell", "terminal",
        # Chat & Collaboration noise
        "microsoft teams", "teams", "google chat", "slack", "new chat",
        "recent chats", "business intelligence", "busmess inteligence",
        "pinned messages", "chat files", "posts", "activity", "calendar",
        "channel notifications", "general", "recent", "chat",
        # Sourcing / OCR noise words and truncated fragments
        "ctv-", "ctv", "gmai", "ynai", "outbok", "dahyaa", "ryzir", "ryzirk",
        "azusasolutions", "azusasdutions", "azusasdgtions", "impresiviwalth",
        "tnnsowceiic", "oracbcontractors", "oraciecontractors", "epnec metrcvolitan",
        "houstadt", "caudting", "javiles", "supertsi", "stcu", "malik", "jain",
        "hdlstadt ca-aating", "hdlstadt", "paladininc",
        # Bogus UI & navigation noise
        "home", "feed", "jobright", "chatgpt", "turboscribe", "email id table",
        "ats", "at", "guided search", "guided search partners", "i'm locking",
        "homepage", "inbox", "messaging", "notifications", "my network", "jobs",
        "for business", "learning", "me", "sent items", "address book", "format text",
        "chelsie walsh", "kelly moran", "jeff thomas", "brenda geisler",
    }
    if t_lower in chrome_ui_noise:
        return False

    # Single-word companies under 4 characters are almost always OCR fragments unless on whitelist
    if len(comp_tokens) == 1 and len(t) < 4:
        valid_short_corps = {"ibm", "sap", "pwc", "hp", "ey", "bp", "ge", "att", "ups", "aws", "bnp", "dhl", "adp", "3m", "8x8"}
        if t_lower not in valid_short_corps:
            return False

    # Reject strings starting or ending with special characters or trailing digits (OCR artifacts like "%iApps", "-5", "System;", "281-")
    if t[0] in "-–—_%#@!~`^&*()[]{}<>|\\;:\"'/?.,":
        return False
    # Allow trailing period if it is a recognized corporate abbreviation suffix (e.g. Inc., Corp., Ltd., Co.)
    if t.endswith("."):
        if not re.search(r"\b(inc|corp|ltd|co|llc|plc|pvt|gmbh|ag|sa|nv|lp|pc|kk|bv|pty)\.$", t_lower):
            return False
    elif t[-1] in "-–—_%#@!~`^&*()[]{}<>|\\;:\"'/?.,":
        return False
    known_digit_corps = {"level 3", "factor 75", "studio 54", "3m", "8x8", "carbon3d", "360learning", "web3", "s3"}
    if t[-1].isdigit():
        if t_lower not in known_digit_corps and not re.search(r"\b(?:level\s*3|factor\s*75|8x8|3m|360|s3|web3)\b", t_lower):
            return False
    if any(c in t for c in [";", ":", "?", "!", "~", "*", "=", "<", ">"]):
        return False
    # Reject strings containing phone numbers or area codes (e.g. "281-", "555-1234")
    if re.search(r"\b\d{3,}[-\s]?\b", t):
        return False
    # Reject strings containing individual professional job titles (e.g. "Cindy Davis Consultant") unless corporate designators present
    has_comp_org_suffix = bool(re.search(r"\b(?:group|partners|associates|consulting|consultancy|advisors?|advisers?|agency|capital|systems|inc|llc|corp|board|holdings|services|solutions|firm|network)\b", t, re.IGNORECASE))
    if not has_comp_org_suffix and re.search(r"\b(?:consultant|recruiter|sourcer|coordinator|advisor|specialist|manager|director|officer)\b", t, re.IGNORECASE):
        return False

    # Reject standalone department abbreviations or isolated 2-letter tokens
    if t_lower in {"it", "hr", "qa", "pr", "ai", "ml", "bi", "ui", "ux", "rd", "pm", "is"}:
        return False

    # Reject pure numeric or very short alphanumeric strings (like "-5", "IT", "aa")
    # Exempt valid brands with digits e.g. "8x8", "3M"
    stripped_alpha = re.sub(r"[^a-zA-Z]", "", t)
    if len(stripped_alpha) < 2 and t_lower not in known_digit_corps:
        return False

    # Reject system/desktop identifiers (e.g. "DESKTOP-GMM7KIN (130891427) UltraViewer")
    if re.match(r"^DESKTOP-", t, re.IGNORECASE):
        return False

    # Reject strings containing system/remote desktop identifiers
    if any(sw in t_lower for sw in ["ultraviewer", "teamviewer", "anydesk", "desktop-"]):
        return False

    # Reject OCR artifacts with excessive special characters (>30% non-alphanumeric)
    non_alpha = sum(1 for c in t if not c.isalnum() and c not in " &.,'-/")
    if len(t) > 0 and non_alpha / len(t) > 0.3:
        return False

    # Words in company name >= 4 characters must contain at least one vowel
    # Exception: Known consonant-cluster corporate abbreviations (KPMG, HSBC, NYSE, etc.)
    CONSONANT_CLUSTER_CORPS = {"kpmg", "hsbc", "nyse", "lvmh", "cbre", "csfb", "dtcc", "bnsf", "kpmg", "bbva", "dksh", "cpfl", "cppib", "nflx", "splk", "ftnt", "crwd", "pltr", "twtr", "msft", "goog", "nvda", "tsmc"}
    for tok in comp_tokens:
        clean_tok = re.sub(r"[^a-zA-Z]", "", tok)
        if len(clean_tok) >= 4 and not re.search(r"[aeiouyAEIOUY]", clean_tok):
            if clean_tok.lower() not in CONSONANT_CLUSTER_CORPS:
                return False

    # Civic, government, institutional organizations that may contain geographic names (e.g. City and County of San Francisco, Port of Oakland)
    is_civic_or_org = bool(re.search(
        r"\b(?:city\s+and\s+county|city\s+of|county\s+of|state\s+of|port\s+of|department\s+of|"
        r"department|commission|authority|administration|district|foundation|institute|hospital|"
        r"health\s+system|schools?)\b",
        t,
        re.IGNORECASE,
    ))
    if not is_civic_or_org and is_valid_location(t):
        return False
    if is_noise_text(t):
        return False
    if DATE_RANGE_PATTERN.search(t):
        return False
    # Reject currency symbols and compensation / rate patterns (e.g. "$80 - $85 an hour", "€50k", "£40/hr")
    if any(c in t for c in ["$", "€", "£", "₹", "¥", "%"]):
        return False
    if re.search(r"\b(?:hour|an hour|per hour|hourly|salary|annually|per year|w2|c2c|1099|background check|drug test|clearance required)\b", t, re.IGNORECASE):
        return False

    # Reject phone/contact channel noise (e.g. "CTV- Phone", "CTV-", "Phone", "Mobile", "Call", "Email", "Grnail", "Gmai", "Ynai")
    if re.search(r"\b(?:phone|mobile|cell|telephone|call|email|e-mail|gmail|grnail|gmai|ynai|yahoo|hotmail|outlook)\b", t, re.IGNORECASE):
        return False
    if re.match(r"^(?:ctv|tel|ph|fx|mob)[\s\-_:]", t, re.IGNORECASE) or t.lower() in {"ctv-", "ctv", "phone", "email"}:
        return False

    # Reject chat status and system phrases (e.g. "History is on", "Active now", "Turn off history")
    if re.search(r"\b(?:history is on|history is off|active now|offline|online|typing|seen at|last seen|joined the chat)\b", t, re.IGNORECASE):
        return False

    # Reject social proof, connections, and activity lines (unless corporate suffix present like "Business Connections Inc")
    if not has_comp_org_suffix and re.search(
        r"\b(?:followed by|mutual connection|connections|followers|people you may know|"
        r"talks about|activity|show all|see all|shared by|reposts|profile views|"
        r"connect|message|view full profile|more profiles)\b",
        t,
        re.IGNORECASE,
    ):
        return False
    # Reject lines that look like sentences or have verbs like "looking for", "helping"
    if re.search(r"\b(?:looking for|helping|building|passionate about|specializing in)\b", t, re.IGNORECASE):
        return False
    # Reject Resume / Profile Section Headers (e.g. "Experience", "About", "Skills", "Education")
    if t_lower in SECTION_HEADERS:
        return False

    # Reject Workplace / Employment Types (e.g. "Full-time", "Contract", "Hybrid", "Remote", "On-site")
    if t_lower in WORKPLACE_TYPES_SET:
        return False

    # Reject Common Tech Skills as standalone employers (e.g. "Python", "Java", "Kubernetes")
    # Exception: Recognized corporations that coincide with platform/product brands
    if t_lower in COMMON_TECH_SKILLS and t_lower not in KNOWN_STANDALONE_CORPS and t_lower not in {"sap", "oracle", "salesforce", "microsoft", "google", "aws", "apple", "amazon web services", "figma", "docker", "dropbox", "github", "gitlab", "stripe"}:
        return False

    # Reject Department / Industry names (e.g. "Human Resources", "Information Technology")
    if t_lower in DEPARTMENTS_AND_INDUSTRIES:
        return False

    # Reject UI Badges and Actions (e.g. "Open to work", "Hiring", "LinkedIn Member")
    if t_lower in UI_BADGES_AND_ACTIONS:
        return False

    # Reject Educational degrees and schools (unless civic/hospital context or explicit corporate designator present)
    if is_plausible_degree(t):
        return False
    if not is_civic_or_org and not has_comp_org_suffix and is_plausible_school(t):
        return False

    # Pure job titles are not company names unless they contain explicit corporate/org identifiers
    has_comp_suffix = bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|group|partners|holdings|labs|studio|ventures|consulting|agency|capital|systems)\b", t, re.IGNORECASE))
    if not has_comp_suffix and is_plausible_title(t):
        return False

    # Strict Mutual Exclusivity with Human Person Names:
    # If string is a clean human person name (e.g. "Abhishek Jadon", "Mohit Tiwari", "John Smith")
    # and possesses NO corporate designators or corporate legal suffixes, and is NOT in KNOWN_STANDALONE_CORPS,
    # it is a candidate's personal name and MUST NOT be classified as a company!
    comp_tokens_lower = {re.sub(r"[^a-zA-Z0-9]", "", tok).lower() for tok in comp_tokens if tok}
    has_any_corp_marker = (
        t_lower in KNOWN_STANDALONE_CORPS
        or any(d in comp_tokens_lower for d in EXPANDED_CORP_DESIGNATORS)
        or bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|technology|tech|tek|solutions|services|group|partners|holdings|labs|ventures|consulting|agency|capital|systems|analytics|logistics|cloud|digital|media|interactive|studios|infotech)\b", t, re.IGNORECASE))
    )
    if not has_any_corp_marker and is_valid_person_name(t):
        return False

    return True


def is_valid_skill(text: Optional[str]) -> bool:
    """Validates whether a candidate string represents a legitimate professional skill."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 50:
        return False
    if is_noise_text(t) or is_valid_location(t):
        return False
    # Reject UI noise in skills sections
    if re.search(
        r"\b(?:show all|see all|endorse|endorsed|passed skill|assessment|quiz|recommendation|"
        r"view|learn more|click to|add skill|skills\b|top skills)\b",
        t,
        re.IGNORECASE,
    ):
        return False
    # Reject pure numbers or dates
    if re.match(r"^\d+$", t) or DATE_RANGE_PATTERN.search(t):
        return False
    return True


def is_noise_text(text: Optional[str]) -> bool:
    """Detects boilerplate navigation, UI buttons, social proof, and cookie banners."""
    if not text:
        return True
    t = text.strip().lower()
    if len(t) < 2:
        return True
    # Standalone social proof words or metric patterns (must not match inside valid company names like 'Business Connections Inc')
    standalone_noise = {"connections", "followers", "activity", "highlights", "interests", "pending", "open to"}
    if t in standalone_noise or re.search(r"^\d+\+?\s*(?:connections?|followers?)$", t):
        return True

    noise_phrases = [
        "see all", "view full profile", "sign in to view", "join now",
        "accept cookies", "privacy policy", "terms of service", "skip to main content",
        "keyboard shortcuts", "all rights reserved", "contact info",
        "followed by", "mutual connection", "mutual connections",
        "people also viewed", "more profiles for", "show all", "show more",
        "send message", "more actions",
        # Chrome / Browser UI noise
        "ask gemini", "more tools", "new tab", "bookmarks bar",
        "reading list", "side panel", "chrome web store", "customize chrome",
        "admin settings", "find people", "cast to",
        # System tray / taskbar
        "ultraviewer", "teamviewer", "anydesk", "task manager",
    ]
    return any(p in t for p in noise_phrases)


def is_valid_person_name(text: Optional[str]) -> bool:
    """
    Strict Semantic Person Name Validation.
    Validates if a text string is a genuine individual candidate name.
    Rejects:
    - Job Titles ("Facilities Coordinator", "Contract Mid-level", "Senior Engineer")
    - Corporate / Vendor entities ("Cloud Destinations LLC", "InnovaWorkforce Inc", "Fastnet Staffing")
    - UI / Browser / Document artifacts ("All Bookmarks", "Full Job Description", "Business Management Spreadsheets")
    - Text with special symbols ("Qlick Ap*y") or numbers
    - Connection degrees ('· 1st', '2nd'), locations, pronouns, and actions.
    Requires 2 to 4 properly capitalized human name parts.
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    # Strip pronouns and connection degree badges first
    t = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd(?:\+)?).*$", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    if len(t) < 3 or len(t) > 40:
        return False
    if is_noise_text(t) or is_valid_location(t) or extract_connection_degree(t):
        return False
    if UI_ACTIONS.match(t) or re.search(r"^[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]", t):
        return False

    # A person name cannot contain digits, colons, or punctuation/math/wildcard symbols
    if any(c.isdigit() or c in "*@/\\()_~!+=<>[]{}^%$#:;?\"&" for c in t):
        return False

    # Reject truncated strings ending with dots or ellipses e.g. "54 Ri Ht...", "John..."
    if t.endswith(".") or ".." in t:
        return False

    t_lower = t.lower()

    # A person name CANNOT be a job title!
    if is_plausible_title(t):
        return False

    # A person name CANNOT be a Section Header, Workplace Type, Tech Skill, Department/Industry, or UI Action/Badge!
    if t_lower in SECTION_HEADERS or t_lower in WORKPLACE_TYPES_SET or t_lower in COMMON_TECH_SKILLS:
        return False
    if t_lower in DEPARTMENTS_AND_INDUSTRIES or t_lower in UI_BADGES_AND_ACTIONS:
        return False
    if is_plausible_school(t) or is_plausible_degree(t):
        return False
    if t_lower in KNOWN_STANDALONE_CORPS:
        return False

    # A person name CANNOT contain explicit corporate suffixes, business designations or markers!
    if any(re.search(rf"\b{re.escape(d)}\b", t, re.IGNORECASE) for d in EXPANDED_CORP_DESIGNATORS):
        return False

    # Reject names that start with article 'The ' or UI action 'Review '
    if t_lower.startswith("the ") or t_lower.startswith("review "):
        return False

    # Reject names that end in corporate / agency designations (e.g. "Daley Ard Associates", "The Davis Companies")
    if any(t_lower.endswith(" " + d) for d in [
        "associates", "associated", "partners", "partner", "group", "holdings",
        "solutions", "consulting", "enterprises", "llc", "inc", "corp", "agency",
        "network", "networks", "systems", "ventures", "capital", "companies", "company",
        "college", "university", "queue", "tech", "tek", "labs", "inspirations",
        "innovations", "dynamics", "logistics", "cloud", "digital", "media"
    ]):
        return False

    words = t.split()
    # Filter for alphabetic words (allowing standard hyphens, apostrophes, and Latin Extended accented characters)
    clean_words = [re.sub(r"[^a-zA-Z\u00C0-\u024F\'-]", "", w) for w in words]
    clean_words = [w for w in clean_words if w and any(c.isalpha() for c in w)]
    if len(clean_words) < 2 or len(clean_words) > 4:
        return False

    # Allow single-letter middle initials in 3- or 4-word names (e.g. "John F. Kennedy", "David A. Sinclair")
    for idx, w in enumerate(clean_words):
        if len(w) < 2:
            if len(clean_words) >= 3 and 0 < idx < len(clean_words) - 1 and w.isupper():
                continue
            return False

    # Reject if all words are 2-letter fragments (e.g. "Ri Ht" -> OCR truncation)
    # Real names must have at least one name component with length >= 3
    if all(len(w) <= 2 for w in clean_words):
        return False

    # Reject any string containing unicode replacement character or unprintable chars
    if "\ufffd" in t or "\\ufffd" in t or "\uFFFD" in t:
        return False

    # Every name token with length >= 3 must contain at least one vowel (rejects consonant-only OCR noise e.g. 'Svh', 'Trk')
    VOWEL_CHECK_REGEX = re.compile(r"[aeiouyAEIOUY\u00C0-\u00C6\u00C8-\u00CF\u00D2-\u00D6\u00D9-\u00DC\u00E0-\u00E6\u00E8-\u00EF\u00F2-\u00F6\u00F9-\u00FC]")
    if any(len(w) >= 3 and not VOWEL_CHECK_REGEX.search(w) for w in clean_words):
        return False

    # Every word must be a valid human name token: Capital letter followed by lowercase letters
    # Accepts: John, Mary-Jane, O'Connor, McDonald, de, van, da, von
    # Also supports uniform ALL-CAPS names (common in resumes/ATS: e.g. "JOHN SMITH")
    NAME_PARTICLES = {"van", "de", "da", "von", "del", "di", "la", "le", "el", "al", "bin", "ibn", "du", "der"}
    is_uniform_all_caps = all(w.isupper() for w in clean_words)

    for idx, w in enumerate(clean_words):
        # Allow lowercase particles when not first or last word
        if w.lower() in NAME_PARTICLES and 0 < idx < len(clean_words) - 1:
            continue
        if not is_uniform_all_caps and not w[0].isupper():
            return False
        # Reject ALL-CAPS words mixed into normal-case names that look like acronyms or UI labels (e.g. 'LLC', 'INC', 'D365', 'MDG')
        if not is_uniform_all_caps and len(w) > 2 and w.isupper():
            return False
        # Reject internal uppercase letters that represent OCR glitches (e.g. 'SaO', 'MEkan', 'JaIl', 'LiKe')
        # Allowed exceptions: McDonald, McCarthy, O'Connor, FitzGerald
        if not is_uniform_all_caps:
            rest = w[1:]
            if any(c.isupper() for c in rest):
                # Check if valid prefix (Mc, Mac, O', Fitz) or standard hyphenated name
                is_valid_prefix = bool(re.match(r"^(?:Mc[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+|Mac[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+|O'[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+|Fitz[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+|[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+-[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+)$", w))
                if not is_valid_prefix:
                    return False

    # Check for non-name title/role/section/system/document words
    lower_words = [w.lower() for w in clean_words]
    blacklisted = {
        # Navigation & UI
        "experience", "education", "skills", "about", "activity", "interests",
        "recommendations", "people", "results", "search", "connections", "followers",
        "director", "recruiter", "manager", "engineer", "sourcer", "specialist",
        "consultant", "analyst", "current", "previous", "view", "contact",
        "university", "college", "institute", "school", "company", "group", "team",
        "inbox", "mail", "gmail", "outlook", "gemini", "chatgpt", "claude", "copilot",
        "chat", "assistant", "jobs", "apply", "feed", "home", "notifications",
        "network", "windows", "tab", "chrome", "firefox", "edge", "safari",
        "microsoft", "teams", "slack", "skype", "webex", "zoom", "technovion",
        "scout", "demand", "lawyers", "lawyer", "legal",
        "post", "posts", "quick", "easy", "prompt", "top", "united", "states",
        "history", "conversation", "conversations", "profile", "profiles",
        "message", "messages", "filter", "filters", "dialog", "session", "menu",
        # Quantitative / Job posting / Adjectives / Agencies
        "minimum", "maximum", "salary", "hourly", "rate", "rates", "contract",
        "total", "average", "standard", "background", "check", "clearance",
        "client", "vendor", "partner", "partners", "overview", "description",
        "associates", "associated",
        # Web / Browser & Document Noise
        "bookmarks", "all", "description", "spreadsheets", "management", "contract",
        "mid-level", "senior", "junior", "full", "part-time", "temporary", "remote",
        "hybrid", "on-site", "overview", "hiring", "job", "career", "careers",
        "talent", "staffing", "recruitment", "employee", "employees", "software",
        "international", "business", "development", "lead", "services", "solutions",
        "destinations", "workforce", "work", "worker", "employment", "document",
        "spreadsheet", "file", "download", "summary", "workflow", "data", "report",
        "candidate", "candidates", "applicant", "applicants", "resume", "cv",
        "open", "closed", "level", "hourly", "salary", "annually", "rate",
        "click", "skip", "badge", "icon", "logo", "search", "google", "meet",
        "tools", "tool", "admin", "settings", "setting", "app", "apps", "more",
        "desktop", "find", "spark", "planet", "seasoned", "tv", "options", "option",
        "device", "devices", "help", "support", "sign", "login", "logout", "portal",
        "zoominfo", "lite", "export", "reveal", "suggest", "homepage",
        "reason", "active", "window", "active window", "overview", "candidate card",
        # Executive role acronyms & tokens
        "cto", "ceo", "cfo", "coo", "cio", "cmo", "cpo", "cro", "vp", "svp", "evp", "hr",
        "myridius",
        # Departments, Disciplines & Corporate Nouns
        "human", "resources", "information", "technology", "acquisition", "operations",
        "quality", "assurance", "tech", "tek", "inspirations", "innovations", "dynamics",
        "logistics", "cloud", "digital", "media", "interactive", "studios", "pharma",
        "biotech", "healthcare", "systems", "solutions", "services", "consultancy",
        "advisors", "enterprises", "holdings", "ventures", "capital",
    }
    if any(w in blacklisted for w in lower_words):
        return False
    if any(w in EXPANDED_CORP_DESIGNATORS for w in lower_words if len(w) > 1):
        return False
    if any(w in COMMON_TECH_SKILLS for w in lower_words if len(w) > 1):
        return False
    if "reason:" in t.lower() or "active window" in t.lower() or "overview" in t.lower():
        return False
    return True


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
    if not EMAIL_REGEX.match(e):
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


EMAIL_REGEX = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")
PHONE_REGEX = re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+\d{10,14}|\b[2-9]\d{9}\b")


def clean_person_name(text: Optional[str]) -> Optional[str]:
    """
    Strips notification badges (54 |, (54)), degree badges (• 2nd, · 1st), pronouns,
    honorifics (Dr., Mr.), bullets, and validates clean candidate name.
    Example: '54 | Ritik Sharma' -> 'Ritik Sharma'
    Example: '(54) Mariam Nguyen • 2nd' -> 'Mariam Nguyen'
    """
    if not text:
        return None
    raw_str = text.strip()
    # Immediate rejection of key-value / label pairs with colons or truncated strings with ellipses
    if ":" in raw_str or ".." in raw_str or raw_str.endswith("..."):
        return None
    t = raw_str
    # Strip leading notification numbers or badges e.g. "54 | ", "(54) ", "[12] "
    t = re.sub(r"^(?:[\(\[]\d+\+?[\)\]]\s*[|•·–—\-:]?\s*|\d+\s*[|•·–—\-:]\s*)+", "", t).strip()
    # Strip degree suffixes: • 2nd, · 1st, 3rd, etc.
    t = re.sub(r"\s*[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+\s*(?:1st|2nd|3rd(?:\+)?).*$", "", t, flags=re.IGNORECASE).strip()
    # Strip pronouns in parens/brackets/free: (she/her), [she/her], (he/him), etc.
    t = re.sub(r"\s*[\(\[]?\b(?:she/her|he/him|they/them|she/they|he/they)\b[\)\]]?", "", t, flags=re.IGNORECASE).strip()
    # Strip honorific prefixes (Dr., Mr., Ms., Mrs., Prof.)
    t = re.sub(r"^(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+", "", t, flags=re.IGNORECASE).strip()
    # Strip trailing badges / dots / icons
    t = re.sub(r"[·•\u00B7\u2022\u2219\u25E6\u2013\u2014|]+.*$", "", t).strip()
    # Strip generational / name suffixes e.g. ", Jr.", " Jr.", ", Sr.", " III", " II", " IV"
    t = re.sub(r"(?:,\s*(?:Jr|Sr|III|IV|II)\.?|\s+(?:Jr|Sr|III|IV|II)\.?)$", "", t, flags=re.IGNORECASE).strip()
    # Strip professional post-nominal credentials appended to names with commas.
    # e.g. "Kate Threewitts, SPHR, SHRM-SCP" → "Kate Threewitts"
    # e.g. "Megan Alford, PRC, CIR, CMVR" → "Megan Alford"
    # Pattern: comma followed by 2-10 uppercase letters/numbers/hyphens (credential abbreviations)
    t = re.sub(r"(?:,\s*[A-Z][A-Z0-9\-]{1,9})+$", "", t).strip()
    return t if is_valid_person_name(t) else None


def classify_semantic_entity(text: Optional[str]) -> Dict[str, Any]:
    """
    Authoritative, high-precision semantic entity discriminator.
    Unambiguously classifies candidate strings into mutually exclusive types:
      - 'PERSON': Individual human name (e.g., 'Abhishek Jadon', 'Mohit Tiwari', 'John Smith')
      - 'COMPANY': Corporate entity / employer (e.g., 'Tek Inspirations', 'Kochar Tech', 'Google', 'Acme Corp')
      - 'JOB_TITLE': Professional role / headline (e.g., 'Senior Software Engineer', 'Recruiting Manager')
      - 'LOCATION': Geographic location (e.g., 'San Francisco, CA', 'Bengaluru, Karnataka')
      - 'EDUCATION': School, college, university, or degree (e.g., 'Stanford University', 'B.S. Computer Science')
      - 'SKILL': Technical/domain skill (e.g., 'Python', 'Java', 'Docker', 'Kubernetes')
      - 'WORKPLACE_TYPE': Employment/work arrangement (e.g., 'Full-time', 'Contract', 'Hybrid', 'Remote')
      - 'SECTION_HEADER': Resume/profile section title (e.g., 'Experience', 'About', 'Skills', 'Education')
      - 'DEPARTMENT_OR_INDUSTRY': Business function or sector (e.g., 'Human Resources', 'Information Technology')
      - 'UI_NOISE': Action button, badge, metric, or navigation artifact (e.g., 'Open to work', 'Save to PDF', 'Connect')
      - 'UNKNOWN': Ambiguous or unclassified text
    """
    if not text or not isinstance(text, str):
        return {"entity_type": "UNKNOWN", "confidence": 0.0, "details": "Empty input"}

    t = text.strip()
    if not t:
        return {"entity_type": "UNKNOWN", "confidence": 0.0, "details": "Whitespace only"}

    t_lower = t.lower()

    # 1. Section Headers (Universal invariants: 'Overview', 'Experience', 'About', etc.)
    if t_lower in SECTION_HEADERS:
        return {"entity_type": "SECTION_HEADER", "confidence": 0.99, "details": "Resume or profile section header"}

    # 2. Workplace / Employment Types (Universal invariants: 'Full-time', 'Contract', etc.)
    if t_lower in WORKPLACE_TYPES_SET:
        return {"entity_type": "WORKPLACE_TYPE", "confidence": 0.99, "details": "Employment or workplace arrangement"}

    # 3. Dynamic Runtime Learned Entities (Learned by Fleet AI Teacher without restart)
    if t_lower in DYNAMIC_CORPS:
        return {"entity_type": "COMPANY", "confidence": 0.99, "source": "DYNAMIC_CLOUD_LEARNED", "details": "Dynamically learned corporate entity (Fleet AI Teacher)"}
    if t_lower in DYNAMIC_NOISE:
        return {"entity_type": "UI_NOISE", "confidence": 0.99, "source": "DYNAMIC_CLOUD_LEARNED", "details": "Dynamically learned UI noise (Fleet AI Teacher)"}
    if t_lower in DYNAMIC_SKILLS:
        return {"entity_type": "SKILL", "confidence": 0.99, "source": "DYNAMIC_CLOUD_LEARNED", "details": "Dynamically learned technical skill (Fleet AI Teacher)"}
    if t_lower in DYNAMIC_TITLES:
        return {"entity_type": "JOB_TITLE", "confidence": 0.99, "source": "DYNAMIC_CLOUD_LEARNED", "details": "Dynamically learned job title (Fleet AI Teacher)"}
    if t_lower in DYNAMIC_PERSONS:
        return {"entity_type": "PERSON", "confidence": 0.99, "source": "DYNAMIC_CLOUD_LEARNED", "details": "Dynamically learned candidate name (Fleet AI Teacher)"}

    # 3. UI Noise / Action Buttons / Social Badges / Metrics / Pronouns
    if (
        UI_ACTIONS.match(t)
        or PRONOUNS.match(t)
        or METRICS.search(t)
        or t_lower in UI_BADGES_AND_ACTIONS
        or is_noise_text(t)
        or re.match(r"^[·•\s]*\d*(?:st|nd|rd|th)?(?:\s*degree)?$", t, re.IGNORECASE)
    ):
        return {"entity_type": "UI_NOISE", "confidence": 0.99, "details": "UI button, badge, action, or social metric"}

    # 4. Prominent Standalone Corporate Brands (AWS, Figma, Google, Microsoft, Docker, etc.)
    if t_lower in KNOWN_STANDALONE_CORPS and is_valid_company_name(t):
        return {"entity_type": "COMPANY", "confidence": 0.99, "details": "Prominent standalone corporate brand"}

    # 5. Education: Academic Degrees or Educational Institutions (Evaluated before generic commercial markers,
    # unless entity contains explicit commercial business markers like 'Cambridge Advisors' or 'Oxford BioMedica Inc')
    if is_plausible_degree(t):
        return {"entity_type": "EDUCATION", "confidence": 0.95, "details": "Academic degree or field of study"}

    tokens = [re.sub(r"[^a-zA-Z0-9]", "", tok).lower() for tok in t.split() if tok]
    has_commercial_biz_marker = (
        any(tok in COMMERCIAL_LEGAL_AND_BIZ_MARKERS for tok in tokens)
        or bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|group|partners|associates|holdings|ventures|consulting|consultancy|advisors|advisers|capital|solutions|services|staffing)\b", t, re.IGNORECASE))
    )
    if is_plausible_school(t) and not has_commercial_biz_marker and t_lower not in KNOWN_STANDALONE_CORPS:
        return {"entity_type": "EDUCATION", "confidence": 0.95, "details": "School, college, or university"}

    # 6. Companies with Explicit Commercial Markers (e.g. 'Cambridge Advisors', 'Tek Inspirations', 'Kochar Tech')
    has_explicit_commercial_marker = (
        has_commercial_biz_marker
        or any(tok in COMMERCIAL_CORP_DESIGNATORS for tok in tokens)
        or bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|technology|tech|tek|solutions|services|group|partners|associates|holdings|labs|ventures|consulting|consultancy|agency|capital|systems|analytics|logistics|cloud|digital|media|interactive|studios|infotech|advisors|advisers)\b", t, re.IGNORECASE))
    )
    if has_explicit_commercial_marker and is_valid_company_name(t):
        return {"entity_type": "COMPANY", "confidence": 0.95, "details": "Corporate entity with verified business marker"}

    # 7. Business Departments and Industries
    if t_lower in DEPARTMENTS_AND_INDUSTRIES:
        return {"entity_type": "DEPARTMENT_OR_INDUSTRY", "confidence": 0.95, "details": "Department, business function, or industry sector"}

    # 8. Technical Skills (e.g. 'Python', 'Java', 'Kubernetes', 'React')
    if t_lower in COMMON_TECH_SKILLS:
        return {"entity_type": "SKILL", "confidence": 0.95, "details": "Technical skill, tool, or framework"}

    # 9. Geographic Locations
    if is_valid_location(t):
        return {"entity_type": "LOCATION", "confidence": 0.95, "details": "Geographic location or postal code"}

    # 10. Professional Job Titles
    has_comp_suffix = bool(re.search(r"\b(?:inc|llc|ltd|corp|corporation|technologies|group|partners|holdings|labs|studio|ventures|consulting|agency|capital|systems)\b", t, re.IGNORECASE))
    if not has_comp_suffix and is_plausible_title(t):
        return {"entity_type": "JOB_TITLE", "confidence": 0.92, "details": "Professional job title"}

    # 11. Company vs Person Arbitration
    if is_valid_person_name(t):
        return {"entity_type": "PERSON", "confidence": 0.95, "details": "Verified human person name"}

    if is_valid_company_name(t):
        return {"entity_type": "COMPANY", "confidence": 0.85, "details": "Plausible company name"}

    if is_valid_skill(t):
        return {"entity_type": "SKILL", "confidence": 0.70, "details": "Plausible professional skill"}

    return {"entity_type": "UNKNOWN", "confidence": 0.0, "details": "Unclassified text"}


