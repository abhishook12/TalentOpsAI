import os
import sys
import pandas as pd
import glob
from sqlalchemy.orm import Session
from sqlalchemy import or_
import gc

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company

def clean_phone(phone_str):
    if pd.isna(phone_str) or not str(phone_str).strip():
        return None
    cleaned = ''.join(c for c in str(phone_str) if c.isdigit())
    if len(cleaned) == 10:
        return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 11 and cleaned.startswith('1'):
        return f"{cleaned[1:4]}-{cleaned[4:7]}-{cleaned[7:]}"
    return str(phone_str).strip()

def clean_email(email_str):
    if pd.isna(email_str) or not str(email_str).strip():
        return None
    return str(email_str).strip().lower()

def clean_string(val):
    if pd.isna(val) or not str(val).strip():
        return None
    return str(val).strip()

def process_recruiter_files(db: Session):
    files = glob.glob('C:/Users/User/Desktop/for talent ops cleaned*.xlsx')
    
    total_companies_created = 0
    total_recruiters_created = 0
    total_recruiters_merged = 0

    print("Pre-fetching companies...", flush=True)
    companies_cache = {c.normalized_company_name: c for c in db.query(Company).all() if c.normalized_company_name}
    
    print("Pre-fetching recruiters...", flush=True)
    recruiters_by_email = {r.email: r for r in db.query(Recruiter).filter(Recruiter.email.isnot(None)).all()}

    for file in files:
        print(f"Processing {file}...", flush=True)
        try:
            df = pd.read_excel(file, dtype=str)
        except Exception as e:
            print(f"Failed to read {file}: {e}", flush=True)
            continue
            
        print(f"Loaded {len(df)} rows.", flush=True)
        
        batch_size = 5000
        for i, row in df.iterrows():
            if i % 1000 == 0 and i > 0:
                print(f"  Processed {i}/{len(df)} rows...", flush=True)
                
            c_name = clean_string(row.get('company'))
            r_name = clean_string(row.get('name'))
            r_email = clean_email(row.get('email'))
            r_phone = clean_phone(row.get('phone'))
            
            if not c_name and not r_name and not r_email:
                continue
                
            company = None
            if c_name:
                norm_c = c_name.strip().lower().replace(" ", "").replace(",", "").replace(".", "").replace("inc", "").replace("llc", "")
                if norm_c in companies_cache:
                    company = companies_cache[norm_c]
                else:
                    company = Company(
                        company_name=c_name,
                        normalized_company_name=norm_c,
                        data_source="desktop_injection"
                    )
                    db.add(company)
                    db.flush()
                    companies_cache[norm_c] = company
                    total_companies_created += 1

            if r_email or r_name:
                recruiter = recruiters_by_email.get(r_email) if r_email else None
                
                if recruiter:
                    updated = False
                    if not recruiter.phone and r_phone:
                        recruiter.phone = r_phone
                        updated = True
                    if updated:
                        total_recruiters_merged += 1
                else:
                    recruiter = Recruiter(
                        recruiter_name=r_name or (r_email.split("@")[0].replace(".", " ").title() if r_email else "Unknown"),
                        email=r_email,
                        phone=r_phone,
                        company_id=company.company_id if company else None,
                        data_source="desktop_injection",
                        email_status="verified" if r_email else "unknown",
                        email_confidence=100 if r_email else 0
                    )
                    db.add(recruiter)
                    if r_email:
                        recruiters_by_email[r_email] = recruiter
                    total_recruiters_created += 1
                    
            if i % batch_size == 0 and i > 0:
                db.commit()
                gc.collect()
                
        db.commit()
        
    return total_companies_created, total_recruiters_created, total_recruiters_merged

def process_company_file(db: Session):
    file = 'C:/Users/User/Desktop/FOR ANTIGRAVITY.xlsx'
    if not os.path.exists(file):
        return 0, 0
        
    print(f"Processing {file}...", flush=True)
    df = pd.read_excel(file, header=None, dtype=str)
    print(f"Loaded {len(df)} rows.", flush=True)
    
    total_companies_created = 0
    total_companies_merged = 0
    
    companies_cache = {c.normalized_company_name: c for c in db.query(Company).all() if c.normalized_company_name}

    for i, row in df.iterrows():
        if i % 1000 == 0 and i > 0:
            print(f"  Processed {i}/{len(df)} rows...", flush=True)
            
        c_name = clean_string(row.get(0))
        c_website = clean_string(row.get(1))
        c_linkedin = clean_string(row.get(2))
        
        if not c_name:
            continue
            
        norm_c = c_name.strip().lower().replace(" ", "").replace(",", "").replace(".", "").replace("inc", "").replace("llc", "")
        
        if norm_c in companies_cache:
            company = companies_cache[norm_c]
            updated = False
            if not company.website and c_website:
                company.website = c_website
                updated = True
            if not company.linkedin and c_linkedin:
                company.linkedin = c_linkedin
                updated = True
                
            if updated:
                total_companies_merged += 1
        else:
            company = Company(
                company_name=c_name,
                normalized_company_name=norm_c,
                website=c_website,
                linkedin=c_linkedin,
                data_source="desktop_injection"
            )
            db.add(company)
            db.flush()
            companies_cache[norm_c] = company
            total_companies_created += 1

    db.commit()
    return total_companies_created, total_companies_merged

if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Starting Data Injection...", flush=True)
        c_created_r, r_created, r_merged = process_recruiter_files(db)
        print(f"\nRecruiter Files -> Companies Created: {c_created_r}", flush=True)
        print(f"Recruiter Files -> Recruiters Created: {r_created}", flush=True)
        print(f"Recruiter Files -> Recruiters Merged: {r_merged}", flush=True)
        
        c_created_c, c_merged = process_company_file(db)
        print(f"\nCompany File -> Companies Created: {c_created_c}", flush=True)
        print(f"Company File -> Companies Merged: {c_merged}", flush=True)
        
        print("\nData Injection Complete!", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        db.rollback()
    finally:
        db.close()
