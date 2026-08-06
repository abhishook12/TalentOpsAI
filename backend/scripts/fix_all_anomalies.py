import psycopg

def fix_anomalies():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            
            print("--- 1. Deduplicating Companies ---")
            cur.execute("""
                SELECT website, array_agg(company_id) 
                FROM companies 
                WHERE website IS NOT NULL AND website != '' 
                GROUP BY website 
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            
            master_ids = []
            dupe_ids = []
            
            for website, c_ids in duplicates:
                master_id = min(c_ids)
                for did in c_ids:
                    if did != master_id:
                        master_ids.append(master_id)
                        dupe_ids.append(did)
                        
            if master_ids:
                print(f"Re-assigning recruiters from {len(dupe_ids)} duplicate companies to their master records...")
                cur.execute("""
                    UPDATE recruiters AS r
                    SET company_id = t.new_id
                    FROM unnest(%s, %s) AS t(new_id, old_id)
                    WHERE r.company_id = t.old_id
                """, (master_ids, dupe_ids))
                print(f"Updated {cur.rowcount} recruiters.")
                
                print(f"Deleting {len(dupe_ids)} duplicate companies...")
                cur.execute("""
                    DELETE FROM companies
                    WHERE company_id = ANY(%s)
                """, (dupe_ids,))
                print(f"Deleted {cur.rowcount} companies.")
            else:
                print("No duplicates to merge.")
                
            print("\\n--- 2. Purging Malformed Data ---")
            cur.execute("DELETE FROM recruiters WHERE email IS NULL OR email = '' OR email NOT LIKE '%@%.%'")
            print(f"Deleted invalid emails: {cur.rowcount}")
            
            cur.execute("DELETE FROM recruiters WHERE LENGTH(TRIM(recruiter_name)) < 2")
            print(f"Deleted short names: {cur.rowcount}")
            
            cur.execute("DELETE FROM companies WHERE company_name IS NULL OR company_name = ''")
            print(f"Deleted companies missing names: {cur.rowcount}")
            
            print("\\n--- 3. Auto-Assigning Missing Companies ---")
            import re
            cur.execute("SELECT company_id, website FROM companies WHERE website IS NOT NULL AND website != ''")
            all_companies = cur.fetchall()
            domain_map = {}
            for cid, website in all_companies:
                website = website.lower().strip()
                website = re.sub(r'^https?://', '', website)
                website = re.sub(r'^www\\.', '', website)
                website = website.split('/')[0]
                if website:
                    if website not in domain_map:
                        domain_map[website] = cid
                        
            cur.execute("SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email IS NOT NULL AND email LIKE '%@%'")
            missing = cur.fetchall()
            
            assign_cids = []
            assign_rids = []
            
            for rid, email in missing:
                domain = email.split('@')[-1].lower().strip()
                if domain in domain_map:
                    assign_cids.append(domain_map[domain])
                    assign_rids.append(rid)
                    
            if assign_cids:
                print(f"Found {len(assign_cids)} orphaned recruiters matching an existing domain. Assigning...")
                batch_size = 5000
                total_updated = 0
                for i in range(0, len(assign_cids), batch_size):
                    batch_cids_part = assign_cids[i:i+batch_size]
                    batch_rids_part = assign_rids[i:i+batch_size]
                    cur.execute("""
                        UPDATE recruiters AS r
                        SET company_id = t.cid
                        FROM unnest(%s, %s) AS t(cid, rid)
                        WHERE r.recruiter_id = t.rid
                    """, (batch_cids_part, batch_rids_part))
                    total_updated += cur.rowcount
                    conn.commit()
                print(f"Assignments complete. {total_updated} updated.")
            else:
                print("No orphaned recruiters could be assigned.")
            
        conn.commit()
        print("\\nAll fixes applied successfully and committed.")

if __name__ == "__main__":
    fix_anomalies()
