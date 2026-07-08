import os
import sys
import logging
import re
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

COMPANY_INDICATORS = [
    'inc', 'llc', 'ltd', 'corp', 'corporation', 'company', 'solutions', 'systems',
    'talent', 'group', 'services', 'consulting', 'technologies', 'partners',
    'staffing', 'search', 'advisors', 'international', 'global', 'agency'
]

def format_name_from_email_prefix(prefix):
    if not prefix: return None
    prefix = prefix.strip().lower()
    # Remove digits at the end
    prefix = re.sub(r'\d+$', '', prefix)
    
    if '.' in prefix or '_' in prefix or '-' in prefix:
        parts = re.split(r'[\._\-]', prefix)
        parts = [p.capitalize() for p in parts if len(p) > 0]
        if len(parts) >= 2:
            return ' '.join(parts)
        elif len(parts) == 1 and len(parts[0]) > 2:
            return parts[0]
            
    # e.g. cperry -> C Perry if len > 4
    if len(prefix) >= 5 and prefix[0].isalpha() and prefix[1:].isalpha():
        # Check common patterns
        return f"{prefix[0].upper()} {prefix[1:].capitalize()}"
        
    if len(prefix) > 2:
        return prefix.capitalize()
    return None

def calculate_completeness(r):
    score = 0
    if r.recruiter_name and len(r.recruiter_name) > 2 and '@' not in r.recruiter_name:
        score += 30
    if r.email and '@' in r.email and 'missing.local' not in r.email:
        score += 30
    if r.company_id:
        score += 20
    if r.phone and len(str(r.phone)) >= 7:
        score += 10
    if r.title and r.title.lower() not in ['none', 'nan', 'recruiter']:
        score += 5
    if r.state or r.location:
        score += 5
    return score

def repair_corrupted_recruiters():
    db = SessionLocal()
    logger.info("Starting automated data quality repair and sanitization across all recruiters...")
    
    stats = {
        "emails_with_spaces_cleaned": 0,
        "names_from_email_fixed": 0,
        "company_names_in_recruiter_fixed": 0,
        "short_names_expanded": 0,
        "placeholders_tagged": 0,
        "completeness_updated": 0
    }
    
    # 1. Clean spaces inside email addresses
    logger.info("Step 1: Cleaning spaces inside email addresses...")
    spaced_emails = db.query(Recruiter).filter(Recruiter.email.contains(' ')).all()
    for r in spaced_emails:
        old_email = r.email
        clean_email = re.sub(r'\s+', '', old_email)
        # Check if clean_email already exists
        existing = db.query(Recruiter).filter(Recruiter.email == clean_email, Recruiter.recruiter_id != r.recruiter_id).first()
        if not existing:
            r.email = clean_email
            if r.repair_reason:
                r.repair_reason += "; cleaned_email_spaces"
            else:
                r.repair_reason = "cleaned_email_spaces"
            stats["emails_with_spaces_cleaned"] += 1
    db.commit()
    logger.info(f"Cleaned {stats['emails_with_spaces_cleaned']} emails containing spaces.")
    
    # 2. Fix recruiter_name when it contains an '@' sign
    logger.info("Step 2: Fixing recruiter names containing email addresses...")
    email_names = db.query(Recruiter).filter(Recruiter.recruiter_name.contains('@')).all()
    for r in email_names:
        prefix = r.recruiter_name.split('@')[0]
        extracted = format_name_from_email_prefix(prefix)
        if extracted:
            r.recruiter_name = extracted[:150]
            if r.normalized_recruiter_name:
                r.normalized_recruiter_name = extracted[:150].lower()
            stats["names_from_email_fixed"] += 1
            r.repair_reason = (r.repair_reason or "") + "; name_extracted_from_email"
    db.commit()
    logger.info(f"Fixed {stats['names_from_email_fixed']} names that were previously email addresses.")
    
    # 3. Fix company names erroneously put inside recruiter_name field
    logger.info("Step 3: Detecting and fixing company names placed inside recruiter_name...")
    # Inspect recruiters where name matches typical company words
    all_recs = db.query(Recruiter).filter(func.length(Recruiter.recruiter_name) > 3).all()
    for r in all_recs:
        name_lower = str(r.recruiter_name).lower()
        if any(f" {ind}" in name_lower or name_lower.endswith(f" {ind}") for ind in COMPANY_INDICATORS):
            # Check if we can extract actual human name from email
            if r.email and '@' in r.email and 'missing.local' not in r.email:
                prefix = r.email.split('@')[0]
                if prefix.lower() not in ['info', 'contact', 'hr', 'sales', 'support', 'admin', 'careers']:
                    extracted = format_name_from_email_prefix(prefix)
                    if extracted and extracted.lower() != name_lower:
                        # Ensure company is set properly if needed
                        if not r.company_id:
                            comp = db.query(Company).filter(Company.company_name.ilike(f"%{r.recruiter_name}%")).first()
                            if comp:
                                r.company_id = comp.company_id
                        
                        r.recruiter_name = extracted[:150]
                        if r.normalized_recruiter_name:
                            r.normalized_recruiter_name = extracted[:150].lower()
                        stats["company_names_in_recruiter_fixed"] += 1
                        r.repair_reason = (r.repair_reason or "") + "; company_name_moved_from_person_name"
    db.commit()
    logger.info(f"Fixed {stats['company_names_in_recruiter_fixed']} records where company name was inside recruiter_name.")
    
    # 4. Expand/repair short names or initials (<= 2 chars)
    logger.info("Step 4: Expanding short names/initials from email prefixes...")
    short_names = db.query(Recruiter).filter(func.length(Recruiter.recruiter_name) <= 2).all()
    for r in short_names:
        if r.email and '@' in r.email and 'missing.local' not in r.email:
            prefix = r.email.split('@')[0]
            extracted = format_name_from_email_prefix(prefix)
            if extracted and len(extracted) > 2 and extracted.lower() != r.recruiter_name.lower():
                r.recruiter_name = extracted[:150]
                if r.normalized_recruiter_name:
                    r.normalized_recruiter_name = extracted[:150].lower()
                stats["short_names_expanded"] += 1
                r.repair_reason = (r.repair_reason or "") + "; short_name_expanded_from_email"
                r.needs_review = False
    db.commit()
    logger.info(f"Expanded {stats['short_names_expanded']} short/initial names into full names.")
    
    # 5. Tag and organize placeholder emails
    logger.info("Step 5: Tagging missing.local placeholder emails cleanly...")
    placeholders = db.query(Recruiter).filter(Recruiter.email.contains('missing.local')).all()
    for r in placeholders:
        if r.email_status != 'missing_placeholder':
            r.email_status = 'missing_placeholder'
            r.repair_reason = (r.repair_reason or "") + "; placeholder_email_tagged"
            stats["placeholders_tagged"] += 1
    db.commit()
    logger.info(f"Tagged {stats['placeholders_tagged']} placeholder emails cleanly.")
    
    # 6. Recalculate completeness scores for all recruiters with repairs
    logger.info("Step 6: Updating completeness scores across the repaired records...")
    repaired_recs = db.query(Recruiter).filter(Recruiter.repair_reason != None).all()
    for r in repaired_recs:
        r.completeness_score = calculate_completeness(r)
        stats["completeness_updated"] += 1
        if r.completeness_score >= 50 and r.needs_review:
            r.needs_review = False
    db.commit()
    logger.info(f"Updated completeness scores on {stats['completeness_updated']} repaired records.")
    
    logger.info("=== REPAIR COMPLETE ===")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")

if __name__ == "__main__":
    repair_corrupted_recruiters()
