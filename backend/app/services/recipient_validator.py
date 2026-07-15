import re
import logging
from typing import Optional, List
from dataclasses import dataclass, field, asdict
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models.models import Recruiter, Company

logger = logging.getLogger(__name__)

# Known disposable email domains
DISPOSABLE_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'throwaway.email',
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

@dataclass
class ValidatedRecipient:
    email: str
    status: str  # 'valid', 'invalid', 'duplicate', 'disposable'
    reason: Optional[str] = None
    # Enrichment from DB
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
    
    # Fetch existing recruiters in one batch for performance
    existing_recruiters = {}
    if cleaned_emails:
        db_recruiters = db.query(Recruiter).filter(Recruiter.email.in_(cleaned_emails)).all()
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

    for email in cleaned_emails:
        recipient = ValidatedRecipient(email=email, status='valid')
        
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
        domain = email.split('@')[1] if '@' in email else ''
        if domain in DISPOSABLE_DOMAINS:
            recipient.status = 'disposable'
            recipient.reason = 'Disposable email domain'
            result.disposable_count += 1
            result.recipients.append(recipient)
            continue
            
        # 4. Enrich from DB
        enrichment = existing_recruiters.get(email)
        if enrichment:
            recipient.recruiter_id = enrichment['recruiter_id']
            recipient.recruiter_name = enrichment['recruiter_name']
            recipient.company_name = enrichment['company_name']
            recipient.company_id = enrichment['company_id']
            recipient.title = enrichment['title']
            recipient.location = enrichment['location']
            recipient.linkedin = enrichment['linkedin']
            
        result.valid_count += 1
        result.recipients.append(recipient)
        
    return result
