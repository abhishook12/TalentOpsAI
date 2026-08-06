import os
import glob
import pandas as pd
import json

directories = [
    r"C:\Users\User\Desktop",
    r"C:\Users\User\Downloads",
    r"C:\Users\User\Documents"
]

files_to_check = []
for d in directories:
    for ext in ['*.xlsx', '*.xls', '*.csv']:
        files_to_check.extend(glob.glob(os.path.join(d, '**', ext), recursive=True))

results = []
for filepath in files_to_check:
    try:
        # Ignore temp excel files
        if os.path.basename(filepath).startswith('~'):
            continue
            
        size = os.path.getsize(filepath)
        if size == 0:
            continue
            
        # Try reading just the headers
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, nrows=0)
            sheet_name = 'default'
            cols = df.columns.tolist()
            if len(cols) <= 15:
                results.append({'file': filepath, 'sheet': sheet_name, 'columns': cols, 'count': len(cols), 'size': size})
        else:
            xl = pd.ExcelFile(filepath)
            for sheet_name in xl.sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=0)
                cols = df.columns.tolist()
                if len(cols) <= 15:
                    results.append({'file': filepath, 'sheet': sheet_name, 'columns': cols, 'count': len(cols), 'size': size})
                    
    except Exception as e:
        # Silently continue on read errors (password protected, corrupted, etc)
        pass

# Save results for agent to read
with open('c:/TalentOpsAI/backend/scripts/discovery_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Discovered {len(results)} valid sheets/files with <= 15 columns.")
