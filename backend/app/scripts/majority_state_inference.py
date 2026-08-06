import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import text
from app.database import SessionLocal

def run():
    print("=== STARTING MAJORITY STATE INFERENCE (SQL BULK) ===", flush=True)
    t0 = time.time()
    db = SessionLocal()
    
    try:
        print("Executing bulk update via SQL...", flush=True)
        update_query = text('''
            WITH domain_counts AS (
                SELECT SPLIT_PART(email, '@', 2) as domain, state, COUNT(*) as cnt
                FROM recruiters 
                WHERE email IS NOT NULL AND email != '' 
                  AND state IS NOT NULL AND state != '' AND state != 'US'
                GROUP BY SPLIT_PART(email, '@', 2), state
            ),
            ranked_domains AS (
                SELECT domain, state, 
                       ROW_NUMBER() OVER(PARTITION BY domain ORDER BY cnt DESC) as rn
                FROM domain_counts
            ),
            majority_states AS (
                SELECT domain, state 
                FROM ranked_domains 
                WHERE rn = 1
            )
            UPDATE recruiters r
            SET state = ms.state, state_source = 'company_majority_state'
            FROM majority_states ms
            WHERE SPLIT_PART(r.email, '@', 2) = ms.domain
              AND (r.state IS NULL OR r.state = '')
              AND r.email IS NOT NULL AND r.email != '';
        ''')
        
        result = db.execute(update_query)
        db.commit()
        
        print(f"Successfully updated {result.rowcount} recruiters!")
        print(f"Time Elapsed: {time.time() - t0:.2f}s")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    run()
