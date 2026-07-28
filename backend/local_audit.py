import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal

def run_diagnostic():
    db = SessionLocal()
    try:
        # Total recruiters
        total = db.execute(text("SELECT COUNT(*) FROM recruiters")).fetchone()[0]
        
        # Missing states
        missing_states = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = '' OR state = 'Unknown'")).fetchone()[0]
        
        # Missing company assignments
        missing_companies = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NULL")).fetchone()[0]
        
        # Missing LinkedIn URLs
        missing_linkedin = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE linkedin IS NULL OR linkedin = ''")).fetchone()[0]
        
        print(f"Total Recruiters: {total}")
        print(f"Missing States: {missing_states}")
        print(f"Missing Companies: {missing_companies}")
        print(f"Missing LinkedIn: {missing_linkedin}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_diagnostic()
