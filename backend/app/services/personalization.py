import re
from typing import Dict, Any, Optional
from ..models.models import Recruiter, Company
from ..models.campaigns import CampaignRecruiter

VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

def interpolate_variables(text: str, recruiter: Recruiter, company: Company = None, custom_vars: Dict[str, Any] = None, signature_html: Optional[str] = None) -> str:
    if not text:
        return ""
        
    def replace_var(match):
        var_name = match.group(1).lower()
        
        if custom_vars and var_name in {k.lower(): k for k in custom_vars}:
            # Find the actual key with matching lowercase
            actual_key = next(k for k in custom_vars if k.lower() == var_name)
            val = custom_vars[actual_key]
            return str(val) if val is not None else ""
            
        if var_name == "firstname":
            if recruiter and recruiter.recruiter_name:
                return recruiter.recruiter_name.split()[0]
            return "there"
            
        if var_name == "lastname":
            if recruiter and recruiter.recruiter_name:
                parts = recruiter.recruiter_name.split()
                return parts[-1] if len(parts) > 1 else ""
            return ""
            
        if var_name in ("name", "fullname"):
            return recruiter.recruiter_name if recruiter and recruiter.recruiter_name else ""
            
        if var_name == "company":
            if company and company.company_name:
                return company.company_name
            return ""
            
        if var_name == "title":
            return recruiter.title if recruiter and recruiter.title else ""
            
        if var_name == "location":
            return recruiter.location if recruiter and recruiter.location else ""
        
        if var_name == "state":
            return recruiter.state if recruiter and recruiter.state else ""
        
        if var_name == "email":
            return recruiter.email if recruiter and recruiter.email else ""
        
        if var_name == "linkedin":
            return recruiter.linkedin if recruiter and recruiter.linkedin else ""
            
        return match.group(0)  # Return original if unknown
        
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
