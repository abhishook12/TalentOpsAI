import pandas as pd
import sys
import gc

f1 = r'C:\Users\User\Downloads\arjun 2nd sheet .xlsx'
f2 = r'C:\Users\User\Downloads\merged_master_final.xlsx'

print("Starting memory-efficient evaluation of massive datasets...")

try:
    print(f"Reading {f2}...")
    df2 = pd.read_excel(f2, engine='openpyxl')
    merged_rows = len(df2)
    merged_valid = df2['email'].dropna().shape[0] if 'email' in df2.columns else 0
    print(f"MERGED MASTER: {merged_rows} total rows, {merged_valid} valid emails")
    del df2
    gc.collect()

    print(f"\nReading {f1}...")
    df1 = pd.read_excel(f1, engine='openpyxl')
    arjun_rows = len(df1)
    
    # We found out earlier that the email column in the arjun sheet is fully capitalized as 'EMAIL'
    arjun_valid = df1['EMAIL'].dropna().shape[0] if 'EMAIL' in df1.columns else 0
    print(f"ARJUN SHEET: {arjun_rows} total rows, {arjun_valid} valid emails")
    del df1
    gc.collect()
    
    print("\n--- EVALUATION CONCLUSION ---")
    if merged_valid > arjun_valid:
        print("WINNER: merged_master_final.xlsx")
    else:
        print("WINNER: arjun 2nd sheet .xlsx")

except Exception as e:
    print(f"Evaluation Error: {e}")
