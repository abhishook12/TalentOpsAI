import os, sys, time
sys.path.append('C:/TalentOpsAI/backend')
from sqlalchemy import create_engine, text

# Hardcode the production URL safely for this specific maintenance script
PROD_DB_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def clean_database():
    engine = create_engine(PROD_DB_URL, pool_pre_ping=True)
    
    print("Starting safe, throttle-controlled cleanup...")
    
    # Emails are NOT NULL and UNIQUE, so 'missing.local' is actually the correct
    # system tag for users without an email (prevents deletion). We skip email wiping.
    
    # Clean names
    print("Flagging bad names in chunks...")
    while True:
        with engine.begin() as conn:
            res = conn.execute(text("""
                SELECT recruiter_id FROM recruiters 
                WHERE (recruiter_name IS NULL OR recruiter_name = '' OR recruiter_name ILIKE '%unknown%' OR length(recruiter_name) <= 2)
                AND needs_review = false
                LIMIT 500
            """)).fetchall()
            
            if not res:
                break
                
            ids = [r[0] for r in res]
            conn.execute(text("UPDATE recruiters SET needs_review = true, completeness_score = 0, review_reason = 'Invalid name detected' WHERE recruiter_id = ANY(:ids)"), {"ids": ids})
            print(f"Flagged {len(ids)} bad names...")
        time.sleep(0.2)

    print("Flagging dummy emails and phones in chunks...")
    while True:
        with engine.begin() as conn:
            res = conn.execute(text("""
                SELECT recruiter_id FROM recruiters 
                WHERE (
                    email ILIKE 'dummy%' OR email ILIKE 'test@%' OR email ILIKE 'noemail%' OR email ILIKE 'unknown%'
                    OR phone = '0000000000' OR phone = '1111111111' OR phone = '1234567890' OR phone = '9999999999'
                )
                AND needs_review = false
                LIMIT 500
            """)).fetchall()
            
            if not res:
                break
                
            ids = [r[0] for r in res]
            conn.execute(text("UPDATE recruiters SET needs_review = true, completeness_score = 0, review_reason = 'Dummy email or phone detected' WHERE recruiter_id = ANY(:ids)"), {"ids": ids})
            print(f"Flagged {len(ids)} bad emails/phones...")
        time.sleep(0.2)

    print("Cleanup complete!")

if __name__ == "__main__":
    clean_database()
