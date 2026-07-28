import pandas as pd
import re
import os
import sys
from collections import defaultdict

# Add backend directory to path so we can import models
sys.path.append(r"C:\TalentOpsAI\backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Recruiter, Company
from app.utils.normalizer import extract_domain
from dotenv import load_dotenv

load_dotenv(r"C:\TalentOpsAI\backend\.env")
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL not found in .env")

def clean_name(name):
    if pd.isna(name): return None
    s_name = str(name).strip()
    if not s_name or s_name.lower() == 'nan': return None
    # Strip non-breaking spaces and clean whitespace
    name = re.sub(r'\s+', ' ', s_name.replace('\xa0', ' ')).strip()
    return name.title()

def clean_email(email):
    if pd.isna(email): return None
    s_email = str(email).replace('\xa0', '').strip().lower()
    if not s_email or s_email == 'nan': return None
    if re.match(r"[^@]+@[^@]+\.[^@]+", s_email):
        return s_email
    return None

def clean_phone(phone):
    if pd.isna(phone): return None
    s_phone = str(phone).strip()
    if not s_phone or s_phone.lower() == 'nan': return None
    # Extract only digits
    digits = re.sub(r'\D+', '', s_phone)
    if len(digits) >= 10:
        # Format as standard US if 10 digits
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return digits
    return None

def process_file(file_path):
    print(f"--- STAGE 1: Reading File ---")
    df = pd.read_excel(file_path, header=None)
    # The file has extra columns which causes index shifting if we use names=[]
    df = df.iloc[:, :3]
    df.columns = ['Name', 'Email', 'Phone']
    print(f"Loaded {len(df)} rows.")

    print(f"--- STAGE 2: Normalization ---")
    df['Name'] = df['Name'].apply(clean_name)
    df['Email'] = df['Email'].apply(clean_email)
    df['Phone'] = df['Phone'].apply(clean_phone)
    
    # Drop rows where everything is missing
    df = df.dropna(how='all')
    print(f"After cleaning and dropping empties, {len(df)} rows remain.")

    print(f"--- STAGE 3 & 4: Intra-File Consolidation ---")
    # Group by name to consolidate multiple emails/phones for the same person
    profiles = defaultdict(lambda: {'emails': set(), 'phones': set(), 'name': None})
    
    # We will also try grouping by email if name is missing but email is present
    for _, row in df.iterrows():
        name = row['Name'] if pd.notna(row['Name']) else None
        email = row['Email'] if pd.notna(row['Email']) else None
        phone = row['Phone'] if pd.notna(row['Phone']) else None
        
        # Primary key for internal merging is Name if available, otherwise email
        key = name if name else email
        if not key:
            continue
            
        profiles[key]['name'] = name
        if email: profiles[key]['emails'].add(email)
        if phone: profiles[key]['phones'].add(phone)
        
    print(f"Consolidated into {len(profiles)} unique rich profiles.")
    return profiles

def smart_merge(profiles, dry_run=True):
    print(f"\n--- STAGE 5 & 6: Database Comparison & Smart Merge ---")
    
    # Fix for PgBouncer / psycopg3 prepared statement errors
    connect_args = {}
    if "postgresql" in DB_URL:
        connect_args["prepare_threshold"] = None
        
    engine = create_engine(
        DB_URL, 
        pool_pre_ping=True, 
        connect_args=connect_args
    )
    
    # BARRY FIX: Enforce 75% Storage Kill-Switch BEFORE running imports!
    from app.services.storage_limit_service import get_database_size, DB_SIZE_LIMIT_BYTES
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    db_size = get_database_size(session)
    if db_size >= DB_SIZE_LIMIT_BYTES:
        session.close()
        raise RuntimeError(f"Storage Kill-Switch Activated: Database capacity is over the 75% safety limit ({db_size / 1024 / 1024:.2f} MB / 375.0 MB). Import aborted.")
    else:
        print(f"[KILL-SWITCH PASSED]: Current DB usage is safe ({db_size / 1024 / 1024:.2f} MB)")
    
    # Ensure all tables exist in the local DB
    from app.models.models import Base
    Base.metadata.create_all(engine)
    
    stats = {
        'new_inserted': 0,
        'existing_updated': 0,
        'exact_duplicates_skipped': 0,
        'conflicts_flagged': 0,
        'skipped_no_email': 0
    }
    
    report_lines = []

    try:
        # Get all existing recruiters for fast lookup
        existing_recruiters = session.query(Recruiter).all()
        
        # Lookup tables
        email_to_recruiter = {}
        for r in existing_recruiters:
            for e in [r.email, r.email2, r.email3, r.email4]:
                if e: email_to_recruiter[e] = r
                
        phone_to_recruiter = {}
        for r in existing_recruiters:
            for p in [r.phone, r.phone2, r.phone3, r.phone4]:
                if p: phone_to_recruiter[p] = r

        for key, p in profiles.items():
            match = None
            # Find match by email
            for email in p['emails']:
                if email in email_to_recruiter:
                    match = email_to_recruiter[email]
                    break
            
            # Find match by phone if no email match
            if not match:
                for phone in p['phones']:
                    if phone in phone_to_recruiter:
                        match = phone_to_recruiter[phone]
                        break
                        
            if match:
                # WE FOUND A MATCH! SMART APPEND!
                updated = False
                
                # Check emails
                existing_emails = {match.email, match.email2, match.email3, match.email4}
                for email in p['emails']:
                    if email not in existing_emails:
                        # Append to next available slot
                        if not match.email2: match.email2 = email; updated = True
                        elif not match.email3: match.email3 = email; updated = True
                        elif not match.email4: match.email4 = email; updated = True
                        else:
                            report_lines.append(f"CONFLICT: Recruiter {match.recruiter_name} has no more email slots for {email}")
                            stats['conflicts_flagged'] += 1
                
                # Check phones
                existing_phones = {match.phone, match.phone2, match.phone3, match.phone4}
                for phone in p['phones']:
                    if phone not in existing_phones:
                        # Append to next available slot
                        if not match.phone: match.phone = phone; updated = True
                        elif not match.phone2: match.phone2 = phone; updated = True
                        elif not match.phone3: match.phone3 = phone; updated = True
                        elif not match.phone4: match.phone4 = phone; updated = True
                        else:
                            report_lines.append(f"CONFLICT: Recruiter {match.recruiter_name} has no more phone slots for {phone}")
                            stats['conflicts_flagged'] += 1
                
                if updated:
                    stats['existing_updated'] += 1
                    report_lines.append(f"MERGED: Enriched existing profile {match.recruiter_name} (ID: {match.recruiter_id})")
                else:
                    stats['exact_duplicates_skipped'] += 1
                    
            else:
                # NEW RECRUITER
                # Extract domain to infer company logic if needed later
                # For now, just create the recruiter
                emails = list(p['emails'])
                phones = list(p['phones'])
                
                if len(emails) == 0:
                    stats['skipped_no_email'] += 1
                    report_lines.append(f"SKIPPED (No Email): {p['name'] or 'Unknown'}")
                    continue
                
                new_rec = Recruiter(
                    recruiter_name=p['name'] or "Unknown",
                    email=emails[0] if len(emails) > 0 else None,
                    email2=emails[1] if len(emails) > 1 else None,
                    phone=phones[0] if len(phones) > 0 else None,
                    phone2=phones[1] if len(phones) > 1 else None,
                    user_id=1, # Default user_id for system/admin import
                    data_source="JUN 18 Excel Import"
                )
                session.add(new_rec)
                stats['new_inserted'] += 1
                report_lines.append(f"INSERTED: New profile for {new_rec.recruiter_name}")
                
                # Add to local lookup to prevent duplicates within the same batch being inserted twice
                if new_rec.email: email_to_recruiter[new_rec.email] = new_rec
                if new_rec.phone: phone_to_recruiter[new_rec.phone] = new_rec

        if dry_run:
            print("\n[DRY RUN] Rolling back transaction.")
            session.rollback()
        else:
            print("\n[LIVE RUN] Committing to database.")
            session.commit()
            
    except Exception as e:
        session.rollback()
        print(f"FATAL ERROR: {e}")
    finally:
        session.close()

    print(f"\n--- STAGE 8: Import Report ---")
    print(f"New Recruiters Inserted:   {stats['new_inserted']}")
    print(f"Existing Profiles Merged:  {stats['existing_updated']}")
    print(f"Exact Duplicates Skipped:  {stats['exact_duplicates_skipped']}")
    print(f"Conflicts Flagged:         {stats['conflicts_flagged']}")
    print(f"Skipped (No Email):        {stats['skipped_no_email']}")
    print("\nSnippet of action log:")
    for line in report_lines[:15]:
        print("  -", line)
    if len(report_lines) > 15:
        print(f"  ... and {len(report_lines)-15} more actions.")

if __name__ == "__main__":
    import sys
    dry = "--live" not in sys.argv
    file_path = r"C:\Users\User\Desktop\JUN 18 FOR DATABASW.xlsx"
    profiles = process_file(file_path)
    smart_merge(profiles, dry_run=dry)
