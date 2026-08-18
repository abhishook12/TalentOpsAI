"""
TalentOpsAI Campaign Pre-Flight Deliverability Safety Gate
===========================================================
Before any campaign dispatches emails, this service scans all recipients
against the unified deliverability engine and categorizes them into:

  - safe_to_send     → Tier 1 (verified) + Tier 2 (likely_deliverable)
  - risky_catchall   → Tier 3 (risky_catchall) — flagged for review
  - blocked          → Tier 4 (undeliverable) + Tier 5 (missing)

The gate prevents undeliverable emails from being dispatched, protecting
sender reputation and reducing bounce rates.
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field

from app.services.recruiter_store import recruiter_store

logger = logging.getLogger("campaign_preflight")


@dataclass
class PreflightRecipient:
    """Individual recipient deliverability assessment."""
    email: str
    name: str
    recruiter_id: Optional[int]
    email_status: str           # verified, likely_deliverable, risky_catchall, undeliverable, missing
    email_confidence: int
    is_deliverable: bool
    tier: int                   # 1-5
    tier_label: str
    action: str                 # 'send', 'review', 'block'


@dataclass
class PreflightResult:
    """Campaign-wide pre-flight check result."""
    campaign_id: int
    total_recipients: int
    safe_to_send: int
    risky_review: int
    blocked: int
    deliverability_rate: float   # percentage of safe recipients
    risk_level: str              # 'low', 'medium', 'high', 'critical'
    can_proceed: bool            # True if deliverability_rate >= 70%
    warning_message: Optional[str]
    recipients: List[dict]       # List of PreflightRecipient dicts
    checked_at: str
    check_duration_ms: float


# Status → tier mapping
STATUS_TO_TIER = {
    'verified': (1, 'Tier 1 — Verified Corporate MX'),
    'likely_deliverable': (2, 'Tier 2 — Likely Deliverable'),
    'likely_valid': (2, 'Tier 2 — Likely Deliverable'),
    'risky_catchall': (3, 'Tier 3 — Risky Catch-All'),
    'needs_monitoring': (3, 'Tier 3 — Needs Monitoring'),
    'undeliverable': (4, 'Tier 4 — Undeliverable'),
    'suspicious': (4, 'Tier 4 — Suspicious'),
    'likely_invalid': (4, 'Tier 4 — Likely Invalid'),
    'invalid': (4, 'Tier 4 — Invalid'),
    'missing': (5, 'Tier 5 — Missing Email'),
}


def _classify_action(tier: int) -> str:
    """Map tier to action: send, review, or block."""
    if tier <= 2:
        return 'send'
    elif tier == 3:
        return 'review'
    else:
        return 'block'


def _classify_risk(deliverability_rate: float, blocked_count: int, total: int) -> str:
    """Classify overall campaign risk level."""
    if blocked_count == 0 and deliverability_rate >= 95:
        return 'low'
    elif deliverability_rate >= 80:
        return 'medium'
    elif deliverability_rate >= 60:
        return 'high'
    else:
        return 'critical'


def run_preflight_check(
    campaign_id: int,
    recipient_emails: List[str],
    recipient_names: Optional[List[str]] = None
) -> PreflightResult:
    """
    Run a pre-flight deliverability check for all campaign recipients.
    
    Queries the unified DuckDB Parquet store for each recipient's
    deliverability status and returns a categorized breakdown.
    
    Args:
        campaign_id: Campaign database ID
        recipient_emails: List of recipient email addresses
        recipient_names: Optional list of recipient names (parallel to emails)
    
    Returns:
        PreflightResult with categorized recipients and risk assessment
    """
    start_time = time.time()
    
    if not recipient_names:
        recipient_names = [''] * len(recipient_emails)
    
    # Ensure names list matches emails
    while len(recipient_names) < len(recipient_emails):
        recipient_names.append('')
    
    # Query DuckDB for deliverability data
    recruiter_store._ensure_loaded()
    conn = recruiter_store._conn
    
    results: List[PreflightRecipient] = []
    safe_count = 0
    risky_count = 0
    blocked_count = 0
    
    for i, email in enumerate(recipient_emails):
        email_clean = email.lower().strip()
        name = recipient_names[i] if i < len(recipient_names) else ''
        
        # Query Parquet for this email
        try:
            row = conn.execute("""
                SELECT recruiter_id, email_status, email_confidence, is_deliverable
                FROM recruiters
                WHERE LOWER(email) = ?
                LIMIT 1
            """, [email_clean]).fetchone()
        except Exception:
            row = None
        
        if row:
            recruiter_id = int(row[0]) if row[0] else None
            email_status = str(row[1]) if row[1] else 'missing'
            email_confidence = int(row[2]) if row[2] else 0
            is_deliverable = bool(row[3]) if row[3] is not None else False
        else:
            # Email not in database — treat as unknown/risky
            recruiter_id = None
            email_status = 'missing'
            email_confidence = 0
            is_deliverable = False
        
        tier, tier_label = STATUS_TO_TIER.get(email_status, (5, 'Tier 5 — Unknown'))
        action = _classify_action(tier)
        
        recipient = PreflightRecipient(
            email=email_clean,
            name=name,
            recruiter_id=recruiter_id,
            email_status=email_status,
            email_confidence=email_confidence,
            is_deliverable=is_deliverable,
            tier=tier,
            tier_label=tier_label,
            action=action
        )
        results.append(recipient)
        
        if action == 'send':
            safe_count += 1
        elif action == 'review':
            risky_count += 1
        else:
            blocked_count += 1
    
    total = len(results)
    deliverability_rate = round((safe_count / max(1, total)) * 100, 1)
    risk_level = _classify_risk(deliverability_rate, blocked_count, total)
    
    # Determine if campaign can proceed
    can_proceed = deliverability_rate >= 50  # At least 50% must be safe
    
    # Generate warning message
    warning_message = None
    if blocked_count > 0:
        warning_message = f"{blocked_count} recipient(s) have undeliverable or missing emails and will be skipped."
    if risk_level == 'critical':
        warning_message = f"CRITICAL: Only {deliverability_rate}% of recipients have verified emails. Campaign launch is blocked."
        can_proceed = False
    elif risk_level == 'high':
        warning_message = f"WARNING: {deliverability_rate}% deliverability rate. {blocked_count} blocked, {risky_count} need review."
    
    elapsed = (time.time() - start_time) * 1000
    
    return PreflightResult(
        campaign_id=campaign_id,
        total_recipients=total,
        safe_to_send=safe_count,
        risky_review=risky_count,
        blocked=blocked_count,
        deliverability_rate=deliverability_rate,
        risk_level=risk_level,
        can_proceed=can_proceed,
        warning_message=warning_message,
        recipients=[asdict(r) for r in results],
        checked_at=datetime.now(timezone.utc).isoformat(),
        check_duration_ms=round(elapsed, 1)
    )


def get_deliverability_report(campaign_id: int, recipient_emails: List[str]) -> dict:
    """
    Generate a detailed per-recipient deliverability report for a campaign.
    
    Returns breakdown by tier with aggregate statistics.
    """
    result = run_preflight_check(campaign_id, recipient_emails)
    
    # Group by tier
    by_tier = {}
    for r in result.recipients:
        tier_key = f"tier_{r['tier']}"
        if tier_key not in by_tier:
            by_tier[tier_key] = {
                'tier': r['tier'],
                'label': r['tier_label'],
                'action': r['action'],
                'count': 0,
                'recipients': []
            }
        by_tier[tier_key]['count'] += 1
        by_tier[tier_key]['recipients'].append({
            'email': r['email'],
            'name': r['name'],
            'confidence': r['email_confidence'],
            'status': r['email_status']
        })
    
    return {
        'campaign_id': campaign_id,
        'summary': {
            'total': result.total_recipients,
            'safe_to_send': result.safe_to_send,
            'risky_review': result.risky_review,
            'blocked': result.blocked,
            'deliverability_rate': result.deliverability_rate,
            'risk_level': result.risk_level,
            'can_proceed': result.can_proceed,
            'warning': result.warning_message
        },
        'tiers': by_tier,
        'checked_at': result.checked_at,
        'check_duration_ms': result.check_duration_ms
    }
