import os
import glob
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import time

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env.local'))
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

raw_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///./dev.db"
if raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(raw_url)

TABLE_SCHEMAS = {
    'recruiters': ['recruiter_name', 'email', 'phone', 'linkedin', 'specialization', 'company_id', 'is_active'],
    'companies': ['company_name', 'industry', 'location', 'website']
}

def clean_df(df, table_name):
    df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
    
    column_mapping = {
        'name': 'recruiter_name' if table_name == 'recruiters' else 'company_name',
        'recruiter': 'recruiter_name',
        'company': 'company_name',
        'contact': 'phone',
        'email(s)': 'email',
        'phone(s)': 'phone',
        'title': 'specialization'
    }
    df = df.rename(columns=column_mapping)
    
    valid_cols = [c for c in df.columns if c in TABLE_SCHEMAS[table_name]]
    
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        db_cols = [c['name'] for c in inspector.get_columns(table_name)]
        valid_cols = [c for c in valid_cols if c in db_cols]
        
    if not valid_cols:
        return None
        
    df = df[valid_cols]
    
    primary_col = 'email' if table_name == 'recruiters' else 'company_name'
    if primary_col in df.columns:
        df = df.dropna(subset=[primary_col])
        
    return df

def write_status(inserted_so_far, current_file):
    with open('ingestion_status.txt', 'w') as f:
        f.write(f"ROWS_INSERTED: {inserted_so_far}\nCURRENT_FILE: {current_file}\n")

def process_massive_files():
    print("Starting process_massive_files()...")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    
    # Target exactly the massive datasets we skipped previously
    files = [
        os.path.join(base_dir, 'backend', 'exports', 'production_seed_recruiters.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'perpetual_shred_1782549077.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'perpetual_shred_1782549112.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530576.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530678.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530744.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530793.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530814.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530837.csv'),
        os.path.join(base_dir, 'exports', 'archives', 'shredded_archive_1782530885.csv')
    ]

    total_inserted = 0
    print(f"Connecting to: {raw_url.split('@')[-1]}")
    
    write_status(total_inserted, "Initializing")
    
    # 1. Process local_deep_extract.db explicitly in chunks
    print("Processing local_deep_extract.db into recruiters...")
    write_status(total_inserted, "local_deep_extract.db")
    try:
        source_engine = create_engine('sqlite:///' + os.path.join(base_dir, 'local_deep_extract.db'))
        for chunk in pd.read_sql('SELECT email, name as recruiter_name FROM recruiters', source_engine, chunksize=10000):
            clean_data = clean_df(chunk, 'recruiters')
            if clean_data is not None and not clean_data.empty:
                clean_data.to_sql('recruiters', engine, if_exists='append', index=False, method='multi')
                total_inserted += len(clean_data)
                write_status(total_inserted, "local_deep_extract.db")
                print(f" -> DB Chunk Inserted. Total so far: {total_inserted}")
    except Exception as e:
        print(f" -> Error processing local_deep_extract.db: {e}")

    # 2. Process all massive CSV files in chunks
    for f in files:
        if not os.path.exists(f):
            continue
            
        filename = os.path.basename(f).lower()
        table_name = 'recruiters'
        print(f"Processing {filename} into {table_name}...")
        
        try:
            for chunk in pd.read_csv(f, chunksize=10000):
                clean_data = clean_df(chunk, table_name)
                if clean_data is not None and not clean_data.empty:
                    clean_data.to_sql(table_name, engine, if_exists='append', index=False, method='multi')
                    total_inserted += len(clean_data)
                    write_status(total_inserted, filename)
                    print(f" -> CSV Chunk Inserted. Total so far: {total_inserted}")
        except Exception as e:
            print(f" -> Error processing {filename}: {e}")

    write_status(total_inserted, "COMPLETE")
    print(f"Finished! Total rows safely inserted: {total_inserted}")

if __name__ == '__main__':
    process_massive_files()
