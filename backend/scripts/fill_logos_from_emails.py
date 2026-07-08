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
    "protonmail.com", "ymail.com"
}

def fill_logos_from_emails():
    db = SessionLocal()
    
    # Get all companies missing a website
    companies = db.query(Company).filter(
        (Company.website == None) | (Company.website == '')
    ).all()
    
    logger.info(f"Found {len(companies)} companies missing websites (logos).")
    
    updated_count = 0
    
    for company in companies:
        # Find all recruiters for this company
        recruiters = db.query(Recruiter).filter(Recruiter.company_id == company.company_id).all()
        
        domain_counts = {}
        for r in recruiters:
            if r.email and '@' in r.email:
                domain = r.email.split('@')[-1].lower().strip()
                if domain and domain not in GENERIC_DOMAINS:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    
        if domain_counts:
            # Pick the most common non-generic domain
            best_domain = max(domain_counts.items(), key=lambda x: x[1])[0]
            
            company.website = best_domain
            if not company.email_pattern:
                company.email_pattern = best_domain
            updated_count += 1
            
            if updated_count % 500 == 0:
                logger.info(f"Updated {updated_count} companies... (Latest: {company.company_name} -> {best_domain})")
                db.commit()
                
    db.commit()
    logger.info(f"Finished! Successfully extracted domains and populated logos for {updated_count} companies.")

if __name__ == "__main__":
    fill_logos_from_emails()
