import os
import json
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models.models import Recruiter, Company

logger = logging.getLogger(__name__)

# Known disposable email domains
DISPOSABLE_DOMAINS = {
    'guerrillamail.com', 'tempmail.com', 'throwaway.email',
    'yopmail.com', 'sharklasers.com', 'guerrillamailblock.com', 'grr.la',
    'guerrillamail.info', 'guerrillamail.net', 'trashmail.com', 'tempinbox.com',
    'maildrop.cc', 'dispostable.com', 'getnada.com', 'temp-mail.org',
    'fakeinbox.com', 'mailnesia.com', 'binkmail.com', 'mintemail.com',
    'tempail.com', 'mohmal.com', 'emailondeck.com', '10minutemail.com',
    'trashmail.net', 'trashmail.org', 'harakirimail.com', 'jetable.org',
}

EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Load cached MX domain registry
_MX_REGISTRY: Optional[Dict[str, Any]] = None

def _get_mx_registry() -> Dict[str, Any]:
    global _MX_REGISTRY
    if _MX_REGISTRY is None:
        cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mx_domain_registry.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    _MX_REGISTRY = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load MX domain registry: {e}")
                _MX_REGISTRY = {}
        else:
            _MX_REGISTRY = {}
    return _MX_REGISTRY

def _check_domain_mx_live(domain: str) -> bool:
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2.0
        resolver.lifetime = 2.0
        answers = resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except Exception:
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2.0
            resolver.lifetime = 2.0
            answers = resolver.resolve(domain, 'A')
            return len(answers) > 0
        except Exception:
            return False

from datetime import datetime, timedelta, timezone

@dataclass
class ValidatedRecipient:
    email: str
    status: str  # 'valid', 'invalid', 'duplicate', 'disposable', 'invalid_mx'
    reason: Optional[str] = None
    # Enrichment from DB & DNS Engine
    is_deliverable: bool = True
    deliverability_status: str = "valid_mx"
    trust_score: int = 95
    logo_url: Optional[str] = None
    contacted_recently: bool = False
    last_contacted_date: Optional[str] = None
    contact_cooldown_warning: Optional[str] = None
    recruiter_id: Optional[int] = None
    recruiter_name: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    title: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None

@dataclass
class ValidationResult:
    total: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    disposable_count: int = 0
    undeliverable_mx_count: int = 0
    recent_contact_count: int = 0
    recipients: List[ValidatedRecipient] = field(default_factory=list)


