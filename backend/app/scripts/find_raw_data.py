import os
import sqlite3
import pandas as pd

def scan_files():
    print("Scanning for local raw data...")
    found_files = []
    
    # Directories to scan
    dirs_to_scan = [
        "C:\\TalentOpsAI\\backend\\uploads",
        "C:\\TalentOpsAI\\backend\\data",
        "C:\\TalentOpsAI\\backend\\exports",
        "C:\\TalentOpsAI\\backend\\imports",
        "C:\\TalentOpsAI\\backend\\raw",
    ]
    
    for d in dirs_to_scan:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ['.xlsx', '.csv', '.json', '.sql']:
                        found_files.append(os.path.join(root, f))
                        
    # Add SQLite DB
    if os.path.exists("C:\\TalentOpsAI\\backend\\dev.db"):
        found_files.append("C:\\TalentOpsAI\\backend\\dev.db")
        
    # Add the main desktop file
    desktop_file = "C:\\Users\\User\\Desktop\\final updated sheet.xlsx"
    if os.path.exists(desktop_file):
        found_files.append(desktop_file)
        
    print(f"Found {len(found_files)} potential raw data files. Counting rows...")
    
    results = []
    for f in found_files:
        try:
            ext = os.path.splitext(f)[1].lower()
            count = 0
            if ext == '.xlsx':
                xl = pd.ExcelFile(f)
                for sheet in xl.sheet_names:
                    df = xl.parse(sheet)
                    count += len(df)
            elif ext == '.csv':
                df = pd.read_csv(f, low_memory=False)
                count = len(df)
            elif ext == '.json':
                df = pd.read_json(f)
                count = len(df)
            elif ext == '.db':
                conn = sqlite3.connect(f)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cur.fetchall()
                for table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count += cur.fetchone()[0]
                conn.close()
            elif ext == '.sql':
                # Just estimate lines
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    count = sum(1 for _ in file)
                    
            results.append((f, count))
            print(f"File: {f} | Rows/Entries: {count}")
        except Exception as e:
            print(f"File: {f} | Error counting: {e}")
            
    print("-" * 50)
    print("Summary of data sources:")
    for f, c in results:
        print(f"{f} - {c} rows")

if __name__ == "__main__":
    scan_files()
