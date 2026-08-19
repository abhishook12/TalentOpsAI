"""
Email Deliverability & Spam Score Estimator Service
===================================================
Analyzes outreach campaign email subject lines and body contents for spam triggers,
reputation hazards, formatting red flags, and deliverability best practices.
"""

import re
from typing import Dict, Any, List

HIGH_RISK_TRIGGERS = {
    # Urgency & Pressure
    "act now": 15, "urgent response": 18, "exclusive deal": 12, "limited time": 10,
    "apply immediately": 12, "instant access": 10, "don't delete": 20, "final notice": 22,
    "last chance": 12, "immediate action required": 20,
    
    # Financial & Unrealistic Claims
    "make money": 25, "100% free": 20, "guaranteed": 15, "earn $": 20,
    "no cost": 10, "risk free": 15, "extra income": 18, "million dollars": 25,
    "cash bonus": 18, "pure profit": 20,
    
    # Deceptive / Spam Patterns
    "congratulations": 12, "winner": 22, "claim your prize": 25, "selected for": 10,
    "click here": 15, "open immediately": 18, "this is not spam": 25, "opt in": 10,
    "special promotion": 14, "buy direct": 12
}

MODERATE_RISK_TRIGGERS = {
    "opportunity of a lifetime": 10, "unbelievable": 8, "miracle": 15,
    "secret": 8, "hidden": 8, "hidden fees": 8, "cheap": 10,
    "discount": 8, "lowest price": 10, "drastically reduced": 10
}


def analyze_email_content(subject: str, body: str) -> Dict[str, Any]:
    """
    Comprehensive spam risk score analysis (0 = pristine / low risk, 100 = critical spam risk).
    Returns score, risk tier, detected flags, and actionable guidance.
    """
    score = 0
    flags: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    subject_clean = (subject or "").strip()
    body_clean = (body or "").strip()
    full_text = f"{subject_clean} {body_clean}".lower()

    if not subject_clean:
        score += 25
        flags.append({"type": "missing_subject", "severity": "high", "message": "Email subject line is empty."})
        recommendations.append("Add a concise, personalized subject line.")

    # 1. Check Subject Line Capitalization
    if subject_clean:
        upper_letters = sum(1 for c in subject_clean if c.isupper())
        total_letters = sum(1 for c in subject_clean if c.isalpha())
        if total_letters > 0 and (upper_letters / total_letters) > 0.4:
            score += 20
            flags.append({"type": "excessive_caps_subject", "severity": "high", "message": "Subject contains excessive ALL-CAPS text."})
            recommendations.append("Use standard sentence casing in your subject line.")

    # 2. Check Exclamation & Special Character Density
    exclamation_count = full_text.count("!")
    if exclamation_count > 3:
        score += min(15, exclamation_count * 3)
        flags.append({"type": "excessive_punctuation", "severity": "medium", "message": f"Found {exclamation_count} exclamation marks."})
        recommendations.append("Reduce exclamation marks to at most 1 in the entire message.")

    dollar_count = full_text.count("$")
    if dollar_count > 2:
        score += min(15, dollar_count * 4)
        flags.append({"type": "excessive_currency_symbols", "severity": "medium", "message": "Multiple currency signs ($) detected."})
        recommendations.append("Avoid multiple dollar signs in the email body.")

    # 3. Check High-Risk Trigger Phrases
    for trigger, penalty in HIGH_RISK_TRIGGERS.items():
        if re.search(r'\b' + re.escape(trigger) + r'\b', full_text):
            score += penalty
            flags.append({"type": "spam_trigger_phrase", "severity": "high", "phrase": trigger, "message": f"High-risk trigger phrase: '{trigger}'"})

    # 4. Check Moderate-Risk Trigger Phrases
    for trigger, penalty in MODERATE_RISK_TRIGGERS.items():
        if re.search(r'\b' + re.escape(trigger) + r'\b', full_text):
            score += penalty
            flags.append({"type": "moderate_trigger_phrase", "severity": "medium", "phrase": trigger, "message": f"Suspicious marketing phrase: '{trigger}'"})

    # 5. Check Personalization Tokens
    has_personalization = bool(re.search(r'\{\{\s*(first_name|name|recruiter_name|company|company_name)\s*\}\}', body_clean, re.IGNORECASE))
    if not has_personalization and len(body_clean) > 80:
        score += 8
        flags.append({"type": "no_personalization", "severity": "low", "message": "No dynamic recipient tags (e.g. {{first_name}}) detected."})
        recommendations.append("Include dynamic tags like {{first_name}} or {{company}} to improve engagement.")

    # 6. Check Unsubscribe / Opt-out Presence (for outreach compliance)
    has_unsubscribe = bool(re.search(r'(unsubscribe|opt[- ]out|\{\{\s*unsubscribe\s*\}\}|reply with stop)', body_clean, re.IGNORECASE))
    if not has_unsubscribe and len(body_clean) > 120:
        score += 12
        flags.append({"type": "missing_optout", "severity": "medium", "message": "No opt-out or unsubscribe mechanism found."})
        recommendations.append("Add an unsubscribe link or 'Reply STOP to opt out' sentence.")

    # 7. Check Link Density
    links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', body_clean)
    if len(links) > 3:
        score += min(15, (len(links) - 3) * 5)
        flags.append({"type": "high_link_density", "severity": "medium", "message": f"Contains {len(links)} links. High link count triggers spam filters."})
        recommendations.append("Keep total URLs to 1-2 reputable links at most.")

    # Cap score at 100
    final_score = min(100, max(0, score))
    deliverability_score = 100 - final_score

    if final_score <= 20:
        risk_tier = "low"
        is_safe = True
        summary = "Excellent deliverability profile. Low probability of spam filtering."
    elif final_score <= 45:
        risk_tier = "medium"
        is_safe = True
        summary = "Moderate deliverability risk. Recommended to address flagged suggestions."
    else:
        risk_tier = "high"
        is_safe = False
        summary = "High spam risk detected. Email is likely to land in junk or be quarantined."

    return {
        "spam_score": final_score,
        "deliverability_score": deliverability_score,
        "risk_tier": risk_tier,
        "is_safe": is_safe,
        "summary": summary,
        "flag_count": len(flags),
        "flags": flags,
        "recommendations": list(set(recommendations))
    }
