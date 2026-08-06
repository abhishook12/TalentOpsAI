"""
Phase 1: Export current PostgreSQL recruiters (full 59 columns) + merge with archived 260K.
Infer company_id for archived records from email domains.
Output: One unified Parquet file with ALL data.
"""
import os, sys, time
import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')
DB_URL = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

OUTPUT_DIR = 'C:/TalentOpsAI/backend/data'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    start = time.time()
    conn = psycopg.connect(DB_URL, autocommit=True, prepare_threshold=None)
    cur = conn.cursor()

    # ─── Step 1: Export ALL current recruiters from PostgreSQL (full schema) ───
    print("=" * 70)
    print("STEP 1: Exporting current PostgreSQL recruiters (all 59 columns)...")
    print("=" * 70, flush=True)

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'recruiters' ORDER BY ordinal_position")
    all_columns = [r[0] for r in cur.fetchall()]
    print(f"  Columns: {len(all_columns)}")

    col_list = ', '.join(all_columns)
    cur.execute(f"SELECT {col_list} FROM recruiters")
    rows = cur.fetchall()
    df_live = pd.DataFrame(rows, columns=all_columns)
    print(f"  Exported {len(df_live):,} live recruiters from PostgreSQL")

    # ─── Step 2: Load archived Parquet ───
    print("\nSTEP 2: Loading archived Parquet...", flush=True)
    archive_path = 'C:/TalentOpsAI/backend/archived_recruiters_unified.parquet'
    if os.path.exists(archive_path):
        df_archived = pd.read_parquet(archive_path)
        print(f"  Loaded {len(df_archived):,} archived recruiters ({list(df_archived.columns)})")
    else:
        print("  WARNING: No archive file found! Proceeding with live data only.")
        df_archived = pd.DataFrame()

    # ─── Step 3: Build email domain → company_id mapping from live data ───
    print("\nSTEP 3: Building domain -> company_id mapping...", flush=True)
    
    # Get domain-to-company mapping from live recruiters
    cur.execute("""
        SELECT LOWER(SPLIT_PART(email, '@', 2)) as domain, company_id, COUNT(*) as cnt
        FROM recruiters
        WHERE company_id IS NOT NULL 
          AND email IS NOT NULL AND POSITION('@' IN email) > 0
          AND LOWER(SPLIT_PART(email, '@', 2)) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'mail.com')
        GROUP BY LOWER(SPLIT_PART(email, '@', 2)), company_id
        ORDER BY cnt DESC
    """)
    domain_rows = cur.fetchall()
    
    # For each domain, pick the company_id with the most recruiters
    domain_to_company = {}
    for domain, company_id, cnt in domain_rows:
        if domain not in domain_to_company or cnt > domain_to_company[domain][1]:
            domain_to_company[domain] = (company_id, cnt)
    
    domain_map = {d: v[0] for d, v in domain_to_company.items()}
    print(f"  Built mapping for {len(domain_map):,} domains")

    # ─── Step 4: Enrich archived records ───
    if len(df_archived) > 0:
        print("\nSTEP 4: Enriching archived records with company_id...", flush=True)
        
        # Extract domain from archived emails
        def get_domain(email):
            if pd.isna(email) or '@' not in str(email):
                return None
            return str(email).split('@')[1].lower().strip()
        
        df_archived['_domain'] = df_archived['email'].apply(get_domain)
        df_archived['company_id'] = df_archived['_domain'].map(domain_map)
        df_archived.drop(columns=['_domain'], inplace=True)
        
        matched = df_archived['company_id'].notna().sum()
        print(f"  Matched {matched:,} / {len(df_archived):,} archived records to companies ({matched/len(df_archived)*100:.1f}%)")
        
        # Add missing columns with NULLs to match schema
        for col in all_columns:
            if col not in df_archived.columns:
                df_archived[col] = None
        
        # Reorder to match live schema
        df_archived = df_archived[all_columns]

    # ─── Step 5: Deduplicate by recruiter_id ───
    print("\nSTEP 5: Merging and deduplicating...", flush=True)
    
    # Remove any archived records that still exist in live (by recruiter_id)
    if len(df_archived) > 0:
        live_ids = set(df_live['recruiter_id'].tolist())
        df_archived_clean = df_archived[~df_archived['recruiter_id'].isin(live_ids)]
        print(f"  Removed {len(df_archived) - len(df_archived_clean):,} duplicate IDs (already in live)")
        df_merged = pd.concat([df_live, df_archived_clean], ignore_index=True)
    else:
        df_merged = df_live
    
    # Also deduplicate by email (keep the one with more data)
    before_dedup = len(df_merged)
    df_merged = df_merged.drop_duplicates(subset=['email'], keep='first')
    print(f"  Deduplicated by email: {before_dedup:,} -> {len(df_merged):,} (removed {before_dedup - len(df_merged):,})")

    # ─── Step 6: Fix corrupted data ───
    print("\nSTEP 6: Fixing corrupted data...", flush=True)
    
    # Fix .dup emails
    dup_mask = df_merged['email'].str.contains('.dup.', na=False)
    if dup_mask.any():
        import re
        df_merged.loc[dup_mask, 'email'] = df_merged.loc[dup_mask, 'email'].apply(
            lambda x: re.sub(r'\.dup\.\d+$', '', str(x)) if pd.notna(x) else x
        )
        print(f"  Fixed {dup_mask.sum():,} .dup email suffixes")
    
    # Fix semicolon names - keep first part
    semi_mask = df_merged['recruiter_name'].str.contains(';', na=False)
    if semi_mask.any():
        df_merged.loc[semi_mask, 'recruiter_name'] = df_merged.loc[semi_mask, 'recruiter_name'].apply(
            lambda x: str(x).split(';')[0].strip() if pd.notna(x) else x
        )
        print(f"  Fixed {semi_mask.sum():,} semicolon names")
    
    # Set is_active=True for all if missing
    df_merged['is_active'] = df_merged['is_active'].fillna(True)

    # ─── Step 7: Write final Parquet ───
    print("\nSTEP 7: Writing unified Parquet...", flush=True)
    
    parquet_path = os.path.join(OUTPUT_DIR, 'recruiters_full.parquet')
    df_merged.to_parquet(parquet_path, index=False, compression='brotli')
    
    file_size = os.path.getsize(parquet_path) / 1024 / 1024
    print(f"  Written: {parquet_path}")
    print(f"  Total records: {len(df_merged):,}")
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Columns: {len(df_merged.columns)}")
    
    # Stats
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Live from PostgreSQL:  {len(df_live):,}")
    print(f"  Restored from archive: {len(df_archived_clean) if len(df_archived) > 0 else 0:,}")
    print(f"  Total unified:         {len(df_merged):,}")
    print(f"  Parquet size:          {file_size:.2f} MB")
    print(f"  With company_id:       {df_merged['company_id'].notna().sum():,}")
    print(f"  Email status breakdown:")
    for status, cnt in df_merged['email_status'].value_counts().items():
        print(f"    {status}: {cnt:,}")
    print(f"  Time: {time.time() - start:.1f}s")
    
    conn.close()

if __name__ == '__main__':
    main()
