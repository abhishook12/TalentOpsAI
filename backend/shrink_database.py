from app.database import SessionLocal, engine
from sqlalchemy import text
import time

def run():
    print("Starting database shrink procedure...")
    db = SessionLocal()
    
    # 1. Measure initial size
    size_before = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    print(f"Initial DB Size: {size_before}")
    
    # 2. Delete recruiters with no location
    print("Deleting recruiters with no location...")
    res1 = db.execute(text("DELETE FROM recruiters WHERE location IS NULL OR location = ''"))
    db.commit()
    print(f"Deleted {res1.rowcount} recruiters with no location.")
    
    # 3. Delete 80,000 recruiters with no phone
    print("Deleting 80,000 recruiters with no phone...")
    res2 = db.execute(text("""
        DELETE FROM recruiters WHERE recruiter_id IN (
            SELECT recruiter_id FROM recruiters 
            WHERE phone IS NULL OR phone = '' 
            LIMIT 80000
        )
    """))
    db.commit()
    print(f"Deleted {res2.rowcount} recruiters with no phone.")
    
    db.close()
    
    # 4. Vacuum Full
    print("Running VACUUM FULL on recruiters (this physically rewrites the file, might take a minute)...")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM FULL recruiters"))
        print("VACUUM FULL recruiters complete.")
        
        print("Running VACUUM FULL on companies...")
        conn.execute(text("VACUUM FULL companies"))
        print("VACUUM FULL companies complete.")
        
        print("Running VACUUM FULL on email_logs...")
        conn.execute(text("VACUUM FULL email_logs"))
        print("VACUUM FULL email_logs complete.")
        
    # 5. Measure final size
    db = SessionLocal()
    size_after = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
    print(f"Final DB Size: {size_after}")
    db.close()
    print("Shrink procedure complete.")

if __name__ == "__main__":
    run()
