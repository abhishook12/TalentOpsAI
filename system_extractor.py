import os
import sqlite3
import pandas as pd
import glob
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DB_PATH = r"C:\TalentOpsAI\local_deep_extract.db"
QUOTA_LIMIT_MB = 700
QUOTA_LIMIT_BYTES = QUOTA_LIMIT_MB * 1024 * 1024

SEARCH_PATHS = [
    r"C:\Users\User\Desktop",
    r"C:\Users\User\Downloads",
    r"C:\Users\User\Documents",
    r"C:\TalentOpsAI"
]

EXCLUDED_FILES = [
    "final updated sheet.xlsx",
    "JUN 18 FOR DATABASW.xlsx"
]

EXCLUDED_DIRS = ["node_modules", ".venv", "venv", "site-packages", "AppData", "Temp"]

def check_db_size():
    if not os.path.exists(DB_PATH):
        return 0
    return os.path.getsize(DB_PATH)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            email TEXT PRIMARY KEY,
            name TEXT
        )
    """)
    conn.commit()
    return conn

def find_files():
    all_files = []
    for base_path in SEARCH_PATHS:
        for root, dirs, files in os.walk(base_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]
            
            for file in files:
                if file.endswith(('.csv', '.xlsx', '.xls')):
                    if any(file.lower() == ex.lower() for ex in EXCLUDED_FILES):
                        logging.info(f"Skipping excluded file: {file}")
                        continue
                        
                    full_path = os.path.join(root, file)
                    all_files.append(full_path)
    return all_files

def extract_data(file_path):
    try:
        if file_path.endswith('.csv'):
            # fast read for large csv
            df = pd.read_csv(file_path, low_memory=False, on_bad_lines='skip', encoding='utf-8', encoding_errors='ignore')
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
            
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        email_col = None
        for col in df.columns:
            if 'email' in col or 'e-mail' in col:
                email_col = col
                break
                
        name_col = None
        for col in df.columns:
            if 'name' in col and 'company' not in col:
                name_col = col
                break
                
        if not email_col:
            return pd.DataFrame()
            
        df_extracted = pd.DataFrame()
        df_extracted['email'] = df[email_col].astype(str).str.strip().str.lower()
        
        if name_col:
            df_extracted['name'] = df[name_col].astype(str).str.strip()
        else:
            df_extracted['name'] = 'Unknown'
            
        df_extracted = df_extracted.dropna(subset=['email'])
        df_extracted = df_extracted[df_extracted['email'] != 'nan']
        df_extracted = df_extracted[df_extracted['email'] != '']
        df_extracted = df_extracted.drop_duplicates(subset=['email'])
        return df_extracted
        
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

def run_extraction():
    logging.info(f"Starting System-Wide Deep Extraction. Hard Lock: {QUOTA_LIMIT_MB} MB")
    
    if os.path.exists(DB_PATH):
        logging.info("Wiping previous local deep extract DB...")
        os.remove(DB_PATH)
        
    conn = init_db()
    files_to_process = find_files()
    logging.info(f"Found {len(files_to_process)} data files across the system.")
    
    total_inserted = 0
    quota_reached = False
    
    for file_path in files_to_process:
        if quota_reached:
            break
            
        current_size = check_db_size()
        if current_size >= QUOTA_LIMIT_BYTES:
            logging.warning(f"EMERGENCY LOCK TRIGGERED! DB SIZE {current_size / 1024 / 1024:.2f} MB >= {QUOTA_LIMIT_MB} MB LIMIT.")
            break
            
        logging.info(f"Extracting from: {file_path}")
        df_new = extract_data(file_path)
        
        if df_new.empty:
            continue
            
        # Insert chunk by chunk to carefully monitor size
        chunk_size = 5000
        for i in range(0, len(df_new), chunk_size):
            chunk = df_new.iloc[i:i+chunk_size]
            
            try:
                # INSERT OR IGNORE to automatically deduplicate against DB
                records = chunk.to_dict('records')
                cursor = conn.cursor()
                cursor.executemany("INSERT OR IGNORE INTO recruiters (email, name) VALUES (:email, :name)", records)
                conn.commit()
                total_inserted += cursor.rowcount
                
                # Check quota after every chunk insertion
                current_size = check_db_size()
                if current_size >= QUOTA_LIMIT_BYTES:
                    logging.warning(f"HARD LOCK ACTIVATED MID-FILE! Quota {QUOTA_LIMIT_MB} MB hit. Halting insertion instantly.")
                    quota_reached = True
                    break
            except Exception as e:
                logging.error(f"DB Insertion error: {e}")
                
    final_size_mb = check_db_size() / 1024 / 1024
    logging.info("--- DEEP EXTRACTION COMPLETE ---")
    logging.info(f"Final Local DB Size: {final_size_mb:.2f} MB")
    
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
    logging.info(f"Total Unique Highly-Compressed Records Inserted: {count}")

if __name__ == "__main__":
    run_extraction()
