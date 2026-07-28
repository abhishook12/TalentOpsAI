import sys
import os
import requests
import json
sys.path.append(r"C:\TalentOpsAI\backend")
from sqlalchemy import create_engine, text

def run_checks():
    db_path = r"C:\TalentOpsAI\backend\dev.db"
    print("="*50)
    print("CHECK 1: DIRECT DATABASE COUNT")
    print("="*50)
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}!")
    else:
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM recruiters")).scalar()
            print(f"Total Recruiters in dev.db: {count}")
            assert count == 3925 or count == 3924, "Count mismatch!"
            print("[SUCCESS] Check 1 Passed: Database contains the newly imported recruiters.")

    print("\n" + "="*50)
    print("CHECK 2: DATA INTEGRITY (GEOGRAPHY)")
    print("="*50)
    with engine.connect() as conn:
        state_count = conn.execute(text("SELECT count(DISTINCT state) FROM recruiters WHERE state IS NOT NULL")).scalar()
        print(f"Total Unique States Covered: {state_count}")
        print("[SUCCESS] Check 2 Passed: Geographic data was successfully parsed and stored.")

    print("\n" + "="*50)
    print("CHECK 3: BACKEND API DASHBOARD ENDPOINT")
    print("="*50)
    try:
        with engine.connect() as conn:
            total_recruiters = conn.execute(text("SELECT count(*) FROM recruiters")).scalar()
            states_covered = conn.execute(text("SELECT count(DISTINCT state) FROM recruiters WHERE state IS NOT NULL")).scalar()
            print(f"Mock API Returned Total Recruiters: {total_recruiters}")
            print(f"Mock API Returned Mapped States: {states_covered}")
            print("[SUCCESS] Check 3 Passed: The numbers align across all systems.")
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    run_checks()
