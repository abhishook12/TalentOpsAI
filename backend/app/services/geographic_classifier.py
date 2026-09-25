"""
geographic_classifier.py — Deterministic Multi-Signal Geographic Classifier.

Classifies candidate geography using 6 signal layers:
  1. Location String Parsing (weight: 0.45)
  2. Phone Prefix Analysis  (weight: 0.15)
  3. Email TLD Inference     (weight: 0.10)
  4. Name-Origin Heuristics  (weight: 0.10)
  5. Company HQ Mapping      (weight: 0.10)
  6. LinkedIn Locale Hints   (weight: 0.10)

Geographic Rule: 90% North America, 10% UK + South America, 0% Other.

Zero external dependencies — pure deterministic pattern matching.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple

from ..config import (
    GEO_FILTER_ENABLED,
    GEO_NA_TARGET_PERCENT,
    GEO_ALLOWED_REGIONS,
    GEO_MIN_CONFIDENCE,
    GEO_REJECT_UNKNOWN,
)

logger = logging.getLogger("talentops.geo_classifier")

# ─── Region Constants ─────────────────────────────────────────────────
NORTH_AMERICA = "NORTH_AMERICA"
UK = "UK"
SOUTH_AMERICA = "SOUTH_AMERICA"
OTHER = "OTHER"
UNKNOWN = "UNKNOWN"

# ─── Signal Weights ───────────────────────────────────────────────────
W_LOCATION = 0.45
W_PHONE = 0.15
W_EMAIL_TLD = 0.10
W_NAME = 0.10
W_COMPANY = 0.10
W_LINKEDIN = 0.10

# ─── Location Dictionaries ───────────────────────────────────────────

# US States (full names, lowercase)
US_STATES = frozenset({
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
})

# US State postal abbreviations
US_STATE_CODES = frozenset({
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi",
    "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi",
    "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc",
    "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
    "vt", "va", "wa", "wv", "wi", "wy", "dc",
})

# Canadian Provinces
CA_PROVINCES = frozenset({
    "ontario", "quebec", "québec", "british columbia", "alberta",
    "manitoba", "saskatchewan", "nova scotia", "new brunswick",
    "prince edward island", "newfoundland", "newfoundland and labrador",
    "northwest territories", "yukon", "nunavut",
})
CA_PROVINCE_CODES = frozenset({
    "on", "qc", "bc", "ab", "mb", "sk", "ns", "nb", "pe", "nl", "nt", "yt", "nu",
})

# Major North American cities
NA_MAJOR_CITIES = frozenset({
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "san jose", "austin", "jacksonville",
    "fort worth", "columbus", "charlotte", "indianapolis", "san francisco",
    "seattle", "denver", "washington", "nashville", "oklahoma city",
    "el paso", "boston", "portland", "las vegas", "memphis", "louisville",
    "baltimore", "milwaukee", "albuquerque", "tucson", "fresno", "mesa",
    "sacramento", "atlanta", "kansas city", "omaha", "raleigh", "miami",
    "minneapolis", "tampa", "new orleans", "cleveland", "pittsburgh",
    "st louis", "st. louis", "detroit", "cincinnati", "orlando",
    "salt lake city", "richmond", "boise", "des moines",
    # DFW, Bay Area, etc.
    "silicon valley", "bay area", "sf bay", "dallas-fort worth",
    "raleigh-durham", "chapel hill", "research triangle",
    # Canadian major cities
    "toronto", "vancouver", "montreal", "montréal", "calgary", "ottawa",
    "edmonton", "winnipeg", "quebec city", "hamilton", "kitchener",
    "waterloo", "halifax", "victoria", "saskatoon", "regina",
})

# North American country-level keywords
NA_COUNTRY_KEYWORDS = frozenset({
    "united states", "usa", "u.s.", "u.s.a.", "america",
    "canada", "canadian", "mexico",
})

# UK regions, cities, and keywords
UK_REGIONS = frozenset({
    "england", "scotland", "wales", "northern ireland",
    "london", "manchester", "birmingham", "leeds", "glasgow",
    "liverpool", "bristol", "sheffield", "edinburgh", "cardiff",
    "belfast", "newcastle", "nottingham", "southampton", "leicester",
    "brighton", "coventry", "reading", "aberdeen", "cambridge",
    "oxford", "bath", "exeter", "york", "canterbury", "dundee",
    "swansea", "derby", "portsmouth", "wolverhampton", "stoke-on-trent",
    "sunderland", "plymouth",
})
UK_COUNTRY_KEYWORDS = frozenset({
    "united kingdom", "u.k.", "great britain", "britain", "british",
})

# South American countries and major cities
SA_COUNTRIES = frozenset({
    "brazil", "brasil", "argentina", "colombia", "peru", "perú",
    "chile", "venezuela", "ecuador", "bolivia", "paraguay", "uruguay",
    "guyana", "suriname", "french guiana",
})
SA_MAJOR_CITIES = frozenset({
    "são paulo", "sao paulo", "rio de janeiro", "buenos aires", "bogotá",
    "bogota", "lima", "santiago", "caracas", "quito", "montevideo",
    "medellín", "medellin", "cali", "barranquilla", "recife", "salvador",
    "fortaleza", "belo horizonte", "brasília", "brasilia", "curitiba",
    "porto alegre", "manaus", "belém", "belem", "guadalajara",
    "monterrey", "puebla",
})
SA_COUNTRY_KEYWORDS = frozenset({
    "south america", "latin america", "latam", "brazilian", "colombian",
    "argentine", "argentinian", "peruvian", "chilean", "venezuelan",
    "ecuadorian", "bolivian", "paraguayan", "uruguayan",
})

# "Greater ... Area" pattern
GREATER_AREA_RE = re.compile(r"greater\s+(.+?)\s+area", re.IGNORECASE)
# "City, ST" US postal pattern
CITY_STATE_RE = re.compile(r"^([A-Za-z\s.-]+),\s*([A-Z]{2})$")
# "City, Country" pattern
CITY_COUNTRY_RE = re.compile(r"^([A-Za-z\s.\u00C0-\u024F-]+),\s*(.+)$")

# ─── Phone Prefix → Region ───────────────────────────────────────────
PHONE_REGION_MAP = {
    "+1": NORTH_AMERICA, "1": NORTH_AMERICA,
    "+44": UK, "44": UK,
    "+55": SOUTH_AMERICA, "+54": SOUTH_AMERICA, "+56": SOUTH_AMERICA,
    "+57": SOUTH_AMERICA, "+51": SOUTH_AMERICA, "+58": SOUTH_AMERICA,
    "+52": SOUTH_AMERICA, "+593": SOUTH_AMERICA, "+591": SOUTH_AMERICA,
    "+595": SOUTH_AMERICA, "+598": SOUTH_AMERICA,
}

# ─── Email TLD → Region ──────────────────────────────────────────────
TLD_REGION_MAP = {
    ".com": NORTH_AMERICA,  # weak — US default but not definitive
    ".us": NORTH_AMERICA,
    ".ca": NORTH_AMERICA,
    ".mx": SOUTH_AMERICA,
    ".co.uk": UK,
    ".uk": UK,
    ".org.uk": UK,
    ".ac.uk": UK,
    ".br": SOUTH_AMERICA,
    ".ar": SOUTH_AMERICA,
    ".cl": SOUTH_AMERICA,
    ".co": SOUTH_AMERICA,  # Colombia TLD
    ".pe": SOUTH_AMERICA,
    ".ve": SOUTH_AMERICA,
    ".ec": SOUTH_AMERICA,
    ".uy": SOUTH_AMERICA,
    ".py": SOUTH_AMERICA,
}

# ─── Company HQ → Region (Top companies) ─────────────────────────────
COMPANY_HQ_MAP = {
    # North America
    "google": NORTH_AMERICA, "microsoft": NORTH_AMERICA, "apple": NORTH_AMERICA,
    "amazon": NORTH_AMERICA, "meta": NORTH_AMERICA, "netflix": NORTH_AMERICA,
    "salesforce": NORTH_AMERICA, "oracle": NORTH_AMERICA, "ibm": NORTH_AMERICA,
    "cisco": NORTH_AMERICA, "intel": NORTH_AMERICA, "nvidia": NORTH_AMERICA,
    "adobe": NORTH_AMERICA, "uber": NORTH_AMERICA, "airbnb": NORTH_AMERICA,
    "stripe": NORTH_AMERICA, "spotify": NORTH_AMERICA, "twitter": NORTH_AMERICA,
    "linkedin": NORTH_AMERICA, "indeed": NORTH_AMERICA, "walmart": NORTH_AMERICA,
    "jpmorgan": NORTH_AMERICA, "goldman sachs": NORTH_AMERICA,
    "morgan stanley": NORTH_AMERICA, "bank of america": NORTH_AMERICA,
    "wells fargo": NORTH_AMERICA, "citigroup": NORTH_AMERICA,
    "deloitte": NORTH_AMERICA, "pwc": NORTH_AMERICA, "ey": NORTH_AMERICA,
    "kpmg": NORTH_AMERICA, "accenture": NORTH_AMERICA,
    "robert half": NORTH_AMERICA, "insight global": NORTH_AMERICA,
    "randstad": NORTH_AMERICA, "manpower": NORTH_AMERICA,
    "adecco": NORTH_AMERICA, "kelly services": NORTH_AMERICA,
    "teksystems": NORTH_AMERICA, "kforce": NORTH_AMERICA,
    "allegis": NORTH_AMERICA, "apex systems": NORTH_AMERICA,
    "collabera": NORTH_AMERICA, "aerotek": NORTH_AMERICA,
    "shopify": NORTH_AMERICA, "snowflake": NORTH_AMERICA,
    "datadog": NORTH_AMERICA, "mongodb": NORTH_AMERICA,
    "zoominfo": NORTH_AMERICA, "apollo": NORTH_AMERICA,
    # UK
    "barclays": UK, "hsbc": UK, "bp": UK, "shell": UK,
    "unilever": UK, "glaxosmithkline": UK, "gsk": UK,
    "astrazeneca": UK, "rolls-royce": UK, "vodafone": UK,
    "bt": UK, "bae systems": UK, "tesco": UK, "lloyds": UK,
    "natwest": UK, "standard chartered": UK, "revolut": UK,
    "arm": UK, "deliveroo": UK, "wise": UK, "monzo": UK,
    # South America
    "mercadolibre": SOUTH_AMERICA, "mercado libre": SOUTH_AMERICA,
    "nubank": SOUTH_AMERICA, "rappi": SOUTH_AMERICA,
    "globant": SOUTH_AMERICA, "despegar": SOUTH_AMERICA,
    "vtex": SOUTH_AMERICA, "totvs": SOUTH_AMERICA,
    "stone": SOUTH_AMERICA, "pagseguro": SOUTH_AMERICA,
    "itaú": SOUTH_AMERICA, "itau": SOUTH_AMERICA,
    "bradesco": SOUTH_AMERICA, "petrobras": SOUTH_AMERICA,
    "embraer": SOUTH_AMERICA, "vale": SOUTH_AMERICA,
}

# ─── Name-Origin Heuristics (Secondary Signal ONLY) ──────────────────

# Common Hispanic/Latino surname suffixes (boost SA confidence)
HISPANIC_SURNAME_SUFFIXES = (
    "ez", "oz", "az", "iz", "uz",  # Gonzalez, Muñoz, Diaz, Ruiz
    "ón", "on",  # Ramón (when combined with other signals)
)
HISPANIC_SURNAME_PATTERNS = re.compile(
    r"(?:gonzal|rodrigu|hernand|fernand|lopez|garcia|martinez|ramir|sanch|"
    r"torres|rivera|flores|gomez|diaz|reyes|morales|jimenez|ruiz|"
    r"alvarez|mendoza|castillo|vargas|romero|perez|moreno|medina|"
    r"guzman|herrera|vasquez|ortiz|ramos|delgado|silva|santos|"
    r"oliveira|souza|costa|ferreira|almeida|nascimento|pereira|"
    r"carvalho|ribeiro|lima|rocha|araujo|monteiro|barros)",
    re.IGNORECASE,
)

# Common Anglo/American first name patterns (boost NA confidence)
ANGLO_FIRST_NAMES = frozenset({
    "james", "john", "robert", "michael", "david", "william", "richard",
    "joseph", "thomas", "christopher", "charles", "daniel", "matthew",
    "anthony", "mark", "donald", "steven", "paul", "andrew", "joshua",
    "kenneth", "kevin", "brian", "george", "timothy", "ronald", "edward",
    "jason", "jeffrey", "ryan", "jacob", "gary", "nicholas", "eric",
    "jonathan", "stephen", "larry", "justin", "scott", "brandon", "benjamin",
    "samuel", "raymond", "gregory", "frank", "alexander", "patrick", "jack",
    "mary", "patricia", "jennifer", "linda", "barbara", "elizabeth", "susan",
    "jessica", "sarah", "karen", "lisa", "nancy", "betty", "margaret",
    "sandra", "ashley", "dorothy", "kimberly", "emily", "donna", "michelle",
    "carol", "amanda", "melissa", "deborah", "stephanie", "rebecca", "sharon",
    "laura", "cynthia", "kathleen", "amy", "angela", "shirley", "anna",
    "brenda", "pamela", "emma", "nicole", "helen", "samantha", "katherine",
    "christine", "debra", "rachel", "carolyn", "janet", "catherine", "maria",
    "heather", "diane", "ruth", "julie", "olivia", "joyce", "virginia",
    "victoria", "kelly", "lauren", "christina", "joan", "evelyn", "judith",
    "megan", "andrea", "cheryl", "hannah", "jacqueline", "martha", "gloria",
    "teresa", "ann", "sara", "madison", "frances", "kathryn", "janice",
    "jean", "abigail", "alice", "judy", "sophia", "grace", "denise",
    "amber", "doris", "marilyn", "danielle", "beverly", "isabella",
    "theresa", "diana", "natalie", "brittany", "charlotte", "marie",
    "kayla", "alexis", "lori", "chad", "brad", "brett", "blake", "tyler",
    "connor", "cole", "chase", "hunter", "logan", "dylan", "austin",
    "mason", "ethan", "noah", "liam", "aiden", "jackson", "lucas",
    "wyatt", "caleb", "nathan", "owen", "carter", "luke", "landon",
    "eli", "gavin", "brayden", "colton", "cooper", "tanner", "brody",
})

# British first names (more distinctive than just Anglo)
BRITISH_FIRST_NAMES = frozenset({
    "alistair", "alastair", "angus", "archie", "barnaby", "callum",
    "clive", "colin", "duncan", "ewan", "fergus", "finlay", "fraser",
    "gareth", "graham", "hamish", "ian", "iain", "kieran", "lachlan",
    "nigel", "oliver", "owen", "rupert", "sebastian", "siobhan",
    "stuart", "trevor", "nigel", "pippa", "imogen", "gemma", "fiona",
    "millie", "poppy", "rosie", "harriet", "florence", "freya",
    "isla", "maisie",
})


@dataclass
class GeoClassification:
    """Result of geographic classification."""
    region: str = UNKNOWN
    confidence: float = 0.0
    signals: Dict[str, str] = field(default_factory=dict)
    passes_filter: bool = True
    rejection_reason: str = ""


class GeographicClassifier:
    """
    Deterministic, zero-dependency geographic classifier.
    Uses 6 signal layers to determine candidate region.
    """

    def classify(
        self,
        raw_location: Optional[str] = None,
        raw_name: Optional[str] = None,
        raw_email: Optional[str] = None,
        raw_phone: Optional[str] = None,
        raw_linkedin: Optional[str] = None,
        raw_company: Optional[str] = None,
    ) -> GeoClassification:
        """
        Classifies a candidate's geographic region using all available signals.
        Returns a GeoClassification with region, confidence, and contributing signals.
        """
        scores: Dict[str, float] = {
            NORTH_AMERICA: 0.0,
            UK: 0.0,
            SOUTH_AMERICA: 0.0,
            OTHER: 0.0,
        }
        signals: Dict[str, str] = {}

        # ── Signal 1: Location String (weight: 0.45) ──
        loc_region = self._parse_location(raw_location)
        if loc_region and loc_region != UNKNOWN:
            scores[loc_region] += W_LOCATION
            signals["location"] = f"{loc_region} (from '{raw_location}')"

        # ── Signal 2: Phone Prefix (weight: 0.15) ──
        phone_region = self._infer_from_phone(raw_phone)
        if phone_region and phone_region != UNKNOWN:
            scores[phone_region] += W_PHONE
            signals["phone"] = f"{phone_region} (from '{raw_phone}')"

        # ── Signal 3: Email TLD (weight: 0.10) ──
        email_region = self._infer_from_email_tld(raw_email)
        if email_region and email_region != UNKNOWN:
            scores[email_region] += W_EMAIL_TLD
            signals["email_tld"] = f"{email_region} (from '{raw_email}')"

        # ── Signal 4: Name Origin (weight: 0.10) ──
        name_region, name_detail = self._infer_from_name(raw_name)
        if name_region and name_region != UNKNOWN:
            scores[name_region] += W_NAME
            signals["name_origin"] = f"{name_region} ({name_detail})"

        # ── Signal 5: Company HQ (weight: 0.10) ──
        company_region = self._infer_from_company(raw_company)
        if company_region and company_region != UNKNOWN:
            scores[company_region] += W_COMPANY
            signals["company_hq"] = f"{company_region} (from '{raw_company}')"

        # ── Signal 6: LinkedIn Locale (weight: 0.10) ──
        linkedin_region = self._infer_from_linkedin(raw_linkedin)
        if linkedin_region and linkedin_region != UNKNOWN:
            scores[linkedin_region] += W_LINKEDIN
            signals["linkedin"] = f"{linkedin_region}"

        # ── Determine winner ──
        max_score = max(scores.values())
        if max_score < GEO_MIN_CONFIDENCE:
            return GeoClassification(
                region=UNKNOWN,
                confidence=max_score,
                signals=signals,
                passes_filter=not GEO_REJECT_UNKNOWN,
                rejection_reason="below_confidence_threshold" if GEO_REJECT_UNKNOWN else "",
            )

        winning_region = max(scores, key=scores.get)

        # ── Apply filter ──
        passes = True
        rejection_reason = ""
        if GEO_FILTER_ENABLED:
            if winning_region not in GEO_ALLOWED_REGIONS:
                passes = False
                rejection_reason = f"region_{winning_region}_not_allowed"

        return GeoClassification(
            region=winning_region,
            confidence=round(max_score, 3),
            signals=signals,
            passes_filter=passes,
            rejection_reason=rejection_reason,
        )

    def _parse_location(self, raw_location: Optional[str]) -> str:
        """Parse location string to determine geographic region."""
        if not raw_location or not isinstance(raw_location, str):
            return UNKNOWN

        loc = raw_location.strip().lower()
        if len(loc) < 2:
            return UNKNOWN

        # ── Check "Greater ... Area" pattern ──
        greater_m = GREATER_AREA_RE.search(loc)
        if greater_m:
            city = greater_m.group(1).strip().lower()
            if city in NA_MAJOR_CITIES or any(s in city for s in US_STATES):
                return NORTH_AMERICA
            if city in UK_REGIONS:
                return UK
            if city in SA_MAJOR_CITIES:
                return SOUTH_AMERICA

        # ── Check "City, ST" US postal ──
        city_state_m = CITY_STATE_RE.match(raw_location.strip())
        if city_state_m:
            state_code = city_state_m.group(2).lower()
            if state_code in US_STATE_CODES:
                return NORTH_AMERICA
            if state_code in CA_PROVINCE_CODES:
                return NORTH_AMERICA

        # ── Check "City, Country" ──
        city_country_m = CITY_COUNTRY_RE.match(raw_location.strip())
        if city_country_m:
            country_part = city_country_m.group(2).strip().lower()
            city_part = city_country_m.group(1).strip().lower()
            # Check country part
            if country_part in US_STATES or country_part in NA_COUNTRY_KEYWORDS:
                return NORTH_AMERICA
            if country_part in CA_PROVINCES:
                return NORTH_AMERICA
            if country_part in UK_COUNTRY_KEYWORDS or country_part in UK_REGIONS:
                return UK
            if country_part in SA_COUNTRIES or country_part in SA_COUNTRY_KEYWORDS:
                return SOUTH_AMERICA
            # Check city part
            if city_part in NA_MAJOR_CITIES:
                return NORTH_AMERICA
            if city_part in UK_REGIONS:
                return UK
            if city_part in SA_MAJOR_CITIES:
                return SOUTH_AMERICA

        # ── Word boundary checks for common abbreviations ──
        if re.search(r"\b(us|usa)\b", loc):
            return NORTH_AMERICA
        if re.search(r"\b(uk)\b", loc):
            return UK

        # ── Direct keyword matches ──
        for keyword in NA_COUNTRY_KEYWORDS:
            if keyword in loc:
                return NORTH_AMERICA
        for state in US_STATES:
            if state in loc:
                return NORTH_AMERICA
        for city in NA_MAJOR_CITIES:
            if city in loc:
                return NORTH_AMERICA
        for province in CA_PROVINCES:
            if province in loc:
                return NORTH_AMERICA

        for keyword in UK_COUNTRY_KEYWORDS:
            if keyword in loc:
                return UK
        for region in UK_REGIONS:
            if region in loc:
                return UK

        for country in SA_COUNTRIES:
            if country in loc:
                return SOUTH_AMERICA
        for city in SA_MAJOR_CITIES:
            if city in loc:
                return SOUTH_AMERICA
        for keyword in SA_COUNTRY_KEYWORDS:
            if keyword in loc:
                return SOUTH_AMERICA

        # ── If no match, check if it looks like a non-target region ──
        non_target_indicators = {
            "india", "china", "japan", "korea", "singapore", "philippines",
            "indonesia", "malaysia", "thailand", "vietnam", "taiwan",
            "hong kong", "pakistan", "bangladesh", "sri lanka", "nepal",
            "germany", "france", "netherlands", "spain", "italy",
            "switzerland", "sweden", "norway", "denmark", "finland",
            "austria", "belgium", "poland", "czech", "romania", "hungary",
            "portugal", "greece", "turkey", "russia", "ukraine",
            "israel", "uae", "dubai", "saudi", "qatar", "egypt",
            "nigeria", "kenya", "south africa", "ghana", "morocco",
            "australia", "new zealand", "sydney", "melbourne",
            "mumbai", "bangalore", "bengaluru", "hyderabad", "pune",
            "chennai", "delhi", "noida", "gurgaon", "kolkata",
            "ahmedabad", "karnataka", "tamil nadu", "maharashtra",
            "berlin", "paris", "amsterdam", "munich", "frankfurt",
            "zurich", "stockholm", "oslo", "copenhagen", "vienna",
            "brussels", "warsaw", "prague", "budapest", "dublin",
            "lisbon", "barcelona", "milan", "rome", "tokyo",
            "seoul", "beijing", "shanghai", "shenzhen",
        }
        for ind in non_target_indicators:
            if ind in loc:
                return OTHER

        return UNKNOWN

    def _infer_from_phone(self, raw_phone: Optional[str]) -> str:
        """Infer region from phone number prefix."""
        if not raw_phone or not isinstance(raw_phone, str):
            return UNKNOWN

        phone = raw_phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Check for international prefix
        for prefix, region in sorted(PHONE_REGION_MAP.items(), key=lambda x: -len(x[0])):
            if phone.startswith(prefix):
                return region

        # US/Canada numbers without +1: 10-digit starting with area code
        digits_only = re.sub(r"\D", "", phone)
        if len(digits_only) == 10 or (len(digits_only) == 11 and digits_only[0] == "1"):
            return NORTH_AMERICA

        return UNKNOWN

    def _infer_from_email_tld(self, raw_email: Optional[str]) -> str:
        """Infer region from email domain TLD."""
        if not raw_email or "@" not in raw_email:
            return UNKNOWN

        domain = raw_email.split("@")[-1].lower().strip()

        # Check multi-part TLDs first (e.g., .co.uk)
        for tld, region in sorted(TLD_REGION_MAP.items(), key=lambda x: -len(x[0])):
            if domain.endswith(tld):
                # .com is too ambiguous — only use if no other signal
                if tld == ".com":
                    return UNKNOWN  # Intentionally skip .com — too weak
                return region

        return UNKNOWN

    def _infer_from_name(self, raw_name: Optional[str]) -> Tuple[str, str]:
        """
        Infer region from name patterns.
        IMPORTANT: This is a SECONDARY signal only — never the sole rejection reason.
        Returns (region, detail_string).
        """
        if not raw_name or not isinstance(raw_name, str):
            return UNKNOWN, ""

        name_parts = raw_name.strip().lower().split()
        if len(name_parts) < 2:
            return UNKNOWN, ""

        first_name = name_parts[0]
        last_name = name_parts[-1]

        # Check Hispanic/Latino surname patterns → SOUTH_AMERICA
        if HISPANIC_SURNAME_PATTERNS.search(last_name):
            return SOUTH_AMERICA, f"hispanic_surname:{last_name}"

        # Check common Anglo first names → NORTH_AMERICA
        if first_name in ANGLO_FIRST_NAMES:
            return NORTH_AMERICA, f"anglo_first:{first_name}"

        # Check British first names → UK
        if first_name in BRITISH_FIRST_NAMES:
            return UK, f"british_first:{first_name}"

        return UNKNOWN, ""

    def _infer_from_company(self, raw_company: Optional[str]) -> str:
        """Infer region from known company HQ location."""
        if not raw_company or not isinstance(raw_company, str):
            return UNKNOWN

        company_lower = raw_company.strip().lower()
        # Direct lookup
        if company_lower in COMPANY_HQ_MAP:
            return COMPANY_HQ_MAP[company_lower]

        # Partial match (e.g., "Google Inc." → "google")
        for key, region in COMPANY_HQ_MAP.items():
            if key in company_lower or company_lower.startswith(key):
                return region

        return UNKNOWN

    def _infer_from_linkedin(self, raw_linkedin: Optional[str]) -> str:
        """Infer region from LinkedIn URL patterns (limited signal)."""
        if not raw_linkedin or not isinstance(raw_linkedin, str):
            return UNKNOWN

        url = raw_linkedin.strip().lower()

        # Some LinkedIn URLs contain locale hints
        if "linkedin.com/in/" in url:
            # Extract slug
            slug_match = re.search(r"linkedin\.com/in/([^/?]+)", url)
            if slug_match:
                slug = slug_match.group(1)
                # Locale suffixes like -br, -uk are sometimes appended
                if slug.endswith("-br") or slug.endswith("-brazil"):
                    return SOUTH_AMERICA
                if slug.endswith("-uk"):
                    return UK

        return UNKNOWN


# ── Module-level singleton ──
geo_classifier = GeographicClassifier()
