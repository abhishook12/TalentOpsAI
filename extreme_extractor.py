import os
import sqlite3
import pandas as pd
import glob
import zipfile
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TARGET_DB = r"C:\TalentOpsAI\backend\dev.db"
ZIP_DIR = r"C:\Users\User\Downloads"
STAGING_DIR = r"C:\TalentOpsAI\zip_staging"

SEARCH_PATHS = [
    r"D:\desktop",
    r"D:\Download abhi",
    r"D:\\", # specifically scan root files
    r"C:\Users\User\Desktop\for location by claude",
    STAGING_DIR
]

def extract_zips():
    logging.info(f"Scanning for ZIP archives in {ZIP_DIR}...")
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
        
    zip_files = glob.glob(os.path.join(ZIP_DIR, "*.zip"))
    logging.info(f"Found {len(zip_files)} zip archives.")
    
    for zf in zip_files:
        logging.info(f"Unzipping: {os.path.basename(zf)}")
        try:
            with zipfile.ZipFile(zf, 'r') as zip_ref:
                zip_ref.extractall(STAGING_DIR)
        except Exception as e:
            logging.error(f"Failed to unzip {zf}: {e}")

def find_files():
    all_files = []
    
    # Add explicit D root files first without walking the entire huge D drive
    root_files = glob.glob(r"D:\*.xlsx") + glob.glob(r"D:\*.csv") + glob.glob(r"D:\*.xls")
    for f in root_files:
        if os.path.isfile(f):
            all_files.append(f)
            
    # Walk the specific target directories
    target_dirs = [p for p in SEARCH_PATHS if p != r"D:\\"]
    
    for base_path in target_dirs:
        if not os.path.exists(base_path):
            logging.warning(f"Path does not exist, skipping: {base_path}")
            continue
            
        for root, dirs, files in os.walk(base_path):
            # Exclude massive pst files and system dirs
            dirs[:] = [d for d in dirs if d not in ["System Volume Information", "$RECYCLE.BIN"] and not d.startswith('.')]
            
            for file in files:
                if file.endswith(('.csv', '.xlsx', '.xls')):
                    full_path = os.path.join(root, file)
                    all_files.append(full_path)
                    
    return list(set(all_files)) # remove duplicates

def extract_data(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, low_memory=False, on_bad_lines='skip', encoding='utf-8', encoding_errors='ignore')
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        email_col = next((col for col in df.columns if 'email' in col or 'e-mail' in col), None)
        name_col = next((col for col in df.columns if 'name' in col and 'company' not in col), None)
                
        if not email_col:
            return pd.DataFrame()
            
        df_extracted = pd.DataFrame()
        df_extracted['email'] = df[email_col].astype(str).str.strip().str.lower()
        df_extracted['name'] = df[name_col].astype(str).str.strip() if name_col else 'Unknown'
            
        df_extracted = df_extracted.dropna(subset=['email'])
        df_extracted = df_extracted[df_extracted['email'] != 'nan']
        df_extracted = df_extracted[df_extracted['email'] != '']
        df_extracted = df_extracted.drop_duplicates(subset=['email'])
        
        return df_extracted
        
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

def run_extreme_extraction():
    logging.info("--- STARTING EXTREME DEEP DIVE (RESUME MODE) ---")
    
    # 1. Extract ZIPs (Skip if already unzipped)
    # extract_zips() # We already did this yesterday
    
    # Parse yesterday's log to skip already processed files
    log_path = r"C:\Users\User\.gemini\antigravity\brain\8ca93279-e790-4ae4-b3a8-41b138956926\.system_generated\tasks\task-4741.log"
    scraped_files = set()
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "INFO: Scraping: " in line:
                    fname = line.split("INFO: Scraping: ")[1].strip()
                    scraped_files.add(fname)
    
    # We stopped ON this file, so we MUST process it again to ensure it finishes
    resume_file = r"D:\whole master Data(AutoRecovered).xlsx"
    if resume_file in scraped_files:
        scraped_files.remove(resume_file)
        
    logging.info(f"Loaded {len(scraped_files)} previously completed files to skip.")
    
    # 2. Find Targets
    all_files = find_files()
    files_to_process = [f for f in all_files if f not in scraped_files]
    logging.info(f"Found {len(files_to_process)} REMAINING spreadsheets to process.")
    
    # ZIP extraction and Target finding already handled above
    logging.info(f"Found {len(files_to_process)} spreadsheets in the extreme target zones.")
    
    # 3. Connect to local dev.db
    conn = sqlite3.connect(TARGET_DB)
    cursor = conn.cursor()
    
    logging.info("Fetching existing emails to ensure no egress duplication...")
    cursor.execute("SELECT email FROM recruiters WHERE email IS NOT NULL")
    existing_emails = {row[0].strip().lower() for row in cursor.fetchall()}
    logging.info(f"Local dev.db currently has {len(existing_emails)} unique emails.")
    
    total_inserted = 0
    start_time = time.time()
    
    for file_path in files_to_process:
        logging.info(f"Scraping: {file_path}")
        df_new = extract_data(file_path)
        
        if df_new.empty:
            continue
            
        insert_batch = []
        for _, row in df_new.iterrows():
            email = str(row['email'])
            name = str(row['name'])
            
            if email not in existing_emails:
                existing_emails.add(email)
                insert_batch.append((
                    name, 
                    email, 
                    'extreme_deep_dive',
                    1, # is_active
                    0, # needs_review
                    100 # trust_score
                ))
                
        if insert_batch:
            try:
                # bulk insert in chunks
                chunk_size = 5000
                for i in range(0, len(insert_batch), chunk_size):
                    chunk = insert_batch[i:i+chunk_size]
                    cursor.executemany("""
                        INSERT OR IGNORE INTO recruiters 
                        (recruiter_name, email, data_source, is_active, needs_review, trust_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, chunk)
                
                conn.commit()
                total_inserted += len(insert_batch)
                logging.info(f"-> Injected {len(insert_batch)} fresh records into local DB.")
            except Exception as e:
                logging.error(f"DB Insertion error: {e}")

    logging.info("--- EXTREME DEEP DIVE COMPLETE ---")
    logging.info(f"Successfully harvested {total_inserted} brand new unique records.")
    logging.info(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    cursor.execute("SELECT COUNT(*) FROM recruiters")
    final_count = cursor.fetchone()[0]
    logging.info(f"Total Local App UI Records Available: {final_count}")
    
    conn.close()

if __name__ == "__main__":
    run_extreme_extraction()
