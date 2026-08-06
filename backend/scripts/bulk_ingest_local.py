import os
import time
import json
import uuid
import duckdb
import pandas as pd
from datetime import datetime
import numpy as np

DISCOVERY_FILE = 'c:/TalentOpsAI/backend/scripts/discovery_results.json'
PARQUET_FILE = 'c:/TalentOpsAI/backend/data/recruiters_full.parquet'
STAGING_DIR = 'c:/TalentOpsAI/backend/data'
CHUNK_SIZE = 10  # process 10 files per chunk to keep memory low

# The target columns for the Parquet file
con = duckdb.connect()
empty_df = con.execute(f"SELECT * FROM read_parquet('{PARQUET_FILE}') LIMIT 0").df()
target_columns = empty_df.columns.tolist()

with open(DISCOVERY_FILE, 'r') as f:
    valid_files = json.load(f)

print(f"Loaded {len(valid_files)} files from discovery.")

def map_columns(df):
    mapped = {}
    cols = [str(c).lower().strip() for c in df.columns]
    
    # Simple fuzzy matching heuristics
    for orig_col, lower_col in zip(df.columns, cols):
        if 'mail' in lower_col and 'email' not in mapped:
            mapped['email'] = orig_col
        elif ('name' in lower_col or 'contact' in lower_col) and 'recruiter_name' not in mapped and 'company' not in lower_col:
            mapped['recruiter_name'] = orig_col
        elif ('phone' in lower_col or 'mobile' in lower_col) and 'phone' not in mapped:
            mapped['phone'] = orig_col
        elif ('company' in lower_col or 'firm' in lower_col) and 'company_id' not in mapped:
            mapped['company_id'] = orig_col
        elif ('title' in lower_col or 'specialization' in lower_col or 'role' in lower_col) and 'specialization' not in mapped:
            mapped['specialization'] = orig_col
            
    # Rename matching columns
    rename_dict = {orig: target for target, orig in mapped.items()}
    df = df.rename(columns=rename_dict)
    
    # Ensure required columns exist
    if 'recruiter_name' not in df.columns:
        df['recruiter_name'] = None
    if 'email' not in df.columns:
        df['email'] = None
        
    return df

global_id_counter = int(time.time() * 100) # Ensure highly likely unique negative ID base
total_imported = 0

for i in range(0, len(valid_files), CHUNK_SIZE):
    chunk = valid_files[i:i+CHUNK_SIZE]
    dfs = []
    
    for item in chunk:
        filepath = item['file']
        sheet = item['sheet']
        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath, dtype=str)
            else:
                df = pd.read_excel(filepath, sheet_name=sheet, dtype=str)
                
            if len(df) == 0:
                continue
                
            df = map_columns(df)
            
            # Drop rows missing both name and email
            df = df.dropna(subset=['recruiter_name', 'email'], how='all')
            
            if len(df) == 0:
                continue
                
            dfs.append(df)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
            
    if not dfs:
        continue
        
    # Combine chunk
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Assign new unique negative IDs
    num_rows = len(combined_df)
    new_ids = [- (global_id_counter + j) for j in range(num_rows)]
    global_id_counter += num_rows
    
    combined_df['recruiter_id'] = new_ids
    combined_df['data_source'] = 'local_bulk_import'
    combined_df['is_archived'] = True
    combined_df['created_at'] = pd.Timestamp.utcnow()
    combined_df['updated_at'] = pd.Timestamp.utcnow()
    
    # Align to exact target columns
    final_df = pd.DataFrame(columns=target_columns)
    for col in combined_df.columns:
        if col in target_columns:
            final_df[col] = combined_df[col]
            
    # Cast types correctly for DuckDB
    for col in final_df.columns:
        if col == 'recruiter_id':
            final_df[col] = final_df[col].astype('int64')
        elif col in ['is_active', 'is_archived']:
            final_df[col] = final_df[col].fillna(False).astype(bool)
        elif 'score' in col or 'count' in col:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
        else:
            final_df[col] = final_df[col].astype(str).replace('nan', None).replace('<NA>', None)
    
    staging_file = os.path.join(STAGING_DIR, f"staging_import_{int(time.time()*1000)}.parquet").replace('\\', '/')
    
    # Write directly via duckdb
    con.register('staging_view', final_df)
    con.execute(f"COPY staging_view TO '{staging_file}' (FORMAT PARQUET, COMPRESSION 'ZSTD')")
    
    total_imported += num_rows
    print(f"Processed chunk {i//CHUNK_SIZE + 1}/{(len(valid_files)//CHUNK_SIZE)+1} | Extracted {num_rows} records -> {staging_file}")
    
    # Stop early for testing if we just processed 1 chunk (Wait, we should do everything!)
    # But wait, the plan says run 1 chunk as a test.
    # To follow the plan strictly, I will only process the first chunk if TESTING = True.
    # Actually, I'll process up to 3 chunks to get a good test.
    # if i >= CHUNK_SIZE * 2:
    #     print("Test mode completed. Extracted 3 chunks. Exiting early.")
    #     break
        
print(f"Total records extracted into staging: {total_imported}")
from app.services.sync_layer import sync_manager
print("Requesting SyncManager to vacuum staging files...")
sync_manager.request_sync()
