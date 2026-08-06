import psycopg


def repair_postgres_fast():
    print("\\n--- Repairing Postgres (aws-1) FAST ---")
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url) as conn:
        with conn.cursor() as cur:
            
            print("1. Fetching all companies...")
            cur.execute("SELECT company_id, website FROM companies WHERE website IS NOT NULL AND website != ''")
            companies = cur.fetchall()
            
            # Build domain to company_id mapping
            import urllib.parse
            import re
            
            domain_map = {}
            for cid, website in companies:
                website = website.lower().strip()
                # Extract domain, handle http, https, www, etc.
                website = re.sub(r'^https?://', '', website)
                website = re.sub(r'^www\\.', '', website)
                website = website.split('/')[0] # Get just the host
                if website:
                    domain_map[website] = cid
            
            print(f"Mapped {len(domain_map)} unique domains.")
            
            print("2. Fetching recruiters to repair...")
            cur.execute("SELECT recruiter_id, email, company_id FROM recruiters WHERE email IS NOT NULL AND email LIKE '%@%'")
            recruiters = cur.fetchall()
            
            updates = []
            for rid, email, old_cid in recruiters:
                domain = email.split('@')[-1].lower().strip()
                if domain in domain_map:
                    correct_cid = domain_map[domain]
                    if old_cid != correct_cid:
                        updates.append((correct_cid, rid))
            
            print(f"Found {len(updates)} recruiters to repair.")
            
            if updates:
                print("3. Executing repairs...")
                cur.executemany("UPDATE recruiters SET company_id = %s WHERE recruiter_id = %s", updates)
                print("Repairs completed.")
            
            # Check Isabelle specifically
            cur.execute("SELECT company_id FROM recruiters WHERE email = 'isabelle.burke@catapulthc.com'")
            res = cur.fetchone()
            if res:
                c_id = res[0]
                cur.execute("SELECT company_name FROM companies WHERE company_id = %s", (c_id,))
                c_name = cur.fetchone()
                if c_name:
                    print(f"Isabelle is now assigned to: {c_name[0]}")
                else:
                    print(f"Isabelle assigned to company_id {c_id}, which has no name?")
                    
        conn.commit()

if __name__ == "__main__":
    repair_postgres_fast()
