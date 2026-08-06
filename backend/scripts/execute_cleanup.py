"""
Execute the 3-tier cleanup plan:
1. Backup current parquet
2. Archive 111K low-value records
3. Delete 95K pure junk records
4. Keep 197K with state=US
5. Verify
"""
import pandas as pd
import shutil
import time
import os

PQ = 'C:/TalentOpsAI/backend/data/recruiters_full.parquet'
BACKUP = 'C:/TalentOpsAI/backend/data/recruiters_full_pre_cleanup.parquet'
ARCHIVE = 'C:/TalentOpsAI/backend/data/archived_low_value.parquet'

t0 = time.time()

# ── Step 1: Backup ──
print("STEP 1: Creating safety backup...")
shutil.copy2(PQ, BACKUP)
print(f"  Backup saved to: {BACKUP}")
print(f"  Size: {os.path.getsize(BACKUP) / 1024 / 1024:.1f} MB")

# ── Step 2: Load data ──
print("\nSTEP 2: Loading parquet...")
df = pd.read_parquet(PQ)
total_before = len(df)
print(f"  Total records: {total_before:,}")

# ── Step 3: Identify the 3 tiers ──
print("\nSTEP 3: Classifying records...")

us_mask = df['state'] == 'US'

# PURE JUNK: no real name + no real email + no phone + no company
junk_mask = us_mask & (
    (df['recruiter_name'].isna()) | (df['recruiter_name'] == '') | 
    (df['recruiter_name'].str.len() < 3) | (df['recruiter_name'].str.contains('@', na=False))
) & (
    (df['email'].isna()) | (df['email'] == '') | 
    (df['email'].str.contains('missing.local', na=False)) | 
    (df['email'].str.contains('invalid.local', na=False))
) & (
    (df['phone'].isna()) | (df['phone'] == '')
) & (
    df['company_id'].isna()
)

# LOW VALUE: no real email + no phone (but may have a name)
low_value_mask = us_mask & ~junk_mask & (
    (df['email'].isna()) | (df['email'] == '') | 
    (df['email'].str.contains('missing.local', na=False)) | 
    (df['email'].str.contains('invalid.local', na=False))
) & (
    (df['phone'].isna()) | (df['phone'] == '')
)

junk_count = junk_mask.sum()
low_value_count = low_value_mask.sum()
keep_us_count = us_mask.sum() - junk_count - low_value_count

print(f"  PURE JUNK (will delete):    {junk_count:,}")
print(f"  LOW VALUE (will archive):   {low_value_count:,}")
print(f"  KEEPABLE (will retain):     {keep_us_count:,}")
print(f"  NON-US (untouched):         {(~us_mask).sum():,}")

# ── Step 4: Archive low-value records ──
print("\nSTEP 4: Archiving low-value records...")
archived_df = df[low_value_mask].copy()
archived_df.to_parquet(ARCHIVE, index=False, compression='brotli')
print(f"  Archived {len(archived_df):,} records to: {ARCHIVE}")
print(f"  Archive size: {os.path.getsize(ARCHIVE) / 1024 / 1024:.1f} MB")

# ── Step 5: Remove junk + low-value from main dataset ──
print("\nSTEP 5: Removing junk and archived records from main dataset...")
remove_mask = junk_mask | low_value_mask
df_clean = df[~remove_mask].copy()
total_after = len(df_clean)
removed = total_before - total_after

print(f"  Records removed: {removed:,}")
print(f"  Records remaining: {total_after:,}")

# ── Step 6: Save cleaned dataset ──
print("\nSTEP 6: Saving cleaned parquet...")
df_clean.to_parquet(PQ, index=False, compression='brotli')
print(f"  New size: {os.path.getsize(PQ) / 1024 / 1024:.1f} MB")

# ── Step 7: Verify ──
print(f"\n{'='*60}")
print(f"CLEANUP COMPLETE")
print(f"{'='*60}")
print(f"  Before:              {total_before:,}")
print(f"  Deleted (junk):      {junk_count:,}")
print(f"  Archived (low val):  {low_value_count:,}")
print(f"  After:               {total_after:,}")
print(f"  Still 'US':          {(df_clean['state'] == 'US').sum():,}")
print(f"  With real states:    {((df_clean['state'] != 'US') & df_clean['state'].notna()).sum():,}")
print(f"  Time: {time.time() - t0:.1f}s")
