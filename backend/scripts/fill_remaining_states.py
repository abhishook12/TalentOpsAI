import pandas as pd
import time

def fill_remaining(parquet_path):
    print(f"Loading {parquet_path}...")
    t0 = time.time()
    df = pd.read_parquet(parquet_path)
    
    missing_mask = df['state'].isna() | (df['state'] == '')
    initial_missing = missing_mask.sum()
    print(f"Loaded {len(df):,} rows. {initial_missing:,} missing states.")
    
    if initial_missing > 0:
        print("Filling remaining unknown states with 'US'...")
        df.loc[missing_mask, 'state'] = 'US'
        
        final_missing = (df['state'].isna() | (df['state'] == '')).sum()
        print(f"Filled {initial_missing - final_missing:,} states. Remaining unknown: {final_missing:,}")
        
        print("Saving...")
        df.to_parquet(parquet_path, index=False, compression='brotli')
    
    print(f"Done in {time.time() - t0:.1f}s.")

if __name__ == '__main__':
    fill_remaining('C:/TalentOpsAI/backend/data/recruiters_full.parquet')
