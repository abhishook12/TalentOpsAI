import psycopg

def mass_deep_cleanup():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    with psycopg.connect(remote_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            print("=== STARTING MASS DEEP CLEANUP ===")
            
            # 1. Purge Suspicious Recruiters
            cur.execute("""
                DELETE FROM recruiters
                WHERE recruiter_name ~ '[0-9]' OR LENGTH(TRIM(recruiter_name)) < 2 OR recruiter_name ILIKE '%test%' OR recruiter_name ILIKE '%unknown%'
            """)
            print(f"[Purge] Deleted {cur.rowcount} suspicious recruiters.")
            
            # 2. Nullify Dummy Locations and Bad Phones
            cur.execute("""
                UPDATE recruiters
                SET location = NULL
                WHERE location ILIKE 'none' OR location ILIKE 'n/a' OR location ILIKE 'null' OR location ILIKE 'test%'
            """)
            print(f"[Nullify] Cleared {cur.rowcount} dummy locations.")
            
            cur.execute("""
                UPDATE recruiters
                SET phone = NULL
                WHERE phone IS NOT NULL AND phone != ''
                  AND (phone ~ '[a-zA-Z]' OR LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 7)
            """)
            print(f"[Nullify] Cleared {cur.rowcount} invalid phone numbers.")
            
            cur.execute("""
                UPDATE recruiters
                SET title = NULL
                WHERE title IS NOT NULL AND title != ''
                  AND (title ILIKE 'none' OR title ILIKE 'n/a' OR title ILIKE 'null' OR title ILIKE 'unknown')
            """)
            print(f"[Nullify] Cleared {cur.rowcount} dummy job titles.")

            # 3. Smart Merge Duplicate Company Names
            cur.execute("""
                SELECT company_name, array_agg(company_id ORDER BY company_id)
                FROM companies
                WHERE company_name IS NOT NULL AND company_name != ''
                GROUP BY company_name
                HAVING COUNT(*) > 1
            """)
            duplicate_groups = cur.fetchall()
            
            master_ids = []
            dupe_ids = []
            for name, c_ids in duplicate_groups:
                master = c_ids[0]
                for did in c_ids[1:]:
                    master_ids.append(master)
                    dupe_ids.append(did)
                    
            if master_ids:
                print(f"[Merge] Reassigning recruiters for {len(dupe_ids)} duplicate company names...")
                batch_size = 5000
                total_reassigned = 0
                for i in range(0, len(master_ids), batch_size):
                    batch_masters = master_ids[i:i+batch_size]
                    batch_dupes = dupe_ids[i:i+batch_size]
                    cur.execute("""
                        UPDATE recruiters AS r
                        SET company_id = t.master_id
                        FROM unnest(%s, %s) AS t(master_id, old_id)
                        WHERE r.company_id = t.old_id
                    """, (batch_masters, batch_dupes))
                    total_reassigned += cur.rowcount
                    conn.commit()
                print(f"[Merge] Reassigned {total_reassigned} recruiters.")
                
                print(f"[Merge] Deleting {len(dupe_ids)} duplicate company records...")
                for i in range(0, len(dupe_ids), batch_size):
                    batch_dupes = dupe_ids[i:i+batch_size]
                    cur.execute("""
                        DELETE FROM companies
                        WHERE company_id = ANY(%s)
                    """, (batch_dupes,))
                    conn.commit()
                print("[Merge] Duplicate companies deleted.")
            
            # 4. Delete Orphaned Companies
            # We do this last because the merges might have created more orphans.
            print("[Purge] Identifying orphaned companies (0 recruiters)...")
            cur.execute("""
                SELECT c.company_id
                FROM companies c
                LEFT JOIN recruiters r ON c.company_id = r.company_id
                WHERE r.recruiter_id IS NULL
            """)
            orphans = [row[0] for row in cur.fetchall()]
            
            if orphans:
                print(f"[Purge] Deleting {len(orphans)} orphaned companies in batches...")
                batch_size = 5000
                total_deleted = 0
                for i in range(0, len(orphans), batch_size):
                    batch_orphans = orphans[i:i+batch_size]
                    cur.execute("""
                        DELETE FROM companies
                        WHERE company_id = ANY(%s)
                    """, (batch_orphans,))
                    total_deleted += cur.rowcount
                    conn.commit()
                print(f"[Purge] Deleted {total_deleted} orphaned companies.")
            
            print("=== CLEANUP COMPLETED ===")

if __name__ == "__main__":
    mass_deep_cleanup()