def validate_recipients(raw_emails: List[str], db: Session) -> ValidationResult:
    result = ValidationResult()
    seen_emails = set()
    
    # Pre-process emails
    cleaned_emails = []
    for raw in raw_emails:
        if not raw:
            continue
        cleaned = raw.strip().lower()
        if cleaned:
            cleaned_emails.append(cleaned)
            
    result.total = len(cleaned_emails)
    
    # Fetch existing recruiters in one batch for performance (chunked for SQLite limits)
    existing_recruiters = {}
    recent_contacts = {}  # recruiter_id -> last_sent_at str
    
    if cleaned_emails:
        chunk_size = 900
        for i in range(0, len(cleaned_emails), chunk_size):
            chunk = cleaned_emails[i:i + chunk_size]
            db_recruiters = db.query(Recruiter).filter(Recruiter.email.in_(chunk)).all()
            for r in db_recruiters:
                company_name = None
                if r.company:
                    company_name = r.company.company_name
                existing_recruiters[r.email.lower()] = {
                    'recruiter_id': r.recruiter_id,
                    'recruiter_name': r.recruiter_name,
                    'company_name': company_name,
                    'company_id': r.company_id,
                    'title': r.title,
                    'location': r.location,
                    'linkedin': r.linkedin
                }

        # Check 30-day campaign collision / cooldown
        recruiter_ids = [v['recruiter_id'] for v in existing_recruiters.values() if v.get('recruiter_id')]
        if recruiter_ids:
            try:
                from ..models.campaigns import CampaignRecruiter, Campaign
                thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                # Fetch recent campaign enrollments
                cr_records = db.query(CampaignRecruiter, Campaign.name).join(
                    Campaign, CampaignRecruiter.campaign_id == Campaign.campaign_id
                ).filter(
                    CampaignRecruiter.recruiter_id.in_(recruiter_ids),
                    or_(
                        CampaignRecruiter.last_sent_at >= thirty_days_ago,
                        CampaignRecruiter.enrolled_at >= thirty_days_ago
                    )
                ).all()
                for cr, c_name in cr_records:
                    contact_time = cr.last_sent_at or cr.enrolled_at
                    recent_contacts[cr.recruiter_id] = {
                        "campaign_name": c_name,
                        "date": contact_time.strftime("%Y-%m-%d") if contact_time else "recently"
                    }
            except Exception as e:
                logger.debug(f"Campaign cooldown check skipped: {e}")

    mx_registry = _get_mx_registry()

    for email in cleaned_emails:
        recipient = ValidatedRecipient(email=email, status='valid')
        domain = email.split('@')[1] if '@' in email else ''
        
        # 1. Check duplicates
        if email in seen_emails:
            recipient.status = 'duplicate'
            recipient.reason = 'Duplicate email in list'
            result.duplicate_count += 1
            result.recipients.append(recipient)
            continue
            
        seen_emails.add(email)
        
        # 2. Validate syntax
        if not EMAIL_REGEX.match(email):
            recipient.status = 'invalid'
            recipient.reason = 'Invalid email format'
            result.invalid_count += 1
            result.recipients.append(recipient)
            continue
            
        # 3. Check disposable
        if domain in DISPOSABLE_DOMAINS:
            recipient.status = 'disposable'
            recipient.reason = 'Disposable email domain'
            result.disposable_count += 1
            result.recipients.append(recipient)
            continue

        # 4. Check DNS MX Registry
        if domain:
            recipient.logo_url = f"https://logos.hunter.io/{domain}"
            if domain in mx_registry:
                mx_info = mx_registry[domain]
                is_mx_deliv = bool(mx_info.get("valid", False) or mx_info.get("is_deliverable", False))
                recipient.is_deliverable = is_mx_deliv
                recipient.deliverability_status = mx_info.get("type", "valid_mx")
                if not is_mx_deliv:
                    recipient.status = 'invalid'
                    recipient.reason = 'Domain has no active MX records (Non-deliverable mail server)'
                    result.invalid_count += 1
                    result.undeliverable_mx_count += 1
                    result.recipients.append(recipient)
                    continue
            else:
                is_live_deliv = _check_domain_mx_live(domain)
                recipient.is_deliverable = is_live_deliv
                recipient.deliverability_status = "valid_mx" if is_live_deliv else "unresolvable_mx"
                if not is_live_deliv:
                    recipient.status = 'invalid'
                    recipient.reason = 'Domain has no active MX records (DNS resolution failed)'
                    result.invalid_count += 1
                    result.undeliverable_mx_count += 1
                    result.recipients.append(recipient)
                    continue

        # 5. Enrich from DB & Cooldown check
        enrichment = existing_recruiters.get(email)
        if enrichment:
            rec_id = enrichment['recruiter_id']
            recipient.recruiter_id = rec_id
            recipient.recruiter_name = enrichment['recruiter_name']
            recipient.company_name = enrichment['company_name']
            recipient.company_id = enrichment['company_id']
            recipient.title = enrichment['title']
            recipient.location = enrichment['location']
            recipient.linkedin = enrichment['linkedin']
            
            if rec_id in recent_contacts:
                rc = recent_contacts[rec_id]
                recipient.contacted_recently = True
                recipient.last_contacted_date = rc["date"]
                recipient.contact_cooldown_warning = f"Recently contacted in '{rc['campaign_name']}' ({rc['date']})"
                result.recent_contact_count += 1
            
        result.valid_count += 1
        result.recipients.append(recipient)
        
    return result
