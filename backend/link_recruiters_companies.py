from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.routes.analytics import infer_company_from_domain, DOMAIN_DISPLAY_NAMES
from sqlalchemy import text
import re

db = SessionLocal()

free_domains = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'comcast.net', 'att.net',
    'sbcglobal.net', 'verizon.net', 'me.com', 'mail.com', 'protonmail.com',
    'ymail.com', 'cox.net', 'charter.net', 'earthlink.net', 'talentops.ai'
}

print("=== RECRUITER COMPANY LINKING & LOGO RESOLUTION ===")

# 1. Total recruiters missing company_id in PostgreSQL
unlinked = db.query(Recruiter).filter(Recruiter.company_id == None).all()
print(f"Recruiters missing company_id initially: {len(unlinked)}")

# Build lookup cache of existing companies by domain and lowercase name
all_companies = db.query(Company).all()
domain_to_comp = {}
name_to_comp = {}
for c in all_companies:
    if c.primary_domain:
        domain_to_comp[c.primary_domain.lower().strip()] = c
    if c.website:
        w_dom = c.website.lower().replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].strip()
        if w_dom:
            domain_to_comp[w_dom] = c
    if c.company_name:
        name_to_comp[c.company_name.lower().strip()] = c

linked_count = 0
created_count = 0

for r in unlinked:
    target_domain = None
    
    # Try extracting domain from email
    if r.email and '@' in r.email:
        d = r.email.split('@')[-1].lower().strip()
        if d not in free_domains and '.' in d:
            target_domain = d
            
    if target_domain:
        # Match existing company
        if target_domain in domain_to_comp:
            matched_company = domain_to_comp[target_domain]
            r.company_id = matched_company.company_id
            linked_count += 1
        else:
            # Create company
            c_name = DOMAIN_DISPLAY_NAMES.get(target_domain) or infer_company_from_domain(target_domain) or target_domain.split('.')[0].title()
            new_comp = Company(
                company_name=c_name,
                canonical_name=c_name,
                primary_domain=target_domain,
                website=f"https://{target_domain}",
                logo_url=f"https://logos.hunter.io/{target_domain}",
                verification_status="verified",
                trust_score=100
            )
            db.add(new_comp)
            db.flush()
            domain_to_comp[target_domain] = new_comp
            r.company_id = new_comp.company_id
            created_count += 1

db.commit()
print(f"Successfully linked {linked_count} recruiters to existing companies.")
print(f"Created and linked {created_count} new canonical companies with high-res logos.")

# Check final count of remaining unlinked
remaining = db.query(Recruiter).filter(Recruiter.company_id == None).count()
total_now = db.query(Recruiter).count()
print(f"Final state: {remaining} of {total_now} recruiters without company_id (freemail/personal only).")
