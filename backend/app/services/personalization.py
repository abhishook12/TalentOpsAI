import re
from typing import Dict, Any
from ..models.models import Recruiter, Company
from ..models.campaigns import CampaignRecruiter

VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

def interpolate_variables(text: str, recruiter: Recruiter, company: Company = None, custom_vars: Dict[str, Any] = None) -> str:
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
            
        if var_name == "name":
            return recruiter.recruiter_name if recruiter and recruiter.recruiter_name else ""
            
        if var_name == "company":
            if company and company.company_name:
                return company.company_name
            return ""
            
        if var_name == "title":
            return recruiter.title if recruiter and recruiter.title else ""
            
        if var_name == "location":
            return recruiter.location if recruiter and recruiter.location else ""
            
        return match.group(0)  # Return original if unknown
        
    return VARIABLE_PATTERN.sub(replace_var, text)
