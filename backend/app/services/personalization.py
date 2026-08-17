import re
from typing import Dict, Any, Optional
from ..models.models import Recruiter, Company
from ..models.campaigns import CampaignRecruiter

# Support {{var}}, {{var | default: 'fallback'}}, {{var || 'fallback'}}, and {{var | 'fallback'}}
VARIABLE_PATTERN = re.compile(
    r"{{\s*([a-zA-Z0-9_]+)(?:\s*(?:\||\|\|)\s*(?:default:\s*)?['\"]?([^}'\"]*?)['\"]?)?\s*}}"
)

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
    "linkedin": ""
}

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
            r_name = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
            if r_name:
                val = r_name.strip().split()[0]
                
        elif var_name in ("lastname", "last_name"):
            r_name = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
            if r_name:
                parts = r_name.strip().split()
                val = parts[-1] if len(parts) > 1 else ""
                
        elif var_name in ("name", "fullname"):
            val = _get_val(recruiter, "recruiter_name") or _get_val(recruiter, "name")
            
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

        if val and str(val).strip():
            return str(val).strip()
            
        return default_val if default_val is not None else ""
        
    result = VARIABLE_PATTERN.sub(replace_var, text)
    
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
        {"variable": "{{Company}}", "description": "Recipient's company name", "fallback": ""},
        {"variable": "{{Title}}", "description": "Recipient's job title", "fallback": ""},
        {"variable": "{{Location}}", "description": "Recipient's location", "fallback": ""},
        {"variable": "{{State}}", "description": "Recipient's state", "fallback": ""},
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
