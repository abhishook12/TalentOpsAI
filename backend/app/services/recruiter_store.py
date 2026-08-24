"""
RecruiterStore: Unified query engine using DuckDB over Parquet files.
Provides search, filter, pagination, and count methods that mirror
the existing SQLAlchemy-based queries but read from compressed Parquet.

The site sees ONE unified dataset regardless of storage backend.
"""
import os
import re
import logging
import threading
import time
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger("recruiter_store")

# Use an absolute path relative to this file's location to ensure it works on both Windows and Linux
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PARQUET_DIR = os.environ.get("PARQUET_DIR", os.path.join(BASE_DIR, "data"))

# Fallback to /tmp in read-only serverless environments (like Vercel/AWS Lambda)
try:
    os.makedirs(PARQUET_DIR, exist_ok=True)
    test_file = os.path.join(PARQUET_DIR, '.test_write')
    with open(test_file, 'w') as f:
        f.write('1')
except OSError:
    PARQUET_DIR = "/tmp/talentops_data"
    os.makedirs(PARQUET_DIR, exist_ok=True)

def _find_parquet_file() -> str:
    candidates = [
        os.environ.get("PARQUET_PATH", ""),
        os.path.join(PARQUET_DIR, "recruiters_full.parquet"),
        os.path.join(BASE_DIR, "data", "recruiters_full.parquet"),
        os.path.join(BASE_DIR, "backend", "data", "recruiters_full.parquet"),
        os.path.join(os.getcwd(), "data", "recruiters_full.parquet"),
        os.path.join(os.getcwd(), "backend", "data", "recruiters_full.parquet"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "recruiters_full.parquet")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "data", "recruiters_full.parquet")),
        "data/recruiters_full.parquet",
        "backend/data/recruiters_full.parquet",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return os.path.join(PARQUET_DIR, "recruiters_full.parquet")

PARQUET_FILE = _find_parquet_file()

METRO_HUBS = {
    "SF_BAY_AREA": {
        "name": "San Francisco Bay Area",
        "states": ["CA"],
        "cities": ["san francisco", "san jose", "oakland", "palo alto", "sunnyvale", "mountain view", "santa clara", "fremont", "berkeley", "san mateo", "redwood city", "cupertino", "menlo park", "pleasanton", "walnut creek", "san bruno", "santa cruz"]
    },
    "NYC_TRI_STATE": {
        "name": "New York Tri-State Metro",
        "states": ["NY", "NJ", "CT"],
        "cities": ["new york", "new york city", "nyc", "brooklyn", "manhattan", "queens", "jersey city", "hoboken", "stamford", "white plains", "newark", "princeton", "morristown", "greenwich", "bronx", "staten island"]
    },
    "SEATTLE_METRO": {
        "name": "Seattle–Bellevue Tech Hub",
        "states": ["WA"],
        "cities": ["seattle", "bellevue", "redmond", "kirkland", "renton", "bothell", "tacoma", "everett"]
    },
    "TEXAS_TRIANGLE": {
        "name": "Texas Innovation Triangle",
        "states": ["TX"],
        "cities": ["austin", "dallas", "houston", "fort worth", "plano", "irving", "arlington", "san antonio", "frisco", "richardson", "the woodlands", "round rock"]
    },
    "RESEARCH_TRIANGLE": {
        "name": "Research Triangle & Charlotte",
        "states": ["NC"],
        "cities": ["raleigh", "durham", "chapel hill", "cary", "charlotte", "morrisville", "greensboro", "winston-salem", "research triangle park", "wake forest"]
    },
    "GREATER_BOSTON": {
        "name": "Greater Boston Biotech & Tech",
        "states": ["MA"],
        "cities": ["boston", "cambridge", "waltham", "somerville", "quincy", "newton", "burlington", "framingham", "worcester", "lexington"]
    },
    "CHICAGO_METRO": {
        "name": "Greater Chicago Metro",
        "states": ["IL"],
        "cities": ["chicago", "naperville", "evanston", "schaumburg", "oak brook", "downers grove", "rosemont", "aurora", "deerfield"]
    },
    "DMV_CAPITAL": {
        "name": "Washington DC Capital Metro",
        "states": ["DC", "VA", "MD"],
        "cities": ["washington", "arlington", "alexandria", "bethesda", "reston", "mclean", "tysons", "herndon", "silver spring", "rockville", "fairfax", "vienna", "annapolis"]
    }
}

# Lazy import duckdb — only when needed
_duckdb = None
def _get_duckdb():
    global _duckdb
    if _duckdb is None:
        import duckdb
        _duckdb = duckdb
    return _duckdb


