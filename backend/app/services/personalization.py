import re
from typing import Dict, Any, Optional
from ..models.models import Recruiter, Company
from ..models.campaigns import CampaignRecruiter

# Support {{var}}, {{var | default: 'fallback'}}, {{var || 'fallback'}}, and {{var | 'fallback'}}
VARIABLE_PATTERN = re.compile(
    r"{{\s*([a-zA-Z0-9_]+)(?:\s*(?:\||\|\|)\s*(?:default:\s*)?['\"]?([^}'\"]*?)['\"]?)?\s*}}"
)

from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

SMART_DEFAULTS = {
    "firstname": "there",
    "first_name": "there",
    "lastname": "",
    "last_name": "",
    "name": "Hiring Partner",
    "fullname": "Hiring Partner",
    "company": "your organization",
    "company_name": "your organization",
    "title": "Talent Specialist",
    "job_title": "Talent Specialist",
    "location": "your market",
    "city": "your area",
    "state": "your region",
    "email": "",
    "linkedin": "",
    "greeting": "Hello",
    "greetingtime": "Hello",
    "greeting_time": "Hello",
    "seniorityrole": "talent partner",
    "seniority_role": "talent partner",
    "metrohub": "your market",
    "metro_hub": "your market",
    "companyscale": "enterprise",
    "company_scale": "enterprise",
    "timezone": "ET",
    "timezone_code": "ET"
}

METRO_HUB_NAMES = {
    "SF_BAY_AREA": "San Francisco Bay Area",
    "NYC_TRI_STATE": "New York Tri-State Area",
    "SEATTLE_METRO": "Seattle Metro Hub",
    "TEXAS_TRIANGLE": "Texas Tech Corridor",
    "RESEARCH_TRIANGLE": "Research Triangle & Charlotte",
    "GREATER_BOSTON": "Greater Boston Area",
    "CHICAGO_METRO": "Greater Chicago Metro",
    "DMV_CAPITAL": "Washington DC Capital Region"
}

def process_spintax(text: str, seed: Optional[int] = None) -> str:
    """
    Processes nested and flat spintax e.g. {Hi|Hello|Hey} into randomized variations.
    Guarantees unique email hashing across outreach batches to prevent ESP spam flags.
    """
    if not text or '{' not in text:
        return text
    import random
    rng = random.Random(seed) if seed is not None else random
    
    pattern = re.compile(r'\{([^{}]+)\}')
    count = 0
    while pattern.search(text) and count < 10:
        text = pattern.sub(lambda m: rng.choice(m.group(1).split('|')), text)
        count += 1
    return text


