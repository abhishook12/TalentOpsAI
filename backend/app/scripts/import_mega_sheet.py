import os
import sys
import pandas as pd
import re
import json
import uuid
from datetime import datetime, timezone

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import SessionLocal
from app.models.models import Recruiter, Company, UploadJob
from sqlalchemy.orm import Session
from sqlalchemy import text

STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

COMPANY_KEYWORDS = ['llc', 'inc', 'group', 'consulting', 'solutions', 'technology', 'technologies', 'services', 'partners', 'staffing', 'resources', 'search', 'talent']
TITLE_KEYWORDS = ['recruiter', 'manager', 'sourcer', 'talent', 'director', 'executive', 'specialist', 'head', 'lead', 'partner']

def parse_block(block):
    person = {'emails': [], 'phones': [], 'name': '', 'company': '', 'title': '', 'state': '', 'location': '', 'notes': []}
    for j, val in block:
        val = str(val).strip()
        if not val or val.lower() == 'nan':
            continue
            
        # Email
        if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", val):
            person['emails'].append(val.lower())
            continue
            
        # Phone
        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", val)
        if phone_match:
            phone_str = phone_match.group(0)
            phone_digits = re.sub(r"[^\d]", "", phone_str)
            if len(phone_digits) == 10:
                person['phones'].append(f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}")
            else:
                person['phones'].append(phone_str[:30])
            continue
            
        # State
        if len(val) == 2 and val.upper() in STATE_CODES:
            person['state'] = val.upper()
            continue
            
        # Location (City, ST)
        if ',' in val and len(val.split(',')[-1].strip()) == 2 and val.split(',')[-1].strip().upper() in STATE_CODES:
            person['location'] = val.title()
            person['state'] = val.split(',')[-1].strip().upper()
            continue
            
        # Company
        if any(k in val.lower() for k in COMPANY_KEYWORDS):
            if not person['company']:
                person['company'] = val.title()
            else:
                person['notes'].append(val)
            continue
            
        # Title
        if any(k in val.lower() for k in TITLE_KEYWORDS):
            person['title'] = val.title()
            continue
            
        # Name (heuristic: 2-3 words, no numbers, relatively short)
        if len(val.split()) in [2, 3] and not re.search(r"\d", val) and len(val) < 30 and not person['name']:
            person['name'] = val.title()
            continue
            
        # Extra/Notes
        person['notes'].append(val)
        
    # Fallback to assign the first note as the name if name is empty and it looks plausible
    if not person['name'] and person['notes']:
        first_note = person['notes'][0]
        if len(first_note.split()) in [2, 3] and len(first_note) < 30:
            person['name'] = first_note.title()
            person['notes'].pop(0)

    # Fallback to extract company from email domain if company is missing
    if not person['company'] and person['emails']:
        domain = person['emails'][0].split('@')[-1]
        if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']:
            person['company'] = domain.split('.')[0].title()

    return person

