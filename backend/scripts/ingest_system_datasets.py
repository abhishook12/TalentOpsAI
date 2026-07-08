import os
import sys
import logging
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SEARCH_DIRS = [
    r'C:\Users\User\Downloads',
    r'C:\Users\User\Desktop',
    r'C:\Users\User\Documents',
    r'C:\TalentOpsAI\exports'
]

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "msn.com", "live.com", "me.com", "mac.com"
}

def clean_domain(domain):
    if not domain: return None
    return str(domain).lower().strip().replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]

def ingest_system_datasets():
    db = SessionLocal()
    
    # Load existing emails to avoid duplicates
    logger.info("Loading existing recruiter emails from database into memory...")
    existing_emails = set(e[0].lower() for e in db.query(Recruiter.email).filter(Recruiter.email != None).all() if e[0])
    logger.info(f"Loaded {len(existing_emails)} existing unique emails.")
    
    # Load domain -> company_id map
    domain_map = {}
    for c_id, web, emp, name in db.query(Company.company_id, Company.website, Company.email_pattern, Company.company_name).all():
        if web: domain_map[clean_domain(web)] = (c_id, name)
        if emp: domain_map[clean_domain(emp)] = (c_id, name)
        
    total_new_recruiters = 0
    total_new_companies = 0
    
    for folder in SEARCH_DIRS:
        if not os.path.exists(folder): continue
        logger.info(f"Scanning folder: {folder}")
        for root, dirs, files in os.walk(folder):
            if any(x in root for x in ['node_modules', 'venv', '.git', '__pycache__']): continue
            for file in files:
                if not file.endswith(('.csv', '.xlsx')) or file.startswith('.'): continue
                filepath = os.path.join(root, file)
                try:
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    if size_mb > 50 or size_mb < 0.05: continue # Skip tiny (<50KB) or gigantic (>50MB)
                    
                    logger.info(f"Checking {file} ({round(size_mb, 2)} MB)...")
                    if file.endswith('.csv'):
                        df = pd.read_csv(filepath, low_memory=False, on_bad_lines='skip')
                    else:
                        df = pd.read_excel(filepath)
                        
                    # Find email column
                    email_col = next((c for c in df.columns if 'email' in str(c).lower()), None)
                    if not email_col: continue
                    
                    name_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['name', 'full_name', 'recruiter', 'contact'])), None)
                    comp_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['company', 'org', 'firm', 'employer'])), None)
                    title_col = next((c for c in df.columns if 'title' in str(c).lower() or 'role' in str(c).lower()), None)
                    phone_col = next((c for c in df.columns if 'phone' in str(c).lower() or 'mobile' in str(c).lower()), None)
                    
                    new_batch = []
                    for _, row in df.iterrows():
                        email = str(row[email_col]).strip().lower()
                        if not email or '@' not in email or email in existing_emails or len(email) > 120: continue
                        
                        existing_emails.add(email)
                        
                        name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else email.split('@')[0].replace('.', ' ').title()
                        comp_name = str(row[comp_col]).strip() if comp_col and pd.notna(row[comp_col]) else None
                        title = str(row[title_col]).strip() if title_col and pd.notna(row[title_col]) else "Recruiter"
                        phone = str(row[phone_col]).strip() if phone_col and pd.notna(row[phone_col]) else None
                        
                        domain = clean_domain(email.split('@')[-1])
                        company_id = None
                        
                        if domain and domain not in GENERIC_DOMAINS:
                            if domain in domain_map:
                                company_id, cached_name = domain_map[domain]
                                if not comp_name: comp_name = cached_name
                            else:
                                if not comp_name: comp_name = domain.capitalize()
                                new_comp = Company(
                                    company_name=comp_name[:100],
                                    website=domain,
                                    email_pattern=domain,
                                    data_source="system_import_newly_added"
                                )
                                db.add(new_comp)
                                db.commit()
                                db.refresh(new_comp)
                                company_id = new_comp.company_id
                                domain_map[domain] = (company_id, comp_name)
                                total_new_companies += 1
                                
                        new_rec = Recruiter(
                            recruiter_name=name[:150],
                            normalized_recruiter_name=name[:150].lower(),
                            email=email,
                            company_id=company_id,
                            title=title[:150] if title else "Recruiter",
                            phone=phone[:30] if phone else None,
                            data_source="system_import_newly_added"
                        )
                        db.add(new_rec)
                        total_new_recruiters += 1
                        
                        if total_new_recruiters % 500 == 0:
                            db.commit()
                            logger.info(f"Imported {total_new_recruiters} new recruiters so far...")
                    
                    db.commit()
                except Exception as e:
                    logger.warning(f"Skipped {file} due to: {e}")
                    db.rollback()
                    
    logger.info(f"System Scan Complete! Added {total_new_recruiters} newly discovered recruiters and {total_new_companies} new companies.")

if __name__ == "__main__":
    ingest_system_datasets()
