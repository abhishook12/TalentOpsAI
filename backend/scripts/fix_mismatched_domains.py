import psycopg
import re

def fix_mismatched_domains():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            print("Fetching domain map from companies...")
            cur.execute("""
                SELECT company_id, email_pattern 
                FROM companies 
                WHERE email_pattern IS NOT NULL AND email_pattern != ''
            """)
            domain_map = {}
            for cid, pattern in cur.fetchall():
                if pattern not in domain_map:
                    domain_map[pattern] = cid

            print("Fetching mismatched recruiters...")
            cur.execute("""
                SELECT r.recruiter_id, SPLIT_PART(r.email, '@', 2) as domain, r.company_id
                FROM recruiters r
                JOIN companies c ON r.company_id = c.company_id
                WHERE r.email IS NOT NULL 
                  AND r.email != ''
                  AND c.email_pattern IS NOT NULL 
                  AND c.email_pattern != ''
                  AND SPLIT_PART(r.email, '@', 2) != c.email_pattern
                  AND SPLIT_PART(r.email, '@', 2) NOT LIKE '%.missing.local'
                  AND SPLIT_PART(r.email, '@', 2) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com')
            """)
            mismatched = cur.fetchall()
            print(f"Found {len(mismatched)} mismatched recruiters (excluding generic emails).")

            assign_rids = []
            assign_cids = []
            nullify_rids = []

            for rid, domain, current_cid in mismatched:
                domain = domain.lower().strip()
                if domain in domain_map:
                    # We know the right company for this domain
                    correct_cid = domain_map[domain]
                    if correct_cid != current_cid:
                        assign_rids.append(rid)
                        assign_cids.append(correct_cid)
                else:
                    # We don't have the company, so they shouldn't be linked to the WRONG company.
                    nullify_rids.append(rid)

            if assign_rids:
                print(f"Reassigning {len(assign_rids)} recruiters to their correct company based on email domain...")
                batch_size = 5000
                total_updated = 0
                for i in range(0, len(assign_rids), batch_size):
                    batch_cids = assign_cids[i:i+batch_size]
                    batch_rids = assign_rids[i:i+batch_size]
                    cur.execute("""
                        UPDATE recruiters AS r
                        SET company_id = t.cid
                        FROM unnest(%s, %s) AS t(cid, rid)
                        WHERE r.recruiter_id = t.rid
                    """, (batch_cids, batch_rids))
                    total_updated += cur.rowcount
                    conn.commit()
                print(f"Reassigned {total_updated} recruiters.")

            if nullify_rids:
                print(f"Unlinking {len(nullify_rids)} recruiters from wrong companies (correct company not found)...")
                batch_size = 5000
                total_nullified = 0
                for i in range(0, len(nullify_rids), batch_size):
                    batch_rids = nullify_rids[i:i+batch_size]
                    cur.execute("""
                        UPDATE recruiters
                        SET company_id = NULL
                        WHERE recruiter_id = ANY(%s)
                    """, (batch_rids,))
                    total_nullified += cur.rowcount
                    conn.commit()
                print(f"Unlinked {total_nullified} recruiters.")
                
            print("Domain mismatch fix applied successfully.")

if __name__ == "__main__":
    fix_mismatched_domains()
