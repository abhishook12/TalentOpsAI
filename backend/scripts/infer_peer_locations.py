import os
import time
import psycopg
from dotenv import load_dotenv

load_dotenv()
remote_url = os.getenv("DATABASE_URL")
if not remote_url:
    remote_url = "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
elif remote_url.startswith("postgresql+psycopg://"):
    remote_url = remote_url.replace("postgresql+psycopg://", "postgresql://")

def infer_peer_locations():
    print("Starting Peer Domain Clustering Inference...")
    
    with psycopg.connect(remote_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            # 1. Get consensus states for domains
            print("Computing consensus states for email domains...")
            cur.execute("""
                WITH domain_states AS (
                    SELECT split_part(email, '@', 2) as domain, state, COUNT(*) as cnt
                    FROM recruiters
                    WHERE state IS NOT NULL AND state != '' AND email LIKE '%@%'
                    GROUP BY split_part(email, '@', 2), state
                ),
                best_states AS (
                    SELECT domain, state,
                           ROW_NUMBER() OVER(PARTITION BY domain ORDER BY cnt DESC) as rn
                    FROM domain_states
                )
                SELECT domain, state FROM best_states WHERE rn = 1
            """)
            
            domain_to_state = {row[0].lower().strip(): row[1] for row in cur.fetchall()}
            print(f"Loaded consensus states for {len(domain_to_state)} domains.")
            
            # 2. Get recruiters missing state
            cur.execute("""
                SELECT recruiter_id, email 
                FROM recruiters 
                WHERE (state IS NULL OR state = '') AND email LIKE '%@%'
            """)
            recruiters = cur.fetchall()
            print(f"Found {len(recruiters)} recruiters missing a state.")
            
            updates = []
            for r_id, email in recruiters:
                parts = email.split('@')
                if len(parts) == 2:
                    domain = parts[1].lower().strip()
                    if domain in domain_to_state:
                        updates.append((domain_to_state[domain], r_id))
                        
            print(f"Found {len(updates)} recruiters that can be inferred from peer domains.")
            
            if updates:
                print("Executing bulk update...")
                cur.executemany("""
                    UPDATE recruiters 
                    SET state = %s,
                        state_source = 'peer_domain_cluster_inference',
                        state_confidence = 'low'
                    WHERE recruiter_id = %s
                """, updates)
                conn.commit()
                print(f"Actually updated {cur.rowcount} recruiters.")
            else:
                print("No updates needed.")

if __name__ == "__main__":
    start = time.time()
    try:
        infer_peer_locations()
    except Exception as e:
        print(f"Error: {e}")
    print(f"Finished in {time.time() - start:.2f} seconds.")
