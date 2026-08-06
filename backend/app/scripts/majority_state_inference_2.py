import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import text
from app.database import SessionLocal

def run():
    print("=== STARTING FALLBACK HQ STATE INFERENCE (SQL BULK) ===", flush=True)
    t0 = time.time()
    db = SessionLocal()
    
    try:
        print("Executing bulk update via SQL using company HQ state...", flush=True)
        update_query = text('''
            UPDATE recruiters r
            SET state = c.state, state_source = 'company_hq_fallback'
            FROM companies c
            WHERE r.company_id = c.company_id
              AND (r.state IS NULL OR r.state = '')
              AND c.state IS NOT NULL AND c.state != '' AND c.state != 'US';
        ''')
        
        result = db.execute(update_query)
        db.commit()
        
        print(f"Successfully updated {result.rowcount} recruiters using company HQ!")
        print(f"Time Elapsed: {time.time() - t0:.2f}s")
        
        res = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NULL OR state = ''")).scalar()
        print(f"Unknown state recruiters remaining: {res}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    run()