def _parse_boolean_search(query: str, fields: Optional[List[str]] = None) -> Tuple[str, List[Any]]:
    """Parse boolean search expressions with AND, OR, NOT, parentheses, and quoted strings into DuckDB SQL."""
    if fields is None:
        fields = ['recruiter_name', 'email', 'specialization', 'normalized_city', 'company_id']
    
    raw_tokens = re.findall(r'(\bAND\b|\bOR\b|\bNOT\b|[()]|\"[^\"]+\"|[^\s()]+)', query.strip())
    if not raw_tokens:
        return "", []

    params = []
    sql_parts = []
    prev_was_term = False

    def term_to_sql(term):
        clean = term.strip('"').strip("'").lower()
        sub = " OR ".join([f"LOWER(COALESCE(CAST({f} AS VARCHAR), '')) LIKE ?" for f in fields])
        return f"({sub})", [f"%{clean}%" for _ in fields]

    for t in raw_tokens:
        upper_t = t.upper()
        if upper_t in ('AND', 'OR', 'NOT'):
            sql_parts.append(upper_t)
            prev_was_term = False
        elif t == '(':
            if prev_was_term:
                sql_parts.append('AND')
            sql_parts.append('(')
            prev_was_term = False
        elif t == ')':
            sql_parts.append(')')
            prev_was_term = True
        else:
            if prev_was_term:
                sql_parts.append('AND')
            sub_sql, sub_params = term_to_sql(t)
            sql_parts.append(sub_sql)
            params.extend(sub_params)
            prev_was_term = True

    return " ".join(sql_parts), params

STATE_NAME_TO_CODE = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'dc': 'DC', 'district of columbia': 'DC'
}

SPECIALIZATION_KEYWORDS = {
    'tech': 'Information Technology', 'technology': 'Information Technology', 'software': 'Information Technology',
    'it': 'Information Technology', 'cloud': 'Information Technology', 'devops': 'Information Technology',
    'healthcare': 'Healthcare & Nursing', 'nursing': 'Healthcare & Nursing', 'nurse': 'Healthcare & Nursing',
    'medical': 'Healthcare & Nursing', 'pharma': 'Healthcare & Nursing', 'biotech': 'Healthcare & Nursing',
    'finance': 'Finance & Accounting', 'accounting': 'Finance & Accounting', 'accountant': 'Finance & Accounting',
    'cpa': 'Finance & Accounting', 'banking': 'Finance & Accounting',
    'engineering': 'Engineering & Manufacturing', 'manufacturing': 'Engineering & Manufacturing', 'mechanical': 'Engineering & Manufacturing',
    'sales': 'Sales & Marketing', 'marketing': 'Sales & Marketing',
    'hr': 'Human Resources', 'human resources': 'Human Resources',
    'legal': 'Legal & Compliance', 'operations': 'Operations & Supply Chain', 'logistics': 'Operations & Supply Chain'
}

def parse_smart_natural_query(query: str) -> Dict[str, Any]:
    """
    Parses natural language intent from search strings.
    E.g. 'Senior tech recruiters in Texas with verified phones' ->
         {
             'state': 'TX',
             'has_phone': True,
             'seniority_level': 'Senior',
             'specialization': 'Information Technology',
             'remaining_search': 'recruiters'
         }
    """
    if not query:
        return {}
        
    extracted = {
        "state": None,
        "has_phone": None,
        "seniority_level": None,
        "specialization": None,
        "remaining_search": query
    }
    
    working_q = query.strip()
    
    # 1. Phone requirement
    phone_pattern = r'\b(?:with|having|has)\s+(?:verified\s+)?phone(?:s)?\b|\bphone\s+verified\b|\bwith\s+phone\b'
    if re.search(phone_pattern, working_q, re.IGNORECASE):
        extracted["has_phone"] = True
        working_q = re.sub(phone_pattern, '', working_q, flags=re.IGNORECASE)
        
    # 2. State mentions
    st_code_match = re.search(r'\b(?:in|from|based in)\s+([A-Za-z]{2})\b', working_q, re.IGNORECASE)
    if st_code_match and st_code_match.group(1).upper() in STATE_NAME_TO_CODE.values():
        extracted["state"] = st_code_match.group(1).upper()
        working_q = working_q[:st_code_match.start()] + ' ' + working_q[st_code_match.end():]
    else:
        for full_name, code in STATE_NAME_TO_CODE.items():
            st_name_pat = rf'\b(?:in|from|based in)\s+{full_name}\b|\b{full_name}\b'
            if re.search(st_name_pat, working_q, re.IGNORECASE):
                extracted["state"] = code
                working_q = re.sub(st_name_pat, '', working_q, flags=re.IGNORECASE)
                break
                
    # 3. Seniority
    seniority_map = {
        'senior': 'Senior', 'lead': 'Lead', 'principal': 'Principal',
        'director': 'Director', 'executive': 'Executive', 'vp': 'VP',
        'head': 'Head', 'manager': 'Manager'
    }
    for kw, val in seniority_map.items():
        sen_pat = rf'\b{kw}\b'
        if re.search(sen_pat, working_q, re.IGNORECASE):
            extracted["seniority_level"] = val
            working_q = re.sub(sen_pat, '', working_q, flags=re.IGNORECASE)
            break
            
    # 4. Specialization keywords
    for kw, spec_val in SPECIALIZATION_KEYWORDS.items():
        spec_pat = rf'\b{kw}\b'
        if re.search(spec_pat, working_q, re.IGNORECASE):
            extracted["specialization"] = spec_val
            working_q = re.sub(spec_pat, '', working_q, flags=re.IGNORECASE)
            break
            
    working_q = re.sub(r'\s+', ' ', working_q).strip()
    working_q = re.sub(r'^(?:recruiters|recruiter|contacts|leads|people|sourcers)\s*', '', working_q, flags=re.IGNORECASE).strip()
    extracted["remaining_search"] = working_q if working_q else None
    
    return extracted



