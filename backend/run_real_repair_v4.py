import os
import sys
import json
import re
import datetime
import psycopg

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

DB_URL = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
FREE_DOMAINS = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'protonmail']
run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def get_conn():
    return psycopg.connect(DB_URL)

def main():
    print(f"=== FINAL BULK REPAIR START (RunID: {run_id}) ===")
    conn = get_conn()
    cur = conn.cursor()

    print("Phase 1: Loading companies and reference data...")
    cur.execute("SELECT company_id, company_name FROM companies")
    companies = cur.fetchall()
    company_map = {r[0]: r[1] for r in companies}
    co_name_to_id = {r[1].lower(): r[0] for r in companies if r[1]}

    class FakeDB:
        def query(self, *a, **kw): return self
        def filter(self, *a, **kw): return self
        def all(self): return []
        def count(self): return 0
    
    args = SimpleNamespace(
        dry_run=True, apply=False, minimum_confidence=70,
        batch_size=500, max_updates=500, all_recruiters=True
    )
    worker = EnrichmentWorker(FakeDB(), args)

    human_co_ids = set()
    for cid, cname in company_map.items():
        if cname and ' ' in cname and worker.is_human_name(cname, ''):
            human_co_ids.add(cid)
            
    placeholders = ','.join(str(x) for x in human_co_ids)

    print("Phase 2: Loading target cohort...")
    cur.execute(f"""
        SELECT recruiter_id, recruiter_name, company_id, email,
               is_active, needs_review, repair_reason, raw_data,
               metadata_json, source_job_id
        FROM recruiters
        WHERE company_id IN ({placeholders})
    """)
    cols = ['recruiter_id', 'recruiter_name', 'company_id', 'email',
            'is_active', 'needs_review', 'repair_reason', 'raw_data',
            'metadata_json', 'source_job_id']
    target_pool = [dict(zip(cols, row)) for row in cur.fetchall()]
    print(f"  Target pool size: {len(target_pool)}")

    print("Phase 3: Loading emails and building name index...")
    cur.execute("SELECT email, recruiter_id FROM recruiters WHERE email IS NOT NULL AND email != ''")
    existing_emails = {row[0].lower().strip(): row[1] for row in cur.fetchall()}

    cur.execute("""
        SELECT recruiter_id, recruiter_name, company_id, email
        FROM recruiters WHERE company_id IS NOT NULL
    """)
    name_index = {}
    for row in cur.fetchall():
        key = (row[2], row[1].lower().strip() if row[1] else "")
        if key not in name_index:
            name_index[key] = []
        name_index[key].append({'id': row[0], 'email': row[3]})

    # Phase 4: Categorizing in-memory
    print("Phase 4: Categorizing records and preparing updates...")
    backup_export = []
    updates = [] # list of tuple representing the update rows for bulk COPY

    counts = {'clean_dup': 0, 'corr_pair': 0, 'personal': 0, 'safe_swap': 0, 'orphan': 0}

    for rec in target_pool:
        rid = rec['recruiter_id']
        rec_name = rec['recruiter_name'] or ""
        cid = rec['company_id']
        misplaced_human = company_map.get(cid, "")
        misplaced_lower = misplaced_human.lower().strip()

        backup_export.append(rec)

        rec_name_lower = rec_name.lower().strip()
        rec_name_parts = re.split(r'[^a-zA-Z0-9]+', rec_name_lower)

        is_email_like = ('@' in rec_name or any(
            len(rec_name_lower.split('.')) > 1 and rec_name_lower.split('.')[-1] == t
            for t in ['com', 'net', 'org', 'io', 'tech', 'couk', 'uk']
        ))
        is_buzzword = any(
            w in rec_name_parts for w in
            ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners',
             'associates', 'staffing', 'consulting']
        )
        is_plan_a = (is_email_like or is_buzzword or not worker.is_human_name(rec_name, "", rec['email']))

        if is_plan_a:
            primary_email_string = rec_name.split(';')[0].strip()

            matched_id = None
            if "@" in primary_email_string:
                parts = primary_email_string.split('@')
                domain_part = parts[1].lower()
                clean_domain = re.sub(r"\.?(com|net|org|tech|io|couk|uk)$", "", domain_part)
                reconstructed_co_name = clean_domain.replace('-', ' ').title()
                matched_id = co_name_to_id.get(reconstructed_co_name.lower())

            new_email = primary_email_string if "@" in primary_email_string else None
            if new_email and "." not in new_email.split('@')[1]:
                dpart = new_email.split('@')[1]
                for tld in ['com', 'net', 'org', 'io', 'tech']:
                    if dpart.endswith(tld):
                        new_email = new_email.split('@')[0] + "@" + dpart[:-len(tld)] + "." + tld
                        break

            gen_email = new_email if (new_email and re.match(r"[^@]+@[^@]+\.[^@]+", new_email)) else None
            gen_email_lower = gen_email.lower().strip() if gen_email else ""

            best_dup = None
            best_dup_email = None

            if gen_email_lower and gen_email_lower in existing_emails:
                dup_id = existing_emails[gen_email_lower]
                if dup_id != rid:
                    best_dup = dup_id
                    best_dup_email = gen_email

            if not best_dup and matched_id:
                key = (matched_id, misplaced_lower)
                if key in name_index:
                    for d in name_index[key]:
                        if d['id'] != rid:
                            best_dup = d['id']
                            best_dup_email = d['email']
                            break

            if best_dup:
                dem = best_dup_email or ""
                is_clean = (
                    dem and str(dem).strip() != "" and
                    "@missing.local" not in dem and
                    "@invalid.local" not in dem and
                    "@example.com" not in dem
                )
                if is_clean:
                    counts['clean_dup'] += 1
                    updates.append((rid, rec_name, cid, rec['email'], True, 'merged_corrupted_duplicate_pending_review', rec['metadata_json']))
                else:
                    counts['corr_pair'] += 1
                    updates.append((rid, rec_name, cid, rec['email'], True, 'duplicate_pair_both_corrupted_pending_review', rec['metadata_json']))
            else:
                is_personal = False
                if "@" in primary_email_string:
                    dom = primary_email_string.split('@')[1].split('.')[0].lower()
                    if any(f in dom for f in FREE_DOMAINS):
                        is_personal = True

                if is_personal:
                    counts['personal'] += 1
                    updates.append((rid, rec_name, cid, rec['email'], True, 'repair_blocked_personal_email_domain', rec['metadata_json']))
                else:
                    counts['safe_swap'] += 1
                    meta = json.loads(rec['metadata_json']) if rec['metadata_json'] else {}
                    meta["pre_repair_corrupted"] = {
                        "recruiter_name": rec_name,
                        "company_id": cid,
                        "email": rec['email']
                    }
                    
                    target_email = rec['email']
                    if gen_email and gen_email_lower not in existing_emails:
                        target_email = gen_email
                        existing_emails[gen_email_lower] = rid
                        
                    updates.append((rid, misplaced_human, matched_id, target_email, rec['needs_review'], 'repaired_column_swap', json.dumps(meta)))
        else:
            counts['orphan'] += 1
            sjid = rec['source_job_id'] or 'location_workbook'
            updates.append((rid, rec_name, cid, rec['email'], True, f'unrecoverable_import_corruption:{sjid}', rec['metadata_json']))

    print("\n=== CATEGORIZATION RESULTS ===")
    print(f"  Clean Duplicate Artifacts: {counts['clean_dup']}")
    print(f"  Corrupted Duplicate Pairs: {counts['corr_pair']}")
    print(f"  Personal Domain Blocked  : {counts['personal']}")
    print(f"  Safely Repairable Swaps  : {counts['safe_swap']}")
    print(f"  Unrecoverable Orphans    : {counts['orphan']}")
    print(f"  Total                    : {len(updates)}")

    # Phase 5: Writing backup JSON
    print("\nPhase 5: Writing backup JSON...")
    backup_path = f"backend/backup_18774_cohort_{run_id}.json"
    with open(backup_path, "w", encoding="utf-8") as bf:
        json.dump(backup_export, bf, indent=2)
    print(f"  Backup written to {backup_path}")

    # Phase 6: Execute Bulk Update
    print("\nPhase 6: Executing Bulk Update...")
    try:
        # Create temp table
        cur.execute("""
            CREATE TEMP TABLE temp_repair (
                recruiter_id INT,
                recruiter_name VARCHAR(255),
                company_id INT,
                email VARCHAR(255),
                needs_review BOOLEAN,
                repair_reason VARCHAR(255),
                metadata_json TEXT
            ) ON COMMIT DROP;
        """)

        # Copy data
        with cur.copy("""
            COPY temp_repair (
                recruiter_id, recruiter_name, company_id, email,
                needs_review, repair_reason, metadata_json
            ) FROM STDIN
        """) as copy:
            for rid, name, co_id, email, needs_rev, reason, meta in updates:
                copy.write_row((rid, name, co_id, email, needs_rev, reason, meta))

        # Perform UPDATE
        cur.execute("""
            UPDATE recruiters r
            SET recruiter_name = t.recruiter_name,
                company_id = t.company_id,
                email = t.email,
                needs_review = t.needs_review,
                repair_reason = t.repair_reason,
                metadata_json = t.metadata_json,
                updated_at = now()
            FROM temp_repair t
            WHERE r.recruiter_id = t.recruiter_id;
        """)
        updated_rows = cur.rowcount
        print(f"  Successfully updated {updated_rows} rows in database.")

        conn.commit()
        print("  Transaction committed.")
    except Exception as e:
        conn.rollback()
        print(f"  [ERROR] Bulk update failed: {e}. Transaction rolled back.")
        conn.close()
        return

    # Phase 7: Verification
    print("\nPhase 7: Verifying results in database...")
    cur.execute("""
        SELECT repair_reason, count(1) 
        FROM recruiters 
        WHERE company_id IN (
            SELECT company_id FROM companies 
            WHERE company_name IS NOT NULL AND company_name LIKE '% %'
        ) OR repair_reason = 'repaired_column_swap'
        GROUP BY repair_reason
        ORDER BY count(1) DESC
    """)
    print("=== Database repair_reason breakdown ===")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    conn.close()
    print("=== REPAIR COMPLETE SUCCESSFULLY ===")

if __name__ == '__main__':
    main()
