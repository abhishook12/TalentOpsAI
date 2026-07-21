import os
import json
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 1. Setup Database
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# 2. Local Storage Fallback
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "../../storage/raw_data")
os.makedirs(STORAGE_DIR, exist_ok=True)

# 3. Read Source Files
def scan_files():
    found_files = []
    desktop_file = "C:\\Users\\User\\Desktop\\final updated sheet.xlsx"
    if os.path.exists(desktop_file): found_files.append(desktop_file)
    
    upload_dir = "C:\\TalentOpsAI\\backend\\uploads"
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f.endswith('.xlsx') or f.endswith('.csv'):
                found_files.append(os.path.join(upload_dir, f))
    return found_files

def extract_raw_data(files):
    raw_data = []
    print(f"Extracting data from {len(files)} files...")
    for f in files:
        print(f"Reading {os.path.basename(f)}...")
        try:
            if f.endswith('.xlsx'):
                xl = pd.ExcelFile(f)
                for sheet in xl.sheet_names:
                    df = xl.parse(sheet, dtype=str)
                    df['source_file'] = os.path.basename(f)
                    df['source_sheet'] = sheet
                    raw_data.append(df)
            elif f.endswith('.csv'):
                df = pd.read_csv(f, dtype=str, low_memory=False)
                df['source_file'] = os.path.basename(f)
                df['source_sheet'] = 'CSV'
                raw_data.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not raw_data:
        return pd.DataFrame()
        
    combined = pd.concat(raw_data, ignore_index=True)
    return combined

def main():
    files = scan_files()
    if not files:
        print("No source files found!")
        return
        
    df = extract_raw_data(files)
    print(f"Extracted {len(df)} total rows.")
    
    # Fill NA to prevent JSON serialization issues
    df = df.fillna("")
    
    # Get all recruiters to map email -> recruiter_id
    print("Loading recruiters from database to match...")
    with SessionLocal() as db:
        recruiters = db.execute(text("SELECT recruiter_id, email FROM recruiters")).fetchall()
        email_to_id = {r[1].lower().strip(): r[0] for r in recruiters if r[1]}
    
    print(f"Loaded {len(email_to_id)} recruiters from DB.")
    
    # Process dataframe
    matched_count = 0
    updated_count = 0
    
    # Batch updates
    batch = []
    
    # Find email column in dataframe (case insensitive search)
    email_col = None
    for col in df.columns:
        if 'email' in str(col).lower():
            email_col = col
            break
            
    if not email_col:
        print("Could not find an email column in the source files!")
        return
        
    print(f"Using column '{email_col}' as email key.")
    
    # Iterate through rows
    records = df.to_dict('records')
    
    for i, row in enumerate(records):
        email = str(row.get(email_col, "")).lower().strip()
        if not email or email not in email_to_id:
            continue
            
        matched_count += 1
        rec_id = email_to_id[email]
        
        # Save JSON to disk (Simulating Storage Upload)
        file_name = f"recruiter_{rec_id}_raw.json"
        file_path = os.path.join(STORAGE_DIR, file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(row, f)
            
        storage_url = f"storage://talentops-raw-data/{file_name}"
        batch.append({"rec_id": rec_id, "url": storage_url})
        
        # Flush batch
        if len(batch) >= 1000 or i == len(records) - 1:
            with SessionLocal() as db:
                for b in batch:
                    db.execute(
                        text("UPDATE recruiters SET raw_data = :url WHERE recruiter_id = :id"),
                        {"url": b["url"], "id": b["rec_id"]}
                    )
                db.commit()
            updated_count += len(batch)
            batch = []
            print(f"Updated {updated_count} recruiters...")
            
    print(f"Finished! Recovered {matched_count} raw data records into storage.")

if __name__ == "__main__":
    main()
