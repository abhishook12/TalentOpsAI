import sys, os, textwrap
from sqlalchemy import text
from sqlalchemy.orm import Session
sys.path.append(os.getcwd())
from app.database import SessionLocal, engine
from app.models.models import Recruiter

def split_phones(val):
    if not val: return val
    if not val.isdigit(): return val
    length = len(val)
    if length > 10 and length % 10 == 0:
        chunks = textwrap.wrap(val, 10)
        return ", ".join(chunks)
    elif length > 11 and length % 11 == 0 and val.startswith('1'):
        chunks = textwrap.wrap(val, 11)
        # strip leading 1
        clean_chunks = [c[1:] if c.startswith('1') else c for c in chunks]
        return ", ".join(clean_chunks)
    return val

def main():
    print("Connecting to DB...")
    db = SessionLocal()
    
    # 1. Fix concatenated phone numbers
    print("Fixing phone numbers...")
    recruiters = db.query(Recruiter).all()
    updates = 0
    for r in recruiters:
        changed = False
        if r.phone:
            new_p = split_phones(r.phone)
            if new_p != r.phone:
                r.phone = new_p
                changed = True
        if r.phone2:
            new_p2 = split_phones(r.phone2)
            if new_p2 != r.phone2:
                r.phone2 = new_p2
                changed = True
        if changed:
            updates += 1
            
    print(f"Updated {updates} rows with split phone numbers.")
    db.commit()
    
    # 2. Add GIN Indexes to make search instant
    print("Adding pg_trgm extension and GIN indexes...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        conn.commit()
        
        # Check if index exists
        res = conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'recruiters';")).fetchall()
        indexes = [r[0] for r in res]
        
        if 'idx_recruiters_name_trgm' not in indexes:
            print("Creating index on recruiter_name...")
            conn.execute(text("CREATE INDEX idx_recruiters_name_trgm ON recruiters USING gin (recruiter_name gin_trgm_ops);"))
            conn.commit()
            
        if 'idx_recruiters_email_trgm' not in indexes:
            print("Creating index on email...")
            conn.execute(text("CREATE INDEX idx_recruiters_email_trgm ON recruiters USING gin (email gin_trgm_ops);"))
            conn.commit()
            
    print("Database optimizations complete!")

if __name__ == '__main__':
    main()