def run_import(excel_path):
    print(f"Reading {excel_path} ...")
    df = pd.read_excel(excel_path, header=None)
    df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
    
    people = []
    email_index = {}
    phone_index = {}
    name_company_index = {}
    
    print("Extracting blocks and classifying...")
    for row in df.itertuples(index=False):
        row = [str(x).strip() if pd.notna(x) else '' for x in row]
        blocks = []
        current_block = []
        
        for j, cell in enumerate(row):
            if not cell or cell.lower() == 'nan' or cell.lower() == 'none':
                continue
                
            if not current_block:
                current_block.append((j, cell))
            else:
                if j - current_block[-1][0] <= 5:
                    current_block.append((j, cell))
                else:
                    blocks.append(current_block)
                    current_block = [(j, cell)]
        if current_block:
            blocks.append(current_block)
            
        for block in blocks:
            text_concat = " ".join([c[1].lower() for c in block])
            if "contact #1" in text_concat and "email id" in text_concat and not "@" in text_concat:
                continue

            person = parse_block(block)
            if person['emails'] or person['phones'] or (person['name'] and person['company']):
                
                matched = None
                for e in person['emails']:
                    if e in email_index:
                        matched = email_index[e]
                        break
                
                if not matched:
                    for p in person['phones']:
                        if p in phone_index:
                            matched = phone_index[p]
                            break
                
                if not matched and person['name'] and person['company']:
                    nc_key = f"{person['name'].lower()}::{person['company'].lower()}"
                    if nc_key in name_company_index:
                        matched = name_company_index[nc_key]
                            
                if matched:
                    # Merge
                    matched['emails'] = list(dict.fromkeys(matched['emails'] + person['emails']))
                    matched['phones'] = list(dict.fromkeys(matched['phones'] + person['phones']))
                    if not matched['name']: matched['name'] = person['name']
                    if not matched['company']: matched['company'] = person['company']
                    if not matched['title']: matched['title'] = person['title']
                    if not matched['state']: matched['state'] = person['state']
                    if not matched['location']: matched['location'] = person['location']
                    matched['notes'].extend(person['notes'])
                else:
                    people.append(person)
                    matched = person
                
                # Update high-speed indexes
                for e in matched['emails']: email_index[e] = matched
                for p in matched['phones']: phone_index[p] = matched
                if matched['name'] and matched['company']:
                    name_company_index[f"{matched['name'].lower()}::{matched['company'].lower()}"] = matched

    print(f"Extracted {len(people)} unique normalized records.")
    
    # Save to db
    db = SessionLocal()
    try:
        job = UploadJob(
            job_id=str(uuid.uuid4()),
            filename="final updated sheet.xlsx",
            status="processing",
            total_rows=len(people),
            processed_rows=0,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(job)
        db.commit()

        companies_cache = {}
        for c in db.query(Company).all():
            if c.company_name:
                companies_cache[c.company_name.lower()] = c.company_id

        # Pre-fetch existing emails to prevent database unique constraint violations
        existing_emails = {row[0].lower() for row in db.execute(text("SELECT email FROM recruiters WHERE email IS NOT NULL")).fetchall()}

        inserted_recruiters = 0
        for p in people:
            if not p['emails'] and not p['phones']: 
                continue # Skip pure junk
                
            final_email = p['emails'][0] if p['emails'] else (f"no-email-{re.sub(r'[^0-9]', '', p['phones'][0])}@missing.local" if p['phones'] else f"no-email-{uuid.uuid4().hex[:8]}@missing.local")
            if final_email in existing_emails:
                continue
            existing_emails.add(final_email)
                
            c_id = None
            if p['company']:
                c_name = p['company'][:100]
                c_lower = c_name.lower()
                if c_lower in companies_cache:
                    c_id = companies_cache[c_lower]
                else:
                    new_comp = Company(
                        company_name=c_name,
                        website=p['emails'][0].split('@')[-1] if p['emails'] else None
                    )
                    db.add(new_comp)
                    db.flush()
                    c_id = new_comp.company_id
                    companies_cache[c_lower] = c_id

            rec = Recruiter(
                company_id=c_id,
                recruiter_name=p['name'][:100] if p['name'] else "Unknown",
                email=final_email,
                phone=p['phones'][0] if p['phones'] else None,
                location=p['location'][:100] if p['location'] else None,
                state=p['state'][:2] if p['state'] else None,
                title=p['title'][:100] if p['title'] else None,
                notes="; ".join(p['notes'])[:500] if p['notes'] else None,
                email2=p['emails'][1] if len(p['emails']) > 1 else None,
                email3=p['emails'][2] if len(p['emails']) > 2 else None,
                email4=p['emails'][3] if len(p['emails']) > 3 else None,
                phone2=p['phones'][1] if len(p['phones']) > 1 else None,
                phone3=p['phones'][2] if len(p['phones']) > 2 else None,
                phone4=p['phones'][3] if len(p['phones']) > 3 else None,
                linkedin=None
            )
            
            metadata = {}
            if len(p['emails']) > 4: metadata['extra_emails'] = p['emails'][4:]
            if len(p['phones']) > 4: metadata['extra_phones'] = p['phones'][4:]
            if metadata:
                rec.metadata_json = json.dumps(metadata)

            db.add(rec)
            inserted_recruiters += 1

        job.status = "completed"
        job.processed_rows = inserted_recruiters
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        print(f"Successfully inserted {inserted_recruiters} recruiters into the database!")

    except Exception as e:
        db.rollback()
        print(f"Error during import: {e}")
        if 'job' in locals():
            job.status = "failed"
            job.error_log = str(e)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    excel_file = r"C:\Users\User\Desktop\final updated sheet.xlsx"
    run_import(excel_file)
