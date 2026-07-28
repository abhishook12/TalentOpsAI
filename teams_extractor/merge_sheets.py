import pandas as pd
import glob
import os

folder_path = r"C:\TalentOpsAI\teams_extractor\output"
all_files = glob.glob(os.path.join(folder_path, "vision_extracted_data_*.xlsx"))

print(f"Found {len(all_files)} files to merge.")

total_input_rows = 0
df_list = []
for f in all_files:
    try:
        df = pd.read_excel(f)
        total_input_rows += len(df)
        df_list.append(df)
    except Exception as e:
        print(f"Error reading {f}: {e}")

if df_list:
    merged_df = pd.concat(df_list, ignore_index=True)
    out_path = os.path.join(folder_path, "master_sheet.xlsx")
    merged_df.to_excel(out_path, index=False)
    print("Merged successfully!")
    print(f"Total input rows across all files: {total_input_rows}")
    
    # Check 1: File exists
    print(f"Check 1: File exists: {os.path.exists(out_path)}, Size: {os.path.getsize(out_path)} bytes")
    
    # Check 2: Row count matches
    verify_df = pd.read_excel(out_path)
    print(f"Check 2: Merged file row count: {len(verify_df)} (Matches: {len(verify_df) == total_input_rows})")
    
    # Check 3: Data integrity
    print(f"Check 3: Columns: {list(verify_df.columns)}")
    print("First 2 rows of merged data:")
    print(verify_df.head(2))
else:
    print("No dataframes to merge.")
