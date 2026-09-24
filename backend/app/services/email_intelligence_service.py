"""
email_intelligence_service.py — Corporate Email Pattern Prediction & MX Verification Engine.

Functions:
1. Intelligent Name Tokenizer: Parses multi-part, international, and prefixed human names.
2. Corporate Domain Normalizer: Maps corporate entities and DB companies to canonical mail domains.
3. Permutation Generator: Generates standard corporate formulas (first.last, first, f_last, etc.).
4. DNS MX Verifier: Non-blocking DNS mail exchanger verification with provider fingerprinting.
5. Self-Learning Pattern Miner: Automatically deduces company patterns from observed candidate emails.
6. Candidate Resolver: End-to-end enrichment for candidates with missing contact details.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import dns.resolver
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..models.models import Company, CompanyEmailPattern

logger = logging.getLogger("talentops.email_intel")

# ── High-Frequency Company to Primary Domain Mapping ──────────────────────────
# Top tech, global enterprise, Indian IT/unicorns, and consulting firms
KNOWN_COMPANY_DOMAINS: Dict[str, str] = {
    "google": "google.com",
    "alphabet": "google.com",
    "microsoft": "microsoft.com",
    "amazon": "amazon.com",
    "aws": "amazon.com",
    "apple": "apple.com",
    "meta": "meta.com",
    "facebook": "meta.com",
    "netflix": "netflix.com",
    "stripe": "stripe.com",
    "uber": "uber.com",
    "airbnb": "airbnb.com",
    "salesforce": "salesforce.com",
    "adobe": "adobe.com",
    "spotify": "spotify.com",
    "oracle": "oracle.com",
    "ibm": "ibm.com",
    "cisco": "cisco.com",
    "intel": "intel.com",
    "nvidia": "nvidia.com",
    "tesla": "tesla.com",
    "twitter": "x.com",
    "x": "x.com",
    "linkedin": "linkedin.com",
    "datadog": "datadoghq.com",
    "snowflake": "snowflake.com",
    "palantir": "palantir.com",
    "openai": "openai.com",
    "anthropic": "anthropic.com",
    "cloudflare": "cloudflare.com",
    "figma": "figma.com",
    "notion": "makenotion.com",
    "canva": "canva.com",
    "atlassian": "atlassian.com",
    "slack": "slack-corp.com",
    "zoom": "zoom.us",
    "mongodb": "mongodb.com",
    "github": "github.com",
    "gitlab": "gitlab.com",
    "dropbox": "dropbox.com",
    "hubspot": "hubspot.com",
    "twilio": "twilio.com",
    "shopify": "shopify.com",
    "doordash": "doordash.com",
    "instacart": "instacart.com",
    "coinbase": "coinbase.com",
    "robinhood": "robinhood.com",
    "plaid": "plaid.com",
    "brex": "brex.com",
    "ramp": "ramp.com",
    # India Tech & Unicorns
    "zomato": "zomato.com",
    "swiggy": "swiggy.in",
    "flipkart": "flipkart.com",
    "ola": "olacabs.com",
    "paytm": "paytm.com",
    "razorpay": "razorpay.com",
    "cred": "cred.club",
    "zepto": "zeptonow.com",
    "blinkit": "blinkit.com",
    "meesho": "meesho.com",
    "phonepe": "phonepe.com",
    "tcs": "tcs.com",
    "tata consultancy services": "tcs.com",
    "infosys": "infosys.com",
    "wipro": "wipro.com",
    "hcl": "hcltech.com",
    "hcltech": "hcltech.com",
    "tech mahindra": "techmahindra.com",
    "l&t": "larsentoubro.com",
    "larsen & toubro": "larsentoubro.com",
    # Consulting & Finance
    "accenture": "accenture.com",
    "deloitte": "deloitte.com",
    "pwc": "pwc.com",
    "ey": "ey.com",
    "kpmg": "kpmg.com",
    "mckinsey": "mckinsey.com",
    "mckinsey & company": "mckinsey.com",
    "bcg": "bcg.com",
    "boston consulting group": "bcg.com",
    "bain": "bain.com",
    "bain & company": "bain.com",
    "goldman sachs": "gs.com",
    "morgan stanley": "morganstanley.com",
    "jpmorgan": "jpmorgan.com",
    "jp morgan": "jpmorgan.com",
    "jpmorgan chase": "jpmorgan.com",
    "blackrock": "blackrock.com",
}

# ── Seed Company Email Formulas (Known Ground Truth) ──────────────────────────
# Standard patterns: 'first.last', 'first', 'f_last', 'first_last', 'f.last'
SEEDED_COMPANY_PATTERNS: Dict[str, Dict[str, Any]] = {
    "google.com": {"pattern": "first.last", "confidence": 0.90},
    "microsoft.com": {"pattern": "first.last", "confidence": 0.85},
    "amazon.com": {"pattern": "first_last", "confidence": 0.75},
    "apple.com": {"pattern": "first.last", "confidence": 0.80},
    "meta.com": {"pattern": "first", "confidence": 0.70},
    "netflix.com": {"pattern": "first.last", "confidence": 0.85},
    "stripe.com": {"pattern": "first", "confidence": 0.80},
    "uber.com": {"pattern": "first.last", "confidence": 0.85},
    "airbnb.com": {"pattern": "first", "confidence": 0.85},
    "salesforce.com": {"pattern": "first.last", "confidence": 0.80},
    "adobe.com": {"pattern": "first.last", "confidence": 0.80},
    "spotify.com": {"pattern": "first.last", "confidence": 0.85},
    "openai.com": {"pattern": "first", "confidence": 0.85},
    "anthropic.com": {"pattern": "first", "confidence": 0.85},
    "snowflake.com": {"pattern": "first.last", "confidence": 0.85},
    "datadoghq.com": {"pattern": "first.last", "confidence": 0.85},
    "zomato.com": {"pattern": "first.last", "confidence": 0.90},
    "swiggy.in": {"pattern": "first.last", "confidence": 0.85},
    "tcs.com": {"pattern": "first.last", "confidence": 0.80},
    "infosys.com": {"pattern": "first.last", "confidence": 0.85},
    "accenture.com": {"pattern": "first.last", "confidence": 0.90},
    "deloitte.com": {"pattern": "first.last", "confidence": 0.90},
}

# Free / personal webmail domains to exclude from corporate pattern extrapolation
FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "live.com", "msn.com", "protonmail.com", "zoho.com",
    "ymail.com", "mail.com", "gmx.com", "fastmail.com", "inbox.com",
}

# Legal suffixes to clean from company names when resolving domains
COMPANY_LEGAL_SUFFIXES = [
    r"\binc\.?\b", r"\bincorporated\b", r"\bllc\.?\b", r"\bl\.l\.c\.?\b",
    r"\bltd\.?\b", r"\blimited\b", r"\bpvt\.?\s*ltd\.?\b", r"\bprivate\s*limited\b",
    r"\bcorp\.?\b", r"\bcorporation\b", r"\bgmbh\b", r"\bs\.?a\.?\b",
    r"\bco\.?\b", r"\bcompany\b", r"\btechnologies\b", r"\btechnology\b",
    r"\bsoftware\b", r"\bsolutions\b", r"\bsystems\b", r"\bservices\b",
    r"\bglobal\b", r"\bgroup\b", r"\blabs\b", r"\bholdings\b",
]

# Name prefixes and honorifics
NAME_HONORIFICS = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", "prof", "prof.",
    "er", "er.", "adv", "adv.", "sir", "dame", "hon", "hon."
}

# Name suffixes
NAME_SUFFIXES = {
    "jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "phd", "ph.d.", "md", "mba", "cpa", "pmp"
}

# In-memory DNS MX cache (domain -> (has_mx, records, provider, timestamp))
_MX_CACHE: Dict[str, Tuple[bool, List[str], str, float]] = {}
_MX_CACHE_TTL_SEC = 86400  # 24 hours


class EmailIntelligenceService:
    @staticmethod
    def clean_name_tokens(full_name: str) -> Optional[Dict[str, str]]:
        """
        Cleans and tokenizes full names into first, last, and initials.
        Handles prefixes, middle initials, hyphens, and cultural multi-part names.
        """
        if not full_name or not isinstance(full_name, str):
            return None

        # Clean noise characters
        cleaned = re.sub(r"[^\w\s\'-]", " ", full_name).strip()
        tokens = [t for t in cleaned.split() if t]

        if not tokens:
            return None

        # Strip prefixes
        while tokens and tokens[0].lower() in NAME_HONORIFICS:
            tokens.pop(0)

        # Strip suffixes
        while tokens and tokens[-1].lower() in NAME_SUFFIXES:
            tokens.pop()

        if not tokens:
            return None

        # Extract first, middle (if available), and last
        first_raw = tokens[0]
        last_raw = tokens[-1] if len(tokens) > 1 else ""
        middle_raw = tokens[1] if len(tokens) > 2 else ""

        # Remove apostrophes / special chars for email generation
        first_clean = re.sub(r"[^a-zA-Z]", "", first_raw).lower()
        last_clean = re.sub(r"[^a-zA-Z]", "", last_raw).lower()
        middle_clean = re.sub(r"[^a-zA-Z]", "", middle_raw).lower() if middle_raw else ""

        if not first_clean:
            return None

        return {
            "first": first_clean,
            "last": last_clean or first_clean,
            "middle": middle_clean,
            "first_initial": first_clean[0],
            "last_initial": last_clean[0] if last_clean else "",
            "middle_initial": middle_clean[0] if middle_clean else "",
            "raw_first": first_raw,
            "raw_last": last_raw,
        }

    @staticmethod
    def resolve_company_domain(company_name: str, db: Optional[Session] = None) -> Optional[str]:
        """
        Resolves a company name to its primary email domain.
        Hierarchy:
        1. Built-in known tech & enterprise mapping dictionary.
        2. Database query against companies table (primary_domain or website).
        3. Cleaned heuristic corporate domain synthesis.
        """
        if not company_name or not isinstance(company_name, str):
            return None

        norm_name = company_name.lower().strip()

        # 1. Direct dictionary check
        if norm_name in KNOWN_COMPANY_DOMAINS:
            return KNOWN_COMPANY_DOMAINS[norm_name]

        # Strip legal and generic suffixes for dictionary lookup
        stripped = norm_name
        for pattern in COMPANY_LEGAL_SUFFIXES:
            stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE).strip()

        stripped = re.sub(r"\s+", " ", stripped).strip()
        if stripped in KNOWN_COMPANY_DOMAINS:
            return KNOWN_COMPANY_DOMAINS[stripped]

        # 2. Database lookup in existing companies table
        if db:
            try:
                comp = db.query(Company).filter(
                    (Company.company_name.ilike(company_name)) |
                    (Company.canonical_name.ilike(stripped))
                ).first()

                if comp:
                    if comp.primary_domain and "." in comp.primary_domain:
                        clean_dom = comp.primary_domain.lower().replace("www.", "").strip()
                        return clean_dom
                    if comp.website and "." in comp.website:
                        # Extract host from website
                        m = re.search(r"https?://(?:www\.)?([^/]+)", comp.website.lower())
                        if m:
                            return m.group(1).strip()
            except Exception as e:
                logger.debug("Database company domain lookup error: %s", e)

        # 3. Clean slug heuristic
        clean_slug = re.sub(r"[^a-z0-9]", "", stripped)
        if len(clean_slug) >= 2:
            return f"{clean_slug}.com"

        return None

    @staticmethod
    def verify_mx(domain: str) -> Dict[str, Any]:
        """
        Performs non-blocking DNS MX record resolution to check if the domain can receive mail.
        Identifies email provider (Google Workspace, Microsoft 365, etc.).
        Results are cached in memory for 24 hours.
        """
        if not domain or "." not in domain:
            return {"has_mx": False, "mx_records": [], "provider": "Unknown", "is_valid": False}

        domain = domain.lower().strip()
        now = datetime.now(timezone.utc).timestamp()

        # Check in-memory cache
        if domain in _MX_CACHE:
            has_mx, records, provider, cached_at = _MX_CACHE[domain]
            if now - cached_at < _MX_CACHE_TTL_SEC:
                return {
                    "has_mx": has_mx,
                    "mx_records": records,
                    "provider": provider,
                    "is_valid": has_mx,
                    "cached": True,
                }

        has_mx = False
        mx_records = []
        provider = "Generic Corporate Mail"

        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2.5
            resolver.lifetime = 2.5
            # Use public reliable resolvers
            resolver.nameservers = ["8.8.8.8", "1.1.1.1"]

            answers = resolver.resolve(domain, "MX")
            for rdata in answers:
                mx_host = str(rdata.exchange).rstrip(".").lower()
                mx_records.append(mx_host)

            if mx_records:
                has_mx = True
                mx_str = " ".join(mx_records)
                if "google" in mx_str or "aspmx" in mx_str:
                    provider = "Google Workspace"
                elif "outlook" in mx_str or "microsoft" in mx_str or "pphosted" in mx_str:
                    provider = "Microsoft 365"
                elif "mimecast" in mx_str:
                    provider = "Mimecast"
                elif "zoho" in mx_str:
                    provider = "Zoho Mail"
                elif "amazon" in mx_str or "ses" in mx_str:
                    provider = "Amazon SES"
                elif "secureserver" in mx_str:
                    provider = "GoDaddy"

        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, Exception) as e:
            logger.debug("DNS MX lookup failed for %s: %s", domain, e)
            has_mx = False

        _MX_CACHE[domain] = (has_mx, mx_records, provider, now)
        return {
            "has_mx": has_mx,
            "mx_records": mx_records,
            "provider": provider,
            "is_valid": has_mx,
            "cached": False,
        }

    @classmethod
    def generate_permutations(
        cls,
        first: str,
        last: str,
        domain: str,
        known_pattern: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates candidate email variations based on standard B2B corporate formulas.
        Sorts candidates by probability weight.
        """
        has_last = bool(last and last != first)
        f_init = first[0]
        l_init = last[0] if has_last else ""

        # Supported formulas
        candidates = []

        if has_last:
            candidates.append({"pattern": "first.last", "email": f"{first}.{last}@{domain}", "base_weight": 0.75})
            candidates.append({"pattern": "f_last", "email": f"{f_init}{last}@{domain}", "base_weight": 0.65})
            candidates.append({"pattern": "first", "email": f"{first}@{domain}", "base_weight": 0.60})
            candidates.append({"pattern": "first_last", "email": f"{first}{last}@{domain}", "base_weight": 0.50})
            candidates.append({"pattern": "f.last", "email": f"{f_init}.{last}@{domain}", "base_weight": 0.45})
            candidates.append({"pattern": "first_l", "email": f"{first}{l_init}@{domain}", "base_weight": 0.40})
            candidates.append({"pattern": "last.first", "email": f"{last}.{first}@{domain}", "base_weight": 0.35})
        else:
            candidates.append({"pattern": "first", "email": f"{first}@{domain}", "base_weight": 0.85})

        # Boost known company pattern if available
        for c in candidates:
            if known_pattern and c["pattern"] == known_pattern:
                c["confidence"] = 0.95
            else:
                c["confidence"] = c["base_weight"]

        # Sort highest confidence first
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates

    @classmethod
    def learn_pattern_from_email(
        cls,
        email: str,
        full_name: str,
        company_name: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[str]:
        """
        Deduces the company's email formula from an observed email address and candidate name.
        Saves or increments confidence in company_email_patterns table.
        """
        if not email or "@" not in email or not full_name:
            return None

        email = email.lower().strip()
        local_part, domain = email.split("@", 1)

        # Ignore free personal domains
        if domain in FREE_EMAIL_DOMAINS:
            return None

        tokens = cls.clean_name_tokens(full_name)
        if not tokens:
            return None

        first = tokens["first"]
        last = tokens["last"]
        f_init = tokens["first_initial"]
        l_init = tokens["last_initial"]

        # Reverse-engineer pattern
        deduced_pattern = None
        if last and local_part == f"{first}.{last}":
            deduced_pattern = "first.last"
        elif last and local_part == f"{f_init}{last}":
            deduced_pattern = "f_last"
        elif local_part == first:
            deduced_pattern = "first"
        elif last and local_part == f"{first}{last}":
            deduced_pattern = "first_last"
        elif last and local_part == f"{f_init}.{last}":
            deduced_pattern = "f.last"
        elif last and local_part == f"{first}{l_init}":
            deduced_pattern = "first_l"
        elif last and local_part == f"{last}.{first}":
            deduced_pattern = "last.first"

        if not deduced_pattern:
            return None

        # Persist pattern to database if session is provided
        if db:
            try:
                # Find company_id if possible
                comp_id = None
                if company_name:
                    comp = db.query(Company).filter(Company.company_name.ilike(company_name)).first()
                    if comp:
                        comp_id = comp.company_id

                if not comp_id:
                    comp = db.query(Company).filter(Company.primary_domain == domain).first()
                    if comp:
                        comp_id = comp.company_id

                if not comp_id:
                    c_title = (company_name or domain.split(".")[0]).strip().title()
                    new_comp = Company(
                        company_name=c_title,
                        canonical_name=c_title,
                        primary_domain=domain,
                        website=f"https://{domain}",
                        trust_score=75,
                        data_source="email_intelligence",
                    )
                    db.add(new_comp)
                    db.flush()
                    comp_id = new_comp.company_id

                existing = db.query(CompanyEmailPattern).filter(
                    CompanyEmailPattern.domain == domain,
                    CompanyEmailPattern.pattern == deduced_pattern
                ).first()

                if existing:
                    existing.verified_example_count = (existing.verified_example_count or 0) + 1
                    existing.confidence_score = min(100, (existing.confidence_score or 70) + 5)
                    existing.last_verified_at = datetime.now(timezone.utc)
                    db.add(existing)
                else:
                    new_pat = CompanyEmailPattern(
                        company_id=comp_id,
                        domain=domain,
                        pattern=deduced_pattern,
                        verified_example_count=1,
                        confidence_score=85,
                        active=True,
                        last_verified_at=datetime.now(timezone.utc)
                    )
                    db.add(new_pat)
                db.commit()
                logger.info("🎯 Learned email pattern for %s: %s (%s)", domain, deduced_pattern, email)
            except Exception as e:
                logger.debug("Failed saving learned pattern: %s", e)
                db.rollback()

        return deduced_pattern

    @classmethod
    def resolve_and_enrich_candidate(
        cls,
        full_name: str,
        company_name: str,
        existing_email: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for candidate email resolution and verification.
        Returns:
            {
                "email": "sarah.connor@stripe.com",
                "status": "PATTERN_VERIFIED" | "MX_VERIFIED" | "EXISTING",
                "confidence": 0.95,
                "pattern": "first.last",
                "domain": "stripe.com",
                "provider": "Google Workspace",
                "has_mx": True,
                "alternatives": [...]
            }
        """
        # If valid corporate email already exists, verify its MX and learn from it
        if existing_email and "@" in existing_email:
            existing_email = existing_email.strip().lower()
            dom = existing_email.split("@")[1]
            if dom not in FREE_EMAIL_DOMAINS:
                mx_res = cls.verify_mx(dom)
                # Learn pattern in background
                if db:
                    cls.learn_pattern_from_email(existing_email, full_name, company_name, db)
                return {
                    "email": existing_email,
                    "status": "EXISTING_VERIFIED" if mx_res["has_mx"] else "EXISTING",
                    "confidence": 1.0 if mx_res["has_mx"] else 0.85,
                    "pattern": "custom",
                    "domain": dom,
                    "provider": mx_res["provider"],
                    "has_mx": mx_res["has_mx"],
                    "alternatives": [],
                }

        # Candidate lacks email — synthesize and verify
        tokens = cls.clean_name_tokens(full_name)
        if not tokens or not company_name:
            return {"email": None, "status": "INSUFFICIENT_DATA", "confidence": 0.0}

        domain = cls.resolve_company_domain(company_name, db=db)
        if not domain:
            return {"email": None, "status": "DOMAIN_UNRESOLVED", "confidence": 0.0}

        # Check known pattern
        known_pattern = None
        if domain in SEEDED_COMPANY_PATTERNS:
            known_pattern = SEEDED_COMPANY_PATTERNS[domain]["pattern"]

        # Check DB for learned pattern
        if not known_pattern and db:
            try:
                db_pattern = db.query(CompanyEmailPattern).filter(
                    CompanyEmailPattern.domain == domain,
                    CompanyEmailPattern.active == True
                ).order_by(CompanyEmailPattern.verified_example_count.desc()).first()

                if db_pattern:
                    known_pattern = db_pattern.pattern
            except Exception as e:
                logger.debug("Failed querying DB pattern: %s", e)

        # Generate permutations
        permutations = cls.generate_permutations(
            first=tokens["first"],
            last=tokens["last"],
            domain=domain,
            known_pattern=known_pattern,
        )

        if not permutations:
            return {"email": None, "status": "NO_PERMUTATIONS", "confidence": 0.0}

        # Check domain MX status
        mx_info = cls.verify_mx(domain)
        best = permutations[0]

        # Calculate final confidence
        confidence = best["confidence"]
        if mx_info["has_mx"]:
            # Boost confidence when MX server is actively responding
            confidence = min(0.98, confidence + 0.10)
            status = "PATTERN_VERIFIED" if known_pattern else "MX_VERIFIED"
        else:
            confidence = max(0.30, confidence - 0.20)
            status = "MX_UNREACHABLE"

        return {
            "email": best["email"],
            "status": status,
            "confidence": round(confidence, 2),
            "pattern": best["pattern"],
            "domain": domain,
            "provider": mx_info["provider"],
            "has_mx": mx_info["has_mx"],
            "alternatives": permutations[1:4],
        }


# Global Singleton Instance
email_intelligence = EmailIntelligenceService()
