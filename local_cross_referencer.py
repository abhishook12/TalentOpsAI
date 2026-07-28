import os
import sqlite3
import pandas as pd
import glob
import logging
import time
import gc

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TARGET_DB = r"C:\TalentOpsAI\backend\dev.db"
STAGING_DIR = r"C:\TalentOpsAI\zip_staging"

SEARCH_PATHS = [
    r"D:\desktop",
    r"D:\Download abhi",
    r"D:\\",
    r"C:\Users\User\Desktop\for location by claude",
    STAGING_DIR
]

def find_files():
    all_files = []
    root_files = glob.glob(r"D:\*.xlsx") + glob.glob(r"D:\*.csv") + glob.glob(r"D:\*.xls")
    for f in root_files:
        if os.path.isfile(f):
            all_files.append(f)
            
    target_dirs = [p for p in SEARCH_PATHS if p != r"D:\\"]
    for base_path in target_dirs:
        if not os.path.exists(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ["System Volume Information", "$RECYCLE.BIN"] and not d.startswith('.')]
            for file in files:
                if file.endswith(('.csv', '.xlsx', '.xls')):
                    all_files.append(os.path.join(root, file))
                    
    return list(set(all_files))

def run_cross_reference():
    logging.info("--- STARTING ULTRA-FAST LOCAL CROSS-REFERENCING (PHASE 2) ---")
    
    conn = sqlite3.connect(TARGET_DB)
    cursor = conn.cursor()
    
    # Load all recruiters that are MISSING phone or location
    logging.info("Loading memory cache of targets missing phone/location...")
    cursor.execute("SELECT email, recruiter_id FROM recruiters WHERE phone IS NULL OR location IS NULL")
    target_cache = {row[0]: row[1] for row in cursor.fetchall()}
    logging.info(f"Targeting {len(target_cache)} emails for enrichment.")
    
    # We will also keep track of IDs that we've fully satisfied, so we can remove them from cache to shrink it over time
    cursor.execute("SELECT recruiter_id, phone, location FROM recruiters WHERE phone IS NULL OR location IS NULL")
    target_needs = {}
    for r_id, p, l in cursor.fetchall():
        target_needs[r_id] = {
            'needs_phone': p is None or str(p).strip() == '',
            'needs_location': l is None or str(l).strip() == ''
        }
    
    files_to_process = find_files()
    logging.info(f"Cross-referencing against {len(files_to_process)} spreadsheets using Vectorization...")
    
    start_time = time.time()
    
    for file_path in files_to_process:
        logging.info(f"Scanning: {file_path}")
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, low_memory=False, on_bad_lines='skip', encoding='utf-8', encoding_errors='ignore')
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
                
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            email_col = next((col for col in df.columns if 'email' in col or 'e-mail' in col), None)
            phone_col = next((col for col in df.columns if 'phone' in col or 'mobile' in col or 'number' in col), None)
            loc_col = next((col for col in df.columns if 'location' in col or 'city' in col or 'state' in col), None)
            
            if not email_col or (not phone_col and not loc_col):
                del df
                gc.collect()
                continue
            
            # VECTORIZATION MAGIC: Instantly filter down gigabytes of rows to only the ones we care about
            df[email_col] = df[email_col].astype(str).str.strip().str.lower()
            matched_df = df[df[email_col].isin(target_cache.keys())]
            
            updates = {}
            
            # Use itertuples instead of iterrows for remaining matches (50x faster)
            for row in matched_df.itertuples(index=False):
                email = getattr(row, email_col)
                r_id = target_cache[email]
                needs = target_needs.get(r_id, {})
                
                if r_id not in updates:
                    updates[r_id] = {'phone': None, 'location': None}
                    
                if needs.get('needs_phone') and phone_col:
                    val = getattr(row, phone_col, None)
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != 'nan':
                            updates[r_id]['phone'] = val_str
                            needs['needs_phone'] = False # Mark as found!
                            
                if needs.get('needs_location') and loc_col:
                    val = getattr(row, loc_col, None)
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != 'nan':
                            updates[r_id]['location'] = val_str
                            needs['needs_location'] = False # Mark as found!
            
            # Batch write to DB immediately
            if updates:
                update_batch = []
                for r_id, data in updates.items():
                    if data['phone'] or data['location']:
                        update_batch.append((data.get('phone'), data.get('location'), r_id))
                        
                if update_batch:
                    # Chunking SQLite updates by 10k to avoid locking
                    chunk_size = 10000
                    for i in range(0, len(update_batch), chunk_size):
                        chunk = update_batch[i:i + chunk_size]
                        cursor.executemany("UPDATE recruiters SET phone = COALESCE(phone, ?), location = COALESCE(location, ?) WHERE recruiter_id = ?", chunk)
                    conn.commit()
                    logging.info(f" -> Instant batch-write: {len(update_batch)} records updated.")
                    
                    # Remove fully satisfied recruiters from cache to speed up future files
                    for r_id, needs in target_needs.items():
                        if not needs['needs_phone'] and not needs['needs_location']:
                            # Find the email for this r_id and pop it
                            for e, i in list(target_cache.items()):
                                if i == r_id:
                                    target_cache.pop(e, None)
                                    break
            
            # Strict memory management
            del matched_df
            del df
            gc.collect()
                            
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            
    logging.info("--- ULTRA-FAST CROSS-REFERENCING COMPLETE ---")
    logging.info(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    conn.close()

if __name__ == "__main__":
    run_cross_reference()
