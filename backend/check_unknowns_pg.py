import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    
    count_unknown = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state = 'Unknown' OR state IS NULL")).scalar()
    count_total = db.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
    
    print(f"Total recruiters: {count_total}")
    print(f"Unknown states: {count_unknown}")
    if count_total > 0:
        print(f"Percentage unknown: {(count_unknown / count_total) * 100:.2f}%")
        
    sample = db.execute(text("SELECT recruiter_id, email, phone, location, notes FROM recruiters WHERE state = 'Unknown' OR state IS NULL LIMIT 20")).fetchall()
    print("\nSample of unknowns:")
    for row in sample:
        print(row)
        
    db.close()

if __name__ == '__main__':
    main()