def interpolate_variables(text: str, recruiter: Any, company: Any = None, custom_vars: Dict[str, Any] = None, signature_html: Optional[str] = None) -> str:
    if not text:
        return ""
        
    def replace_var(match):
        var_name = match.group(1).lower()
        explicit_fallback = match.group(2)
        default_val = explicit_fallback if explicit_fallback is not None else SMART_DEFAULTS.get(var_name, "")
        
        # Helper to extract value safely from dict or object
        def _get_val(obj, key):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        val = None

        if custom_vars and var_name in {k.lower(): k for k in custom_vars}:
            actual_key = next(k for k in custom_vars if k.lower() == var_name)
            val = custom_vars[actual_key]
            
        elif var_name in ("firstname", "first_name"):
            val = _get_val(recruiter, "first_name") or _get_val(recruiter, "firstname")
            if not val:
                r_name = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
                if r_name:
                    val = r_name.strip().split()[0]
                
        elif var_name in ("lastname", "last_name"):
            val = _get_val(recruiter, "last_name") or _get_val(recruiter, "lastname")
            if not val:
                r_name = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
                if r_name:
                    parts = r_name.strip().split()
                    val = parts[-1] if len(parts) > 1 else ""
                
        elif var_name in ("name", "fullname"):
            val = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
            if not val and (_get_val(recruiter, "first_name") or _get_val(recruiter, "last_name")):
                fn = _get_val(recruiter, "first_name") or ""
                ln = _get_val(recruiter, "last_name") or ""
                val = f"{fn} {ln}".strip()
            
        elif var_name in ("company", "company_name"):
            val = _get_val(company, "company_name") or _get_val(company, "name") or _get_val(recruiter, "company_name") or _get_val(recruiter, "company")
            
        elif var_name in ("title", "job_title"):
            val = _get_val(recruiter, "title") or _get_val(recruiter, "specialization")
            
        elif var_name == "location":
            val = _get_val(recruiter, "location") or _get_val(recruiter, "city")
            
        elif var_name == "city":
            val = _get_val(recruiter, "normalized_city") or _get_val(recruiter, "city") or _get_val(recruiter, "location")
            
        elif var_name == "state":
            val = _get_val(recruiter, "state")
            
        elif var_name == "email":
            val = _get_val(recruiter, "email")
            
        elif var_name == "linkedin":
            val = _get_val(recruiter, "linkedin")

        elif var_name in ("greeting", "greetingtime", "greeting_time"):
            tz_str = _get_val(recruiter, "timezone") or "America/New_York"
            try:
                tz = ZoneInfo(tz_str)
                local_hour = datetime.now(tz).hour
                if 4 <= local_hour < 12:
                    val = "Good morning"
                elif 12 <= local_hour < 17:
                    val = "Good afternoon"
                else:
                    val = "Good evening"
            except Exception:
                val = "Hello"

        elif var_name in ("seniorityrole", "seniority_role"):
            sen = _get_val(recruiter, "seniority_level") or "Specialist"
            if sen == "Executive":
                val = "executive talent leader"
            elif sen == "Director":
                val = "talent acquisition leader"
            elif sen == "Lead":
                val = "lead recruitment partner"
            elif sen == "Senior":
                val = "senior recruiter"
            elif sen == "Campus":
                val = "university & campus talent lead"
            else:
                val = "recruiting specialist"

        elif var_name in ("metrohub", "metro_hub"):
            hub_code = _get_val(recruiter, "metro_hub")
            val = METRO_HUB_NAMES.get(hub_code) if hub_code else None

        elif var_name in ("companyscale", "company_scale"):
            val = _get_val(recruiter, "company_scale")

        elif var_name in ("timezone", "timezone_code"):
            val = _get_val(recruiter, "timezone_code")

        if val and str(val).strip():
            return str(val).strip()
            
        return default_val if default_val is not None else ""
        
    result = VARIABLE_PATTERN.sub(replace_var, text)
    
    # Process Spintax to ensure structural anti-spam uniqueness
    rec_id = None
    if isinstance(recruiter, dict):
        rec_id = recruiter.get("recruiter_id") or recruiter.get("id")
    else:
        rec_id = getattr(recruiter, "recruiter_id", getattr(recruiter, "id", None))
    result = process_spintax(result, seed=rec_id if isinstance(rec_id, int) else None)
    
    # Append signature if provided
    if signature_html:
        result += "\n\n" + signature_html
    
    return result


def get_available_variables():
    """Return list of supported personalization variables with descriptions."""
    return [
        {"variable": "{{FirstName}}", "description": "Recipient's first name", "fallback": "there"},
        {"variable": "{{LastName}}", "description": "Recipient's last name", "fallback": ""},
        {"variable": "{{FullName}}", "description": "Recipient's full name", "fallback": ""},
        {"variable": "{{GreetingTime}}", "description": "Local time greeting (Good morning/afternoon)", "fallback": "Hello"},
        {"variable": "{{Company}}", "description": "Recipient's company name", "fallback": ""},
        {"variable": "{{Title}}", "description": "Recipient's job title", "fallback": ""},
        {"variable": "{{SeniorityRole}}", "description": "Decision level role phrasing", "fallback": "recruiter"},
        {"variable": "{{MetroHub}}", "description": "Major hiring hub market name", "fallback": ""},
        {"variable": "{{CompanyScale}}", "description": "Enterprise / Mid-Market / Boutique scale", "fallback": ""},
        {"variable": "{{Location}}", "description": "Recipient's location", "fallback": ""},
        {"variable": "{{State}}", "description": "Recipient's state", "fallback": ""},
        {"variable": "{{Timezone}}", "description": "Local timezone code (ET, CT, PT, MT)", "fallback": ""},
        {"variable": "{{Email}}", "description": "Recipient's email address", "fallback": ""},
        {"variable": "{{LinkedIn}}", "description": "Recipient's LinkedIn URL", "fallback": ""},
    ]


def preview_email(subject_template: str, body_template: str, recruiter: Recruiter, company: Company = None, signature_html: Optional[str] = None) -> dict:
    """Generate a fully personalized preview of an email for a specific recipient."""
    return {
        "subject": interpolate_variables(subject_template, recruiter, company),
        "body": interpolate_variables(body_template, recruiter, company, signature_html=signature_html),
        "recipient_email": recruiter.email if recruiter else "",
        "recipient_name": recruiter.recruiter_name if recruiter else "",
    }
