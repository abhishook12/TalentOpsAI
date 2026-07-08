import os
import sys
import logging
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Recruiter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

SEARCH_DIRS = [
    r'C:\Users\User\Downloads',
    r'C:\Users\User\Desktop',
    r'C:\Users\User\Documents',
    r'C:\TalentOpsAI\exports'
]

def clean_phone(p):
    if not p or pd.isna(p): return None
    s = str(p).strip()
    if s.lower() in ['none', 'nan', 'null', '', 'n/a']: return None
    # Keep digits, +, -, (, )
    cleaned = ''.join(c for c in s if c.isdigit() or c in '+-() x.')
    if len(cleaned) >= 7: return cleaned[:30]
    return None

def clean_title(t):
    if not t or pd.isna(t): return None
    s = str(t).strip()
    if s.lower() in ['none', 'nan', 'null', '', 'n/a', 'recruiter']: return None
    if len(s) > 2: return s[:150]
    return None

def deep_enrichment_harvester():
    db = SessionLocal()
    logger.info("Starting Deep Phone & Title Harvester across local system datasets...")
    
    # Load map of email -> recruiter_id for fast lookup where phone is None or title is generic
    logger.info("Loading recruiters needing phone or title enrichment into memory...")
    recs_need_info = db.query(Recruiter.recruiter_id, Recruiter.email, Recruiter.phone, Recruiter.title).all()
    
    email_map = {}
    for r_id, email, phone, title in recs_need_info:
        if email:
            email_map[email.lower().strip()] = (r_id, phone, title)
            
    logger.info(f"Loaded {len(email_map)} unique recruiter emails for enrichment matching.")
    
    total_phones_harvested = 0
    total_titles_harvested = 0
    
    for folder in SEARCH_DIRS:
        if not os.path.exists(folder): continue
        for root, dirs, files in os.walk(folder):
            if any(x in root for x in ['node_modules', 'venv', '.git', '__pycache__']): continue
            for file in files:
                if not file.endswith(('.csv', '.xlsx')) or file.startswith('.'): continue
                filepath = os.path.join(root, file)
                try:
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    if size_mb > 40 or size_mb < 0.05: continue
                    
                    if file.endswith('.csv'):
                        df = pd.read_csv(filepath, low_memory=False, on_bad_lines='skip')
                    else:
                        df = pd.read_excel(filepath)
                        
                    email_col = next((c for c in df.columns if 'email' in str(c).lower()), None)
                    if not email_col: continue
                    
                    phone_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['phone', 'mobile', 'cell', 'contact_num'])), None)
                    title_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['title', 'role', 'designation', 'position'])), None)
                    
                    if not phone_col and not title_col: continue
                    
                    batch_updates = 0
                    for _, row in df.iterrows():
                        raw_email = str(row[email_col]).strip().lower()
                        if not raw_email or raw_email not in email_map: continue
                        
                        r_id, existing_phone, existing_title = email_map[raw_email]
                        
                        new_phone = clean_phone(row[phone_col]) if phone_col else None
                        new_title = clean_title(row[title_col]) if title_col else None
                        
                        updated = False
                        rec = None
                        if new_phone and not existing_phone:
                            rec = db.query(Recruiter).filter(Recruiter.recruiter_id == r_id).first()
                            if rec and not rec.phone:
                                rec.phone = new_phone
                                rec.repair_reason = (rec.repair_reason or "") + "; harvested_phone"
                                total_phones_harvested += 1
                                updated = True
                                email_map[raw_email] = (r_id, new_phone, existing_title)
                                
                        if new_title and (not existing_title or existing_title.lower() == 'recruiter'):
                            if not rec: rec = db.query(Recruiter).filter(Recruiter.recruiter_id == r_id).first()
                            if rec:
                                rec.title = new_title
                                rec.repair_reason = (rec.repair_reason or "") + "; harvested_title"
                                total_titles_harvested += 1
                                updated = True
                                email_map[raw_email] = (r_id, existing_phone or new_phone, new_title)
                                
                        if updated:
                            batch_updates += 1
                            if batch_updates % 200 == 0:
                                db.commit()
                    db.commit()
                except Exception as e:
                    db.rollback()
                    
    logger.info(f"=== HARVEST COMPLETE ===")
    logger.info(f"  Total Phone Numbers Harvested & Restored: {total_phones_harvested}")
    logger.info(f"  Total Job Titles Harvested & Restored: {total_titles_harvested}")

if __name__ == "__main__":
    deep_enrichment_harvester()
