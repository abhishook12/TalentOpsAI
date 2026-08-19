"""
TalentOps AI - Domain Health & Deliverability Service
Wraps DNS and Authentication checks with actionable recommendations and warmup schedules.
"""

from typing import Dict, Any, List
from .dns_checker import domain_health_checker

def check_domain_health(domain: str) -> Dict[str, Any]:
    """
    Evaluates SPF, DKIM, DMARC, MX, and DNS reputation for a domain.
    """
    raw = domain_health_checker.inspect_domain(domain)
    
    spf_status = "Valid" if raw.get("has_spf") else "Missing"
    dmarc_status = "Valid" if raw.get("has_dmarc") else "Missing"
    dkim_status = "Found" if len(raw.get("dkim_selectors_found", [])) > 0 else "Unverified"

    return {
        "domain": raw.get("domain", domain),
        "health_score": raw.get("health_score", 0),
        "status": raw.get("status_label", "Unknown"),
        "risk_tier": raw.get("risk_tier", "high"),
        "has_mx": raw.get("has_mx", False),
        "mx_records": raw.get("mx_records", []),
        "spf": {
            "valid": raw.get("has_spf", False),
            "record": raw.get("spf_record"),
            "status": spf_status,
            "details": raw.get("spf_status", "Missing")
        },
        "dmarc": {
            "valid": raw.get("has_dmarc", False),
            "record": raw.get("dmarc_record"),
            "policy": raw.get("dmarc_policy"),
            "status": dmarc_status,
            "details": raw.get("dmarc_status", "Missing")
        },
        "dkim": {
            "valid": len(raw.get("dkim_selectors_found", [])) > 0,
            "status": dkim_status,
            "selectors_checked": raw.get("dkim_selectors_found", [])
        },
        "recommendations": raw.get("recommendations", [])
    }

def get_warmup_schedule() -> List[Dict[str, Any]]:
    """
    Returns standard 4-week domain warmup schedule.
    """
    return [
        {"week": 1, "daily_volume": "10-20 emails/day", "focus": "High engagement warmup & colleague testing"},
        {"week": 2, "daily_volume": "25-50 emails/day", "focus": "Gradual cold outreach ramp to verified active leads"},
        {"week": 3, "daily_volume": "50-100 emails/day", "focus": "Full outreach ramp with auto-pause bounce monitors"},
        {"week": 4, "daily_volume": "100-200 emails/day", "focus": "Peak sustained outreach capacity with 99%+ inbox placement"}
    ]
