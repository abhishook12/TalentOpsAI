import os
import pandas as pd
import glob

files = []
for ext in ('**/*.csv', '**/*.parquet'):
    files.extend(glob.glob(os.path.join('C:\\TalentOpsAI', ext), recursive=True))

results = []
for f in files:
    if 'node_modules' in f or '.git' in f or '.venv' in f:
        continue
    try:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        if f.endswith('.csv'):
            # Just read the file and count lines without loading all into memory to be safe, but pandas is fine for small files
            with open(f, 'rb') as fp:
                rows = sum(1 for _ in fp) - 1 # subtract header
        elif f.endswith('.parquet'):
            df = pd.read_parquet(f, columns=[]) # only read metadata for rows
            rows = len(df)
        else:
            continue
            
        results.append((f, size_mb, rows))
    except Exception as e:
        pass

results.sort(key=lambda x: x[1], reverse=True)
for f, size, rows in results[:30]:
    status = "IGNORE (>50k)" if rows > 50000 else "KEEP (<=50k)"
    print(f"{status} | {rows} rows | {size:.2f} MB | {f}")
