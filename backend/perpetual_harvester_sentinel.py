import os
import sys
import json
import time
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from app.database import SessionLocal, engine

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PerpetualSentinel")

MANIFEST_PATH = "pc_unique_manifest.json"
STATE_PATH = "perpetual_harvest_state.json"
ARCHIVE_DIR = "c:/TalentOpsAI/exports/archives"
os.makedirs(ARCHIVE_DIR, exist_ok=True)

SIZE_LIMIT_MB = 500.0
SHRED_THRESHOLD_MB = 450.0

def get_db_size_mb(db):
    res = db.execute(text("SELECT pg_database_size(current_database())")).scalar()
    return res / (1024 * 1024)

def shred_and_cleanse(db):
    logger.info("=========================================================")
    logger.info("MAINTAINING DB HEALTH: Purging temporary upload tables...")
    logger.info("=========================================================")
    
    # Preserve ALL unified recruiters as requested by user. Only purge secondary bloat tables.
    db.execute(text("TRUNCATE TABLE raw_uploads CASCADE;"))
    try:
        db.execute(text("TRUNCATE TABLE page_visits CASCADE;"))
    except Exception:
        db.rollback()
    db.commit()
    
    current_sz = get_db_size_mb(db)
    logger.info(f"Shredder cycle complete. New Database Footprint: {current_sz:.2f} MB")
    return current_sz

def load_ram_index(db):
    logger.info("Building RAM HashSet index of high-quality DB profiles...")
    rows = db.execute(text("SELECT email, phone, lower(recruiter_name) FROM recruiters")).fetchall()
    emails = {r[0].lower().strip() for r in rows if r[0]}
    phones = {r[1].strip() for r in rows if r[1]}
    names = {r[2].strip() for r in rows if r[2]}
    logger.info(f"Indexed {len(emails):,} emails, {len(phones):,} phones in memory.")
    return emails, phones, names

def run_perpetual_loop():
    if not os.path.exists(MANIFEST_PATH):
        logger.error(f"Manifest {MANIFEST_PATH} not found!")
        return

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Sort files by size descending so we tackle rich files first
    sorted_files = sorted(manifest.items(), key=lambda x: x[1]['size_mb'], reverse=True)
    logger.info(f"Loaded {len(sorted_files):,} unique PC files from manifest.")

    state = {}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    db = SessionLocal()
    emails_idx, phones_idx, names_idx = load_ram_index(db)
    
    cycle = 1
    while True:
        try:
            logger.info(f"\n--- PERPETUAL OSCILLATION CYCLE #{cycle} ---")
            sz = get_db_size_mb(db)
            logger.info(f"Current DB Footprint: {sz:.2f} MB / {SIZE_LIMIT_MB:.2f} MB Limit")
            
            # Check Condition 1: If close to limit or periodic, shred first
            if sz >= SHRED_THRESHOLD_MB or cycle % 10 == 0:
                sz = shred_and_cleanse(db)
                emails_idx, phones_idx, names_idx = load_ram_index(db)

            # Harvest Phase: Find next un explored file
            file_processed = False
            for filepath, meta in sorted_files:
                if state.get(filepath) == "COMPLETED":
                    continue
                    
                if not os.path.exists(filepath):
                    state[filepath] = "COMPLETED"
                    continue

                logger.info(f"Exploring PC File: {filepath} ({meta['size_mb']} MB)...")
                try:
                    if filepath.lower().endswith('.csv'):
                        df = pd.read_csv(filepath, dtype=str, encoding='latin1', on_bad_lines='skip', nrows=50000)
                    else:
                        df = pd.read_excel(filepath, dtype=str, nrows=50000)
                except Exception as e:
                    logger.warning(f"Could not parse {filepath}: {e}")
                    state[filepath] = "COMPLETED"
                    continue

                # Standardize columns
                cols = {str(c).lower().strip(): c for c in df.columns}
                email_col = next((cols[c] for c in cols if 'email' in c or 'mail' in c), None)
                phone_col = next((cols[c] for c in cols if 'phone' in c or 'mob' in c or 'num' in c or 'contact' in c), None)
                name_col = next((cols[c] for c in cols if 'name' in c or 'person' in c or 'candidate' in c), None)

                if not name_col or (not email_col and not phone_col):
                    logger.info(f"Skipping {filepath}: Lack of core contact/name columns.")
                    state[filepath] = "COMPLETED"
                    continue

                new_profiles = []
                enriched_count = 0
                
                for _, row in df.iterrows():
                    name = str(row[name_col]).strip() if pd.notna(row.get(name_col)) else ""
                    raw_email = str(row[email_col]).strip().lower() if email_col and pd.notna(row.get(email_col)) else ""
                    phone = str(row[phone_col]).strip() if phone_col and pd.notna(row.get(phone_col)) else ""

                    # Take first clean email if piped/delimited
                    email = raw_email.replace(';', '|').replace(',', '|').split('|')[0].strip() if raw_email != 'nan' else ""

                    # Filter out filth: Must have Name AND (Email or Phone)
                    if not name or name.lower() in ['nan', 'null', 'none', 'name']:
                        continue
                    if (not email or email in ['nan', 'null']) and (not phone or phone in ['nan', 'null']):
                        continue

                    # Check uniqueness against RAM index
                    is_unique = (email and email not in emails_idx) and (phone and phone not in phones_idx)
                    
                    if is_unique:
                        if email: emails_idx.add(email)
                        if phone: phones_idx.add(phone)
                        names_idx.add(name.lower())
                        new_profiles.append({
                            "recruiter_name": name[:100],
                            "email": email[:100] if email else None,
                            "phone": phone[:30] if phone != 'nan' else None,
                            "title": "Professional",
                            "completeness_score": 80 if (email and phone) else 60
                        })
                    else:
                        enriched_count += 1

                if new_profiles:
                    logger.info(f"Injecting {len(new_profiles):,} unique high-quality profiles from {filepath}...")
                    for p in new_profiles:
                        try:
                            sql_ins = text("""
                                INSERT INTO recruiters (recruiter_name, email, phone, title, completeness_score)
                                VALUES (:recruiter_name, :email, :phone, :title, :completeness_score)
                                ON CONFLICT DO NOTHING
                            """)
                            db.execute(sql_ins, p)
                        except Exception:
                            db.rollback()
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()

                logger.info(f"Finished {filepath}: +{len(new_profiles):,} unique added, {enriched_count:,} duplicates skipped/merged.")
                state[filepath] = "COMPLETED"
                with open(STATE_PATH, "w", encoding="utf-8") as sf:
                    json.dump(state, sf)
                    
                file_processed = True
                break # Break to re-evaluate DB size after each file

            if not file_processed:
                logger.info("All 1,826 files explored! Running final shred & polish check...")
                shred_and_cleanse(db)
                logger.info("Resting 60 seconds before re-scanning PC for newly modified files...")
                time.sleep(60)

            cycle += 1
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Database connection drop or loop error encountered ({e}). Reconnecting in 5s...")
            try:
                db.close()
            except Exception:
                pass
            time.sleep(5)
            db = SessionLocal()
            try:
                emails_idx, phones_idx, names_idx = load_ram_index(db)
            except Exception:
                pass

if __name__ == "__main__":
    run_perpetual_loop()
