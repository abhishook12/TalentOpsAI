import os
import sys
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Company, Recruiter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "msn.com", "live.com", "me.com", "mac.com", "googlemail.com",
    "protonmail.com", "ymail.com", "mail.com", "comcast.net", "sbcglobal.net"
}

def clean_domain(domain):
    if not domain: return None
    domain = domain.lower().strip()
    return domain

def assign_orphaned_recruiters():
    db = SessionLocal()
    
    # Get all recruiters missing a company
    recruiters = db.query(Recruiter).filter(
        Recruiter.company_id == None,
        Recruiter.email != None,
        Recruiter.email != ''
    ).all()
    
    total = len(recruiters)
    logger.info(f"Found {total} recruiters with an email but no company_id.")
    
    if total == 0:
        return
        
    updated_count = 0
    new_companies_created = 0
    skipped_generic = 0
    
    # Cache for domain -> company_id to avoid querying the DB for every recruiter
    domain_to_company_id = {}
    
    for i, recruiter in enumerate(recruiters):
        if not recruiter.email or '@' not in recruiter.email:
            continue
            
        domain = clean_domain(recruiter.email.split('@')[-1])
        if not domain or domain in GENERIC_DOMAINS:
            skipped_generic += 1
            continue
            
        company_id = domain_to_company_id.get(domain)
        company_name = None
        
        if not company_id:
            # Look up company by email_pattern or website
            existing_company = db.query(Company).filter(
                (func.lower(Company.email_pattern) == domain) |
                (func.lower(Company.website) == domain)
            ).first()
            
            if existing_company:
                company_id = existing_company.company_id
                company_name = existing_company.company_name
                domain_to_company_id[domain] = company_id
            else:
                # Auto-create new company
                new_company = Company(
                    company_name=domain.capitalize(),
                    website=domain,
                    email_pattern=domain,
                    data_source="domain_inference"
                )
                db.add(new_company)
                db.commit() # Commit to get the ID immediately
                db.refresh(new_company)
                
                company_id = new_company.company_id
                company_name = new_company.company_name
                domain_to_company_id[domain] = company_id
                new_companies_created += 1
                logger.info(f"Created new company '{company_name}' for domain {domain}")
        else:
            # If we got it from cache, we don't strictly have the name cached, but we can just use the domain
            company_name = domain.capitalize()
            
        recruiter.company_id = company_id
            
        updated_count += 1
        
        # Batch commit every 500
        if updated_count % 500 == 0:
            db.commit()
            logger.info(f"Processed {updated_count} recruiters so far...")
            
    # Final commit
    db.commit()
    logger.info(f"Finished! Assigned {updated_count} recruiters to companies.")
    logger.info(f"Created {new_companies_created} new companies in the process.")
    logger.info(f"Skipped {skipped_generic} recruiters with generic email domains.")

if __name__ == "__main__":
    assign_orphaned_recruiters()
