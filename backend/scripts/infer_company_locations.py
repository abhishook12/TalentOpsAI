import os
import psycopg
import time
from dotenv import load_dotenv

load_dotenv()
remote_url = os.getenv("DATABASE_URL")
if not remote_url:
    remote_url = "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
elif remote_url.startswith("postgresql+psycopg://"):
    remote_url = remote_url.replace("postgresql+psycopg://", "postgresql://")

def infer_locations():
    print("Starting Company Location Inference...")
    start = time.time()
    
    with psycopg.connect(remote_url) as conn:
        with conn.cursor() as cur:
            # First, fetch all company domains that HAVE a state
            cur.execute("""
                SELECT website, state 
                FROM companies 
                WHERE website IS NOT NULL 
                  AND website != '' 
                  AND state IS NOT NULL 
                  AND state != ''
            """)
            company_states = {}
            for website, state in cur.fetchall():
                domain = website.lower().strip()
                if '.' in domain:
                    company_states[domain] = state[:100]
                    
            print(f"Loaded {len(company_states)} company domains with known states.")
            
            # Fetch recruiters missing state
            cur.execute("""
                SELECT recruiter_id, email 
                FROM recruiters 
                WHERE (state IS NULL OR state = '') 
                  AND email LIKE '%@%'
            """)
            recruiters = cur.fetchall()
            print(f"Found {len(recruiters)} recruiters missing a state.")
            
            updates = []
            personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'aol.com'}
            
            for r_id, email in recruiters:
                parts = email.split('@')
                if len(parts) == 2:
                    domain = parts[1].lower().strip()
                    if domain not in personal_domains and domain in company_states:
                        updates.append((company_states[domain], r_id))
                        
            print(f"Found {len(updates)} recruiters that can be inferred from company domain.")
            
            if updates:
                print("Executing bulk update...")
                cur.executemany("""
                    UPDATE recruiters 
                    SET state = %s,
                        state_source = 'company_inferred',
                        state_confidence = 'low'
                    WHERE recruiter_id = %s
                """, updates)
                conn.commit()
                print(f"Actually updated {cur.rowcount} recruiters (out of {len(updates)} possible).")
            else:
                print("No updates needed.")
                
    print("="*50)
    print(f"INFERENCE COMPLETE in {time.time() - start:.2f}s")
    print("="*50)

if __name__ == "__main__":
    infer_locations()
