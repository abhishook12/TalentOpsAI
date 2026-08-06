import os
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import time

load_dotenv(r'C:\TalentOpsAI\backend\.env')
DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('+psycopg', '')
DATABASE_URL = DATABASE_URL.replace(':6543', ':5432') # Direct connection to avoid timeouts

def process_380k():
    print("Connecting to DB:", DATABASE_URL)
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("SET statement_timeout = 0;")
    
    print("Starting massive migration of 380,000 emails...")
    start_time = time.time()
    
    # 1. Insert primary emails from recruiters into recruiter_emails
    print("Migrating primary emails...")
    cur.execute("""
        INSERT INTO recruiter_emails (recruiter_id, email, is_primary, confidence_score, status, company_domain_id, created_at, updated_at)
        SELECT 
            recruiter_id, 
            LOWER(TRIM(email)), 
            TRUE, 
            50, 
            'never_used',
            company_domain_id,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM recruiters r
        WHERE r.email IS NOT NULL AND r.email <> ''
        ON CONFLICT (email) DO NOTHING;
    """)
    print(f"Inserted primary emails. Rowcount: {cur.rowcount}")

    # 2. Initialize mailintel_tracking for all recruiter_emails
    print("Initializing MAILINTEL tracking rows for all emails...")
    cur.execute("""
        INSERT INTO mailintel_tracking (email_id, created_at, updated_at)
        SELECT id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM recruiter_emails
        ON CONFLICT (email_id) DO NOTHING;
    """)
    print(f"Initialized tracking rows. Rowcount: {cur.rowcount}")

    # 3. Apply Domain Reputation scores dynamically to the whole database
    # If a domain has a reputation score > 0, we adjust the confidence of all emails in that domain
    print("Applying historical domain intelligence to all 380k emails...")
    cur.execute("""
        UPDATE recruiter_emails re
        SET 
            confidence_score = LEAST(100, GREATEST(0, 50 + (dr.reputation_score - 50))),
            status = CASE 
                WHEN (50 + (dr.reputation_score - 50)) >= 95 THEN 'verified'
                WHEN (50 + (dr.reputation_score - 50)) >= 80 THEN 'likely_valid'
                WHEN (50 + (dr.reputation_score - 50)) >= 60 THEN 'needs_monitoring'
                WHEN (50 + (dr.reputation_score - 50)) >= 30 THEN 'suspicious'
                ELSE 'invalid'
            END,
            updated_at = CURRENT_TIMESTAMP
        FROM domain_reputation dr
        WHERE dr.domain = SPLIT_PART(re.email, '@', 2)
          AND dr.total_sent > 0
          AND re.status = 'never_used';
    """)
    print(f"Applied domain intelligence to {cur.rowcount} emails.")
    
    elapsed = time.time() - start_time
    print(f"Migration completed in {elapsed:.2f} seconds!")
    
    # 4. Count total emails now tracked by MAILINTEL
    cur.execute("SELECT COUNT(*) FROM recruiter_emails;")
    total_emails = cur.fetchone()[0]
    print(f"Total emails now in MAILINTEL: {total_emails}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    process_380k()
