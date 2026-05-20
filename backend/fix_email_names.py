import os
import sys
import re
from sqlalchemy.orm import Session
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def is_company_name(s, email_domain):
    if not s: return False
    s_lower = s.lower()
    keywords = ['llc', 'inc', 'consulting', 'solutions', 'technologies', 'staffing', 'professionals', 'group', 'partners', 'corp', 'tech', 'services', 'systems', 'scientific', 'llp']
    if any(kw in s_lower.split() for kw in keywords):
        return True
    
    # Check if the name matches the domain e.g. "Epm" -> "epmscientific.com"
    domain_letters = re.sub(r'[^a-z]', '', email_domain.lower())
    name_letters = re.sub(r'[^a-z]', '', s_lower)
    if len(name_letters) >= 3 and name_letters in domain_letters:
        return True
    return False

def extract_name_from_email(email):
    if not email or '@' not in email:
        return None
    prefix = email.split('@')[0]
    # Replace dots, underscores, hyphens with space
    clean = re.sub(r'[\._\-]', ' ', prefix)
    # Remove numbers
    clean = re.sub(r'[0-9]', '', clean)
    clean = clean.strip()
    
    if not clean: return None
    
    # Title case
    return clean.title()

def main():
    db = SessionLocal()
    
    companies_cache = {}
    for c in db.query(Company).all():
        companies_cache[c.company_name.lower()] = c.company_id
        
    recruiters = db.query(Recruiter).all()
    updates = []
    
    for r in recruiters:
        if not r.email or '@' not in r.email:
            continue
            
        domain = r.email.split('@')[1]
        extracted = extract_name_from_email(r.email)
        if not extracted:
            continue
            
        current = r.recruiter_name or ""
        
        # Check if we should upgrade/overwrite
        ext_lower = extracted.lower()
        cur_lower = current.lower()
        
        should_update = False
        new_company_id = r.company_id
        
        if cur_lower == ext_lower:
            continue
            
        # If current name is just a part of the extracted name (e.g. current: Jane, extracted: Jane Ni) -> Upgrade
        if cur_lower in ext_lower.split():
            should_update = True
            
        # If current name contains the extracted name (e.g. extracted: Jared, current: Jared Smith) -> Keep current
        elif ext_lower in cur_lower.split():
            continue
            
        # If totally different (or current is empty)
        else:
            should_update = True
            # If current looks like a company, save it as company
            if current and not r.company_id and is_company_name(current, domain):
                c_name_lower = current.lower()
                if c_name_lower in companies_cache:
                    new_company_id = companies_cache[c_name_lower]
                else:
                    new_c = Company(company_name=current)
                    db.add(new_c)
                    db.flush() # flush to get id without committing transaction yet
                    companies_cache[c_name_lower] = new_c.company_id
                    new_company_id = new_c.company_id

        if should_update:
            r.recruiter_name = extracted
            if new_company_id != r.company_id:
                r.company_id = new_company_id
            updates.append(r)
            
    print(f"Updating {len(updates)} recruiters...")
    db.commit()
    print("Done!")

if __name__ == '__main__':
    main()