class RecruiterStore:
    """
    In-memory DuckDB-backed query engine for recruiter data stored in Parquet.
    Falls back to PostgreSQL if Parquet is unavailable.
    """

    def __init__(self):
        self._conn = None
        self._lock = threading.Lock()
        self._loaded = False
        self._record_count = 0
        self._last_load_time = None
        self._last_error = None

    def _ensure_loaded(self):
        """Load Parquet into DuckDB if not already loaded, or if local file changed."""
        # If already loaded and using httpfs (no local file), stay loaded — nothing to compare.
        if self._loaded and self._conn is not None and not os.path.exists(PARQUET_FILE):
            return

        current_mtime = 0
        try:
            current_mtime = os.path.getmtime(PARQUET_FILE)
        except OSError:
            pass
            
        if self._loaded and self._conn is not None and getattr(self, '_last_mtime', -1) == current_mtime:
            return
            
        if not self._lock.acquire(timeout=5.0):
            logger.warning("Timeout acquiring RecruiterStore lock. Download may be in progress.")
            if not self._conn:
                raise Exception("Database is currently initializing (downloading Parquet). Please try again in 30 seconds.")
            return

        try:
            # Re-check inside lock for TOCTOU safety
            if self._loaded and self._conn is not None and not os.path.exists(PARQUET_FILE):
                return

            current_mtime = 0
            try:
                current_mtime = os.path.getmtime(PARQUET_FILE)
            except OSError:
                pass
                
            if self._loaded and self._conn is not None and getattr(self, '_last_mtime', -1) == current_mtime:
                return
                
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
                
            self._load()
            try:
                self._record_count = self._conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
            except Exception:
                self._record_count = 0
            self._last_mtime = current_mtime
        finally:
            self._lock.release()

    def _get_conn(self):
        """Ensure store is loaded and return active DuckDB connection."""
        self._ensure_loaded()
        return self._conn

    def _load(self):
        """Load the Parquet file into DuckDB using HTTPFS for serverless environments."""
        import time
        duckdb = _get_duckdb()
        
        primary_url = "https://github.com/abhishook12/TalentOpsAI/releases/download/data-v1/recruiters_full.parquet"
        
        start = time.time()
        self._conn = duckdb.connect(":memory:")
        
        try:
            self._conn.execute("PRAGMA max_memory='256MB';")
            self._conn.execute("PRAGMA threads=4;")
        except Exception:
            pass

        try:
            self._conn.execute("INSTALL httpfs;")
            self._conn.execute("LOAD httpfs;")
        except Exception as e:
            logger.warning(f"Could not load httpfs extension: {e}")

        active_file = _find_parquet_file()
        if os.path.exists(active_file):
            logger.info(f"Using local Parquet file: {active_file}")
            parquet_path = f"'{active_file.replace(os.sep, '/')}'"
        else:
            logger.info(f"Parquet file not found locally. Streaming directly via HTTPFS from {primary_url}")
            parquet_path = f"'{primary_url}'"

        try:
            # Use zero-copy VIEW to keep memory usage under 45MB and prevent Linux OOM exit 137
            self._conn.execute(f"""
                CREATE VIEW recruiters AS 
                SELECT * FROM read_parquet({parquet_path})
            """)
            
            res = self._conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()
            self._record_count = res[0] if res else 0
            
            # Build the exclusion list for MODE() filter
            free_domains_sql = ", ".join(f"'{d}'" for d in self._FREE_EMAIL_DOMAINS)
            
            # Pre-aggregate company stats to prevent API timeouts on every search
            self._conn.execute(f"""
                CREATE TABLE company_overall AS 
                SELECT
                    CAST(company_id AS VARCHAR) AS company_key,
                    COUNT(*) AS recruiter_count,
                    MODE(LOWER(SPLIT_PART(email, '@', 2))) FILTER (
                        WHERE email IS NOT NULL
                          AND email LIKE '%@%'
                          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_domains_sql})
                          AND LENGTH(SPLIT_PART(email, '@', 2)) > 2
                    ) AS dominant_domain
                FROM recruiters
                WHERE company_id IS NOT NULL 
                  AND TRIM(CAST(company_id AS VARCHAR)) != ''
                  AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('need to fill data', 'unknown', 'n/a', 'na', 'none', 'null', 'missing', 'missing.local', 'independent staffing')
                  AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT LIKE '%is becoming%'
                  AND INSTR(CAST(company_id AS VARCHAR), '|') = 0
                GROUP BY company_key
            """)

            self._conn.execute(f"""
                CREATE TABLE company_summary AS 
                SELECT
                    CAST(company_id AS VARCHAR) AS company_key,
                    UPPER(COALESCE(state, '')) AS state_upper,
                    COUNT(*) AS recruiter_count,
                    MODE(LOWER(SPLIT_PART(email, '@', 2))) FILTER (
                        WHERE email IS NOT NULL
                          AND email LIKE '%@%'
                          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ({free_domains_sql})
                          AND LENGTH(SPLIT_PART(email, '@', 2)) > 2
                    ) AS dominant_domain
                FROM recruiters
                WHERE company_id IS NOT NULL 
                  AND TRIM(CAST(company_id AS VARCHAR)) != ''
                  AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT IN ('need to fill data', 'unknown', 'n/a', 'na', 'none', 'null', 'missing', 'missing.local', 'independent staffing')
                  AND LOWER(TRIM(CAST(company_id AS VARCHAR))) NOT LIKE '%is becoming%'
                  AND INSTR(CAST(company_id AS VARCHAR), '|') = 0
                GROUP BY company_key, state_upper
            """)

            # Build in-memory fast lookup for company key -> dominant domain
            try:
                domain_rows = self._conn.execute("SELECT company_key, dominant_domain FROM company_overall WHERE dominant_domain IS NOT NULL").fetchall()
                self._company_domains = {str(r[0]): r[1] for r in domain_rows}
            except Exception:
                self._company_domains = {}

            elapsed = time.time() - start
            self._last_error = None
            logger.info(f"RecruiterStore loaded {self._record_count:,} recruiters from Parquet in {elapsed:.2f}s")
            
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            logger.error(f"Failed to load Parquet dataset from {parquet_path}: {e}. Falling back to empty tables.")
            # Safety fallback to prevent 500 errors on the API
            self._conn = duckdb.connect(":memory:")
            self._conn.execute("CREATE TABLE recruiters (id INTEGER)")
            self._conn.execute("""
                CREATE TABLE company_summary (
                    company_key VARCHAR,
                    state_upper VARCHAR,
                    recruiter_count INTEGER,
                    dominant_domain VARCHAR
                )
            """)
            self._company_domains = {}
            self._record_count = 0
            
        self._loaded = True
        self._last_load_time = time.time()

    def get_company_domain(self, company_key: str) -> Optional[str]:
        """Fast O(1) lookup of dominant email domain for any company key/ID."""
        if not company_key:
            return None
        self._ensure_loaded()
        domains_map = getattr(self, '_company_domains', None)
        if domains_map:
            return domains_map.get(str(company_key).strip())
        return None

    def reload(self):
        """Force reload from Parquet (e.g. after sync)."""
        with self._lock:
            if self._conn:
                self._conn.close()
            self._conn = None
            self._loaded = False
        self._ensure_loaded()

    @property
    def total_count(self) -> int:
        self._ensure_loaded()
        return self._record_count

    @property
    def data_version(self) -> str:
        """A cheap cache key that changes whenever the active Parquet file changes."""
        self._ensure_loaded()
        try:
            stat = os.stat(PARQUET_FILE)
            return f"{stat.st_mtime_ns}:{stat.st_size}"
        except OSError:
            # No local file — using httpfs streaming. Use load time as a stable version.
            return f"httpfs:{self._last_load_time or 'unloaded'}"

    # Free/generic email domains to exclude when computing dominant company domain
    _FREE_EMAIL_DOMAINS = frozenset({
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
        'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
        'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
        'ymail.com', 'cox.net', 'charter.net', 'earthlink.net',
        'talentops.ai',  # Internal placeholder domain
    })

    def company_directory(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        matched_keys: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return company keys, counts, and dominant email domain from the active recruiter dataset.

        Imported data contains both numeric database IDs and company-name strings
        in ``company_id``. The raw value is therefore the only stable key shared
        by company search, state drill-down, and recruiter listings.

        The ``dominant_domain`` is the most common email domain among recruiters
        for each company (excluding free email providers). This allows fallback
        logo and name inference even when PostgreSQL metadata is missing.
        """
        self._ensure_loaded()
        clean_q = "".join(c for c in (query or "").lower() if c.isalnum())
        raw_tokens = [re.sub(r'[^a-zA-Z0-9]', '', t.lower()) for t in (query or "").split() if re.sub(r'[^a-zA-Z0-9]', '', t.lower())]
        stop_words = {'llc', 'inc', 'corp', 'co', 'ltd', 'company', 'group', 'services'}
        meaningful_tokens = [t for t in raw_tokens if t not in stop_words]
        tokens = meaningful_tokens if meaningful_tokens else raw_tokens

        if state and state.upper() != "ALL":
            where = ["state_upper = ?"]
            params = [state.upper()]
            order_by = "recruiter_count DESC, cs.company_key ASC"

            if query or matched_keys:
                sub_conds = []
                if query:
                    token_conds = []
                    for t in tokens:
                        token_conds.append("(LOWER(cs.company_key) LIKE ? OR LOWER(COALESCE(co.dominant_domain, '')) LIKE ?)")
                        params.extend([f"%{t}%", f"%{t}%"])
                    
                    fuzzy_sql = f"""(
                        ({' AND '.join(token_conds)})
                        OR LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')) LIKE '%{clean_q}%'
                        OR LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')) LIKE '%{clean_q}%'
                        OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')), '{clean_q}') > 0.80
                        OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') > 0.80
                    )"""
                    sub_conds.append(fuzzy_sql)
                    order_by = f"""
                        GREATEST(
                            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(cs.company_key, ' ', ''), '-', '')), '{clean_q}'),
                            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(co.dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}')
                        ) DESC,
                        recruiter_count DESC,
                        cs.company_key ASC
                    """
                if matched_keys:
                    placeholders = ", ".join("?" for _ in matched_keys)
                    sub_conds.append(f"cs.company_key IN ({placeholders})")
                    params.extend(matched_keys)
                where.append(f"({' OR '.join(sub_conds)})")

            cur = self._conn.cursor()
            rows = cur.execute(f"""
                SELECT
                    cs.company_key,
                    SUM(cs.recruiter_count) AS recruiter_count,
                    COALESCE(co.dominant_domain, MAX(cs.dominant_domain)) AS dominant_domain
                FROM company_summary cs
                LEFT JOIN company_overall co ON cs.company_key = co.company_key
                WHERE {' AND '.join(where)}
                GROUP BY cs.company_key, co.dominant_domain
                ORDER BY {order_by}
            """, params).fetchall()
        else:
            where = ["1=1"]
            params = []
            order_by = "recruiter_count DESC, company_key ASC"

            if query or matched_keys:
                sub_conds = []
                if query:
                    token_conds = []
                    for t in tokens:
                        token_conds.append("(LOWER(company_key) LIKE ? OR LOWER(COALESCE(dominant_domain, '')) LIKE ?)")
                        params.extend([f"%{t}%", f"%{t}%"])
                    
                    fuzzy_sql = f"""(
                        ({' AND '.join(token_conds)})
                        OR LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')) LIKE '%{clean_q}%'
                        OR LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')) LIKE '%{clean_q}%'
                        OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}') > 0.80
                        OR jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}') > 0.80
                    )"""
                    sub_conds.append(fuzzy_sql)
                    order_by = f"""
                        GREATEST(
                            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(company_key, ' ', ''), '-', '')), '{clean_q}'),
                            jaro_winkler_similarity(LOWER(REPLACE(REPLACE(COALESCE(dominant_domain, ''), ' ', ''), '-', '')), '{clean_q}')
                        ) DESC,
                        recruiter_count DESC,
                        company_key ASC
                    """
                if matched_keys:
                    placeholders = ", ".join("?" for _ in matched_keys)
                    sub_conds.append(f"company_key IN ({placeholders})")
                    params.extend(matched_keys)
                where.append(f"({' OR '.join(sub_conds)})")

            cur = self._conn.cursor()
            rows = cur.execute(f"""
                SELECT
                    company_key,
                    recruiter_count,
                    dominant_domain
                FROM company_overall
                WHERE {' AND '.join(where)}
                ORDER BY {order_by}
            """, params).fetchall()

        return [
            {
                "company_key": str(key),
                "recruiter_count": int(count),
                "dominant_domain": str(domain) if domain else None,
            }
            for key, count, domain in rows
        ]

    # ─── Core Query Methods ───

    def _df_to_dict(self, df):
        if df is None:
            return []
        try:
            if df.empty:
                return []
        except Exception:
            return []
        import math
        import pandas as pd
        
        results = df.to_dict(orient='records')
        clean_results = []
        for row in results:
            clean_row = {}
            for k, v in row.items():
                if v is None:
                    clean_row[k] = None
                elif isinstance(v, float) and math.isnan(v):
                    clean_row[k] = None
                elif pd.isna(v):
                    clean_row[k] = None
                else:
                    clean_row[k] = v
            clean_results.append(clean_row)
        return clean_results

    def get_by_id(self, recruiter_id: int) -> Optional[Dict[str, Any]]:
        """Get a single recruiter by ID."""
        self._ensure_loaded()
        cur = self._conn.cursor()
        result = cur.execute(
            "SELECT * FROM recruiters WHERE recruiter_id = ?", [recruiter_id]
        ).fetchdf()
        if result is None or result.empty:
            return None
        return self._df_to_dict(result)[0]

    def list_recruiters(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        state: Optional[str] = None,
        metro_hub: Optional[str] = None,
        company_id: Optional[int] = None,
        company_key: Optional[str] = None,
        company_name: Optional[str] = None,
        specialization: Optional[str] = None,
        specialization_sector: Optional[str] = None,
        seniority_level: Optional[str] = None,
        timezone_code: Optional[str] = None,
        company_scale: Optional[str] = None,
        is_deliverable: Optional[bool] = None,
        has_phone: Optional[bool] = None,
        is_active: Optional[bool] = None,
        needs_review: Optional[bool] = None,
        email_status: Optional[str] = None,
        data_source: Optional[str] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List recruiters with filtering and pagination.
        Returns (results, total_count).
        """
        self._ensure_loaded()

        where_clauses = []
        params = []

        if search and (' in ' in search.lower() or ' with ' in search.lower() or 'has phone' in search.lower()):
            smart = parse_smart_natural_query(search)
            if smart.get("state") and not state:
                state = smart["state"]
            if smart.get("has_phone") is not None and has_phone is None:
                has_phone = smart["has_phone"]
            if smart.get("seniority_level") and not seniority_level:
                seniority_level = smart["seniority_level"]
            if smart.get("specialization") and not specialization:
                specialization = smart["specialization"]
            if smart.get("remaining_search") != search:
                search = smart.get("remaining_search")

        if search:
            search_str = search.strip()
            if any(k in search_str for k in (' AND ', ' OR ', ' NOT ', '"', '(', ')')) or search_str.startswith('NOT '):
                bool_sql, bool_params = _parse_boolean_search(search_str)
                if bool_sql:
                    where_clauses.append(f"({bool_sql})")
                    params.extend(bool_params)
            else:
                search_lower = search_str.lower()
                where_clauses.append("""(
                    LOWER(COALESCE(CAST(recruiter_name AS VARCHAR), '')) LIKE ? 
                    OR LOWER(COALESCE(CAST(email AS VARCHAR), '')) LIKE ?
                    OR LOWER(COALESCE(CAST(specialization AS VARCHAR), '')) LIKE ?
                    OR LOWER(COALESCE(CAST(normalized_city AS VARCHAR), '')) LIKE ?
                    OR LOWER(COALESCE(CAST(company_id AS VARCHAR), '')) LIKE ?
                )""")
                like_pat = f"%{search_lower}%"
                params.extend([like_pat, like_pat, like_pat, like_pat, like_pat])

        if state:
            where_clauses.append("UPPER(COALESCE(state, '')) = ?")
            params.append(state.upper())

        if metro_hub and metro_hub.upper() in METRO_HUBS:
            hub = METRO_HUBS[metro_hub.upper()]
            states_ph = ",".join(["?"] * len(hub["states"]))
            cities_ph = ",".join(["?"] * len(hub["cities"]))
            where_clauses.append(f"""(
                UPPER(COALESCE(state, '')) IN ({states_ph}) 
                AND LOWER(COALESCE(normalized_city, '')) IN ({cities_ph})
            )""")
            params.extend(hub["states"])
            params.extend(hub["cities"])

        if company_id is not None:
            where_clauses.append("CAST(company_id AS VARCHAR) = ?")
            params.append(str(company_id))

        if company_key:
            where_clauses.append("CAST(company_id AS VARCHAR) = ?")
            params.append(str(company_key))

        if specialization:
            where_clauses.append("LOWER(COALESCE(specialization, '')) LIKE ?")
            params.append(f"%{specialization.lower()}%")

        if specialization_sector:
            where_clauses.append("LOWER(COALESCE(specialization, '')) LIKE ?")
            params.append(f"%{specialization_sector.lower()}%")

        if seniority_level:
            where_clauses.append("seniority_level = ?")
            params.append(seniority_level)

        if timezone_code:
            where_clauses.append("timezone_code = ?")
            params.append(timezone_code.upper())

        if company_scale:
            where_clauses.append("company_scale = ?")
            params.append(company_scale)

        if is_deliverable is not None:
            where_clauses.append("is_deliverable = ?")
            params.append(is_deliverable)

        if has_phone is True:
            where_clauses.append("phone IS NOT NULL AND phone != ''")
        elif has_phone is False:
            where_clauses.append("(phone IS NULL OR phone = '')")

        if is_active is not None:
            where_clauses.append("is_active = ?")
            params.append(is_active)

        if needs_review is not None:
            where_clauses.append("needs_review = ?")
            params.append(needs_review)

        if email_status:
            where_clauses.append("email_status = ?")
            params.append(email_status)

        if data_source:
            where_clauses.append("data_source = ?")
            params.append(data_source)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Count
        cur = self._conn.cursor()
        count_sql = f"SELECT COUNT(*) FROM recruiters WHERE {where_sql}"
        total_count = cur.execute(count_sql, params).fetchone()[0]

        # Sort
        valid_sorts = {
            "created_at": "created_at",
            "name": "recruiter_name",
            "company": "company_id",
            "state": "state",
            "completeness": "completeness_score",
            "last_scan_at": "last_scan_at",
        }
        sort_col = valid_sorts.get(sort_by, "created_at")
        sort_dir = "DESC" if sort_desc else "ASC"

        offset = (page - 1) * limit
        query_sql = f"""
            SELECT * FROM recruiters 
            WHERE {where_sql}
            ORDER BY {sort_col} {sort_dir} NULLS LAST
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        df = cur.execute(query_sql, params).fetchdf()
        results = self._df_to_dict(df)

        return results, total_count

    def search(
        self,
        q: str,
        company: Optional[str] = None,
        location: Optional[str] = None,
        specialization: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Smart search across recruiter name, email, company, specialization.
        Returns ranked results.
        """
        self._ensure_loaded()
        q_lower = q.lower()
        q_like = f"%{q_lower}%"

        where_parts = ["""(
            LOWER(COALESCE(recruiter_name, '')) LIKE ?
            OR LOWER(COALESCE(title, '')) LIKE ?
            OR LOWER(COALESCE(company_id, '')) LIKE ?
            OR LOWER(COALESCE(canonical_company_id, '')) LIKE ?
            OR LOWER(COALESCE(email, '')) LIKE ?
            OR LOWER(COALESCE(phone, '')) LIKE ?
            OR LOWER(COALESCE(specialization, '')) LIKE ?
            OR LOWER(COALESCE(taxonomy_category, '')) LIKE ?
        )"""]
        params = [q_like] * 8

        if company:
            where_parts.append("(LOWER(COALESCE(company_id,'')) LIKE ? OR LOWER(COALESCE(canonical_company_id,'')) LIKE ?)")
            params.extend([f"%{company.lower()}%", f"%{company.lower()}%"])

        if location:
            where_parts.append("UPPER(COALESCE(state, '')) = ?")
            params.append(location.upper()[:2])

        if specialization:
            where_parts.append("(LOWER(COALESCE(specialization, '')) LIKE ? OR LOWER(COALESCE(taxonomy_category, '')) LIKE ?)")
            params.extend([f"%{specialization.lower()}%", f"%{specialization.lower()}%"])

        where_sql = " AND ".join(where_parts)

        # Score-based ranking
        sql = f"""
            SELECT *,
                (CASE WHEN LOWER(COALESCE(recruiter_name,'')) = ? THEN 200
                      WHEN LOWER(COALESCE(recruiter_name,'')) LIKE ? || '%' THEN 130
                      WHEN LOWER(COALESCE(recruiter_name,'')) LIKE ? THEN 100
                      ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(email,'')) = ? THEN 200
                        WHEN LOWER(COALESCE(email,'')) LIKE ? THEN 80
                        ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(title,'')) LIKE ? THEN 80
                        ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(company_id,'')) LIKE ? OR LOWER(COALESCE(canonical_company_id,'')) LIKE ? THEN 70
                        ELSE 0 END
                 + CASE WHEN LOWER(COALESCE(specialization,'')) LIKE ? THEN 40
                        ELSE 0 END
                 + COALESCE(completeness_score, 0) / 4
                ) AS relevance_score
            FROM recruiters
            WHERE {where_sql}
            ORDER BY relevance_score DESC, completeness_score DESC NULLS LAST
            LIMIT ?
        """
        score_params = [q_lower, q_lower, q_like, q_lower, q_like, q_like, q_like, q_like, q_like]
        all_params = score_params + params + [limit]

        cur = self._conn.cursor()
        df = cur.execute(sql, all_params).fetchdf()
        return self._df_to_dict(df)

    def count_by_company(self, company_id: int) -> int:
        """Count recruiters for a given company."""
        self._ensure_loaded()
        cur = self._conn.cursor()
        result = cur.execute(
            "SELECT COUNT(*) FROM recruiters WHERE CAST(company_id AS VARCHAR) = ?", [str(company_id)]
        ).fetchone()
        return result[0] if result else 0

    def company_recruiter_counts_by_ids(self, company_ids: List[int]) -> Dict[int, int]:
        """Get recruiter counts for a specific set of company IDs (targeted fast query)."""
        if not company_ids:
            return {}
        self._ensure_loaded()
        cur = self._conn.cursor()
        str_ids = [str(cid) for cid in company_ids]
        placeholders = ", ".join("?" for _ in str_ids)
        rows = cur.execute(f"""
            SELECT CAST(company_id AS VARCHAR), COUNT(*) as cnt 
            FROM recruiters 
            WHERE CAST(company_id AS VARCHAR) IN ({placeholders})
            GROUP BY CAST(company_id AS VARCHAR)
        """, str_ids).fetchall()
        result = {}
        for r in rows:
            if r[0] is not None:
                try:
                    result[int(r[0])] = int(r[1])
                except (ValueError, TypeError):
                    pass
        return result

    def company_recruiter_counts(self) -> Dict[int, int]:
        """Get recruiter counts for all companies (cached with 60s TTL)."""
        now = time.time()
        if hasattr(self, '_counts_cache') and self._counts_cache and (now - getattr(self, '_counts_cache_time', 0)) < 60:
            return self._counts_cache

        self._ensure_loaded()
        cur = self._conn.cursor()
        rows = cur.execute("""
            SELECT CAST(company_id AS VARCHAR), COUNT(*) as cnt 
            FROM recruiters 
            WHERE company_id IS NOT NULL
            GROUP BY CAST(company_id AS VARCHAR)
        """).fetchall()
        result = {}
        for r in rows:
            if r[0] is not None:
                try:
                    result[int(r[0])] = int(r[1])
                except (ValueError, TypeError):
                    pass
        self._counts_cache = result
        self._counts_cache_time = now
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        self._ensure_loaded()
        stats = {
            "total_recruiters": self._record_count,
            "loaded": self._loaded,
            "last_load_time": self._last_load_time,
            "parquet_file": PARQUET_FILE,
            "parquet_exists": os.path.exists(PARQUET_FILE),
        }
        if self._loaded and self._conn:
            cur = self._conn.cursor()
            stats["with_company"] = cur.execute(
                "SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL"
            ).fetchone()[0]
            stats["with_phone"] = cur.execute(
                "SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL AND phone != ''"
            ).fetchone()[0]
            stats["email_status_breakdown"] = dict(
                cur.execute(
                    "SELECT COALESCE(email_status, 'unknown'), COUNT(*) FROM recruiters GROUP BY email_status"
                ).fetchall()
            )
        return stats


    def export_recruiters_csv(
        self,
        search: Optional[str] = None,
        state: Optional[str] = None,
        company_id: Optional[int] = None,
        company_key: Optional[str] = None,
        specialization: Optional[str] = None,
        has_phone: Optional[bool] = None,
        recruiter_ids: Optional[List[int]] = None,
        limit: int = 10000
    ) -> str:
        """Stream matching recruiters directly from DuckDB into RFC 4180 CSV with safe memory limits."""
        self._ensure_loaded()
        import io
        import csv

        # Bombproof limit boundary: Never exceed 50,000 in a single export
        safe_limit = max(1, min(int(limit or 10000), 50000))
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "Recruiter ID", "Full Name", "Title", "Company", "Email",
            "Phone", "Location", "State", "Specialization", "LinkedIn", "Quality Score"
        ])
        
        try:
            if recruiter_ids:
                safe_ids = [int(i) for i in recruiter_ids[:safe_limit] if str(i).isdigit()]
                if not safe_ids:
                    return output.getvalue()
                cur = self._conn.cursor()
                placeholders = ",".join(["?"] * len(safe_ids))
                query = f"""
                    SELECT recruiter_id, recruiter_name, title, company_id, email, phone, location, state, specialization, linkedin, quality_score
                    FROM recruiters
                    WHERE recruiter_id IN ({placeholders})
                    ORDER BY quality_score DESC, recruiter_id ASC
                    LIMIT ?
                """
                params = list(safe_ids) + [safe_limit]
                df = cur.execute(query, params).fetchdf()
                results = self._df_to_dict(df)
            else:
                results, _ = self.list_recruiters(
                    page=1,
                    limit=safe_limit,
                    search=search,
                    state=state,
                    company_id=company_id,
                    company_key=company_key,
                    specialization=specialization,
                    has_phone=has_phone
                )
            
            for r in results:
                writer.writerow([
                    r.get("recruiter_id", ""),
                    r.get("recruiter_name", ""),
                    r.get("title", ""),
                    r.get("company_id", ""),
                    r.get("email", ""),
                    r.get("phone", ""),
                    r.get("location", ""),
                    r.get("state", ""),
                    r.get("specialization", ""),
                    r.get("linkedin", ""),
                    r.get("quality_score", "")
                ])
        except Exception as e:
            logger.error(f"Error during CSV export: {e}")
            
        return output.getvalue()


# Singleton instance
recruiter_store = RecruiterStore()

