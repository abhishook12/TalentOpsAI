import os
import glob
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

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

def process_files():
    print("Starting process_files()...")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    files = [
        os.path.join(base_dir, 'backend', 'app', 'scripts', 'outputs', 'workbook_review_queue.json'),
        os.path.join(base_dir, 'backend', 'backup_18774_cohort_20260625_212008.json'),
        os.path.join(base_dir, 'backend', 'backup_18774_cohort_20260625_211739.json'),
        os.path.join(base_dir, 'backend', 'backup_18774_cohort_20260625_184414.json'),
        os.path.join(base_dir, 'teams_extractor', 'output', 'master_sheet.xlsx')
    ]

    total_inserted = 0
    print(f"Connecting to: {raw_url.split('@')[-1]}")
    print(f"Total files found to check: {len(files)}")
    
    for f in files:
        if any(skip in f.lower() for skip in ['node_modules', '.git', '.venv', '__pycache__', 'package-lock.json', 'package.json']):
            continue
            
        filename = os.path.basename(f).lower()
        
        # Determine target table
        if 'recruiter' in filename or 'master_sheet' in filename or 'review_queue' in filename or 'cohort' in filename:
            table_name = 'recruiters'
        elif 'compan' in filename:
            table_name = 'companies'
        else:
            continue
            
        try:
            if f.endswith('.csv'):
                df = pd.read_csv(f)
            elif f.endswith('.parquet'):
                df = pd.read_parquet(f)
            elif f.endswith('.json'):
                df = pd.read_json(f)
            elif f.endswith('.xlsx'):
                df = pd.read_excel(f)
                
            rows = len(df)
            if rows > 50000:
                print(f"Skipping (>{50000} rows): {filename}")
                continue

            print(f"Processing {filename} into {table_name}...")
            
            clean_data = clean_df(df, table_name)
            if clean_data is not None and not clean_data.empty:
                clean_data.to_sql(table_name, engine, if_exists='append', index=False, method='multi', chunksize=1000)
                print(f" -> Inserted {len(clean_data)} rows.")
                total_inserted += len(clean_data)
            else:
                print(f" -> No valid columns matched schema.")
        except Exception as e:
            print(f" -> Error processing {filename}: {e}")

    print(f"Finished! Total rows safely inserted without API egress: {total_inserted}")

if __name__ == '__main__':
    process_files()
