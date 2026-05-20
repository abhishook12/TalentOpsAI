import os
import sys
import openpyxl
import re
from sqlalchemy.orm import Session
from sqlalchemy import text
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def is_company_name(s):
    if not s: return False
    s_lower = s.lower()
    keywords = ['llc', 'inc', 'consulting', 'solutions', 'technologies', 'staffing', 'professionals', 'group', 'partners', 'corp', 'tech', 'services', 'systems', 'llp']
    return any(kw in s_lower.split() for kw in keywords)

def main():
    FILE = r'C:\Users\User\Desktop\TalentOps_Recruiters_Formatted.xlsx'
    if not os.path.exists(FILE):
        print("Excel file not found.")
        return
        
    print("Loading excel...")
    wb = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
    ws = wb.active
    
    db = SessionLocal()
    
    print("Loading existing companies...")
    companies_cache = {} # lower_name -> company_id
    for c in db.query(Company).all():
        companies_cache[c.company_name.lower()] = c.company_id
        
    print("Loading existing recruiters...")
    recruiters_map = {} # email -> recruiter_id
    for r in db.query(Recruiter).with_entities(Recruiter.recruiter_id, Recruiter.email, Recruiter.recruiter_name, Recruiter.company_id).all():
        if r.email:
            recruiters_map[r.email.lower()] = {
                'id': r.recruiter_id,
                'name': r.recruiter_name,
                'company_id': r.company_id
            }

    update_mappings = []
    
    print("Processing rows...")
    for i, row in enumerate(ws.iter_rows(min_row=17, values_only=True)):
        comp = str(row[0]).strip() if row[0] else None
        name = str(row[1]).strip() if row[1] else None
        email = str(row[2]).strip().lower() if row[2] else None
        
        if not email or email not in recruiters_map:
            continue
            
        r_info = recruiters_map[email]
            
        # Swap logic
        actual_company = comp
        actual_name = name
        
        if comp and name:
            if is_company_name(name) and not is_company_name(comp):
                actual_company = name
                actual_name = comp
            elif email.split('@')[0].lower() in re.sub(r'[^a-z]', '', comp.lower()):
                 actual_company = name
                 actual_name = comp
                 
        if not actual_name:
            actual_name = email.split('@')[0].title()
            
        # Handle Company
        c_id = None
        if actual_company and actual_company.lower() not in ('none', 'n/a', 'null', '-'):
            c_name_lower = actual_company.lower()
            if c_name_lower in companies_cache:
                c_id = companies_cache[c_name_lower]
            else:
                new_c = Company(company_name=actual_company)
                db.add(new_c)
                db.commit()
                db.refresh(new_c)
                companies_cache[c_name_lower] = new_c.company_id
                c_id = new_c.company_id
                
        # Check if update is needed
        if r_info['name'] != actual_name or r_info['company_id'] != c_id:
            update_mappings.append({
                'recruiter_id': r_info['id'],
                'recruiter_name': actual_name,
                'company_id': c_id
            })

    print(f"Executing bulk update for {len(update_mappings)} recruiters...")
    if update_mappings:
        db.bulk_update_mappings(Recruiter, update_mappings)
        db.commit()
        
    print(f"Done! Smartly fixed and updated {len(update_mappings)} recruiters.")

if __name__ == '__main__':
    main()
