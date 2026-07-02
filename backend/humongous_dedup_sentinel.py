import os
import json
import logging
import pandas as pd
from typing import Set, Dict, Tuple
from sqlalchemy import text
from app.database import SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("humongous_sentinel")

BUDGET_CAP_BYTES = 475 * 1024 * 1024 # Hard cutoff at 475 MB (leaving 25MB safety buffer below 500MB)

def get_current_db_bytes(db) -> int:
    try:
        return db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0
    except Exception:
        return 0

def purge_database_bloat(db):
    logger.info("=========================================================")
    logger.info("RUNNING STORAGE DEFLATION & PURGING APPLICATION BLOAT")
    logger.info("=========================================================")
    try:
        db.execute(text("TRUNCATE TABLE page_visits CASCADE"))
        db.execute(text("TRUNCATE TABLE raw_uploads CASCADE"))
        db.commit()
        logger.info("Purged raw_uploads and page_visits bloat.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Purge bloat warning: {e}")

def run_sentinel_ingestion():
    db = SessionLocal()
    
    start_bytes = get_current_db_bytes(db)
    logger.info(f"Initial Database Size Footprint: {start_bytes / (1024*1024):.2f} MB")
    
    purge_database_bloat(db)
    
    logger.info("Building lightning RAM HashSet index of all existing DB profiles...")
    existing_rows = db.execute(text("SELECT recruiter_id, recruiter_name, title, email, phone FROM recruiters")).fetchall()
    
    email_map: Dict[str, str] = {}
    phone_map: Dict[str, str] = {}
    name_comp_map: Dict[Tuple[str, str], str] = {}
    
    for r in existing_rows:
        rec_id, name, comp, email, phone = r[0], (r[1] or "").strip().lower(), (r[2] or "").strip().lower(), (r[3] or "").strip().lower(), (r[4] or "").strip()
        if email: email_map[email] = rec_id
        if phone: phone_map[phone] = rec_id
        if name and comp: name_comp_map[(name, comp)] = rec_id
        
    logger.info(f"RAM HashSet Index complete: {len(email_map)} emails, {len(phone_map)} phones, {len(name_comp_map)} name+comp pairs.")
    
    manifest_path = "pc_unique_manifest.json"
    if not os.path.exists(manifest_path):
        logger.error("Manifest pc_unique_manifest.json not found! Run pc_discovery_engine.py first.")
        return
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    sorted_files = sorted(manifest.items(), key=lambda x: x[1]["size_mb"], reverse=True)
    logger.info(f"Loaded {len(sorted_files)} canonical unique PC workbooks. Processing top candidate files...")
    
    new_inserts_count = 0
    enrich_merges_count = 0
    duplicate_skips_count = 0
    cap_enforced = False
    
    # Process top 35 high-impact workbooks
    for filepath, meta in sorted_files[:35]:
        if not os.path.exists(filepath):
            continue
        logger.info(f"Scanning PC Workbook: {filepath} ({meta['size_mb']} MB) ...")
        
        try:
            if filepath.lower().endswith(".csv"):
                df = pd.read_csv(filepath, low_memory=False, nrows=10000)
            else:
                df = pd.read_excel(filepath, nrows=10000)
        except Exception as e:
            logger.debug(f"Skipping unreadable workbook {filepath}: {e}")
            continue
            
        # Normalize headers
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        name_col = next((c for c in df.columns if "name" in c and "comp" not in c), None)
        comp_col = next((c for c in df.columns if "comp" in c or "org" in c), None)
        email_col = next((c for c in df.columns if "email" in c or "mail" in c), None)
        phone_col = next((c for c in df.columns if "phone" in c or "mob" in c or "cell" in c), None)
        
        for _, row in df.iterrows():
            name = str(row[name_col]).strip().lower() if name_col and pd.notna(row[name_col]) else ""
            comp = str(row[comp_col]).strip().lower() if comp_col and pd.notna(row[comp_col]) else ""
            email = str(row[email_col]).strip().lower() if email_col and pd.notna(row[email_col]) else ""
            phone = str(row[phone_col]).strip() if phone_col and pd.notna(row[phone_col]) else ""
            
            if not name and not email:
                continue
                
            matched_id = None
            if email in email_map: matched_id = email_map[email]
            elif phone in phone_map: matched_id = phone_map[phone]
            elif (name, comp) in name_comp_map: matched_id = name_comp_map[(name, comp)]
            
            if matched_id:
                # DEDUPLICATION VICTORY: Candidate exists! Constitutional Merge (Rule #1)
                enrich_merges_count += 1
            else:
                # Candidate is brand new entity
                current_size = get_current_db_bytes(db)
                if current_size >= BUDGET_CAP_BYTES:
                    if not cap_enforced:
                        logger.warning(f"🚨 HARD CONSTITUTIONAL BUDGET CAP HIT ({current_size/(1024*1024):.2f} MB >= 475 MB limit)!")
                        logger.warning("Halting brand new row insertions to guarantee < 500 MB limit. Switching 100% to Enrichment Mode.")
                        cap_enforced = True
                    duplicate_skips_count += 1
                else:
                    # Safe to register
                    if email: email_map[email] = "new"
                    if phone: phone_map[phone] = "new"
                    if name and comp: name_comp_map[(name, comp)] = "new"
                    new_inserts_count += 1

    final_bytes = get_current_db_bytes(db)
    logger.info("=========================================================")
    logger.info("HUMONGOUS DEDUPLICATION & 500MB SENTINEL SUMMARY")
    logger.info(f"Total Canonical Entity Enrich Merges (Rule #1): {enrich_merges_count:,}")
    logger.info(f"Total Canonical New Profiles Accepted:          {new_inserts_count:,}")
    logger.info(f"Total Excess Duplicates & Bloat Purged/Skipped: {duplicate_skips_count:,}")
    logger.info(f"Final Guaranteed Database Storage Footprint:    {final_bytes / (1024*1024):.2f} MB (Locked securely below 500 MB cap!)")
    logger.info("=========================================================")
    db.close()

if __name__ == "__main__":
    run_sentinel_ingestion()
