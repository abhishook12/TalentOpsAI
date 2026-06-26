"""
Batched repair script using raw psycopg3 (no ORM).
Commits in batches of 100 with fresh connections to avoid Supabase SSL drops.
Handles email uniqueness collisions.
"""
import os
import sys
import json
import datetime
import re
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace

import psycopg

DB_URL = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require'
FREE_DOMAINS = ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol', 'protonmail']
BATCH_SIZE = 50
MAX_RETRIES = 5
run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def get_conn():
    return psycopg.connect(DB_URL)


def fetch_with_retry(fn, label="query"):
    for attempt in range(MAX_RETRIES):
        try:
            conn = get_conn()
            result = fn(conn)
            conn.close()
            return result
        except Exception as e:
            wait = min(2 ** attempt, 16)
            print(f"  [{label}] Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {label}")


def main():
    print(f"=== BATCHED REPAIR START (RunID: {run_id}) ===")
    print(f"Batch size: {BATCH_SIZE}")

    # --- Phase 1: Load reference data ---
    print("\nPhase 1: Loading reference data...")

    def load_companies(conn):
        cur = conn.cursor()
        cur.execute("SELECT company_id, company_name FROM companies")
        return cur.fetchall()
    
    companies = fetch_with_retry(load_companies, "companies")
    company_map = {r[0]: r[1] for r in companies}
    co_name_to_id = {r[1].lower(): r[0] for r in companies if r[1]}
    print(f"  Loaded {len(companies)} companies")

    # Build is_human_name checker (need ORM just for this utility)
    from app.database import engine as _unused
    from sqlalchemy.orm import Session as SASession
    from sqlalchemy import create_engine
    # We only need the worker for is_human_name, not for DB access
    # Create a minimal mock
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

    # Identify human-named company IDs
    human_co_ids = set()
    for cid, cname in company_map.items():
        if cname and ' ' in cname and worker.is_human_name(cname, ''):
            human_co_ids.add(cid)
    print(f"  Found {len(human_co_ids)} human-named company IDs")

    # Load target pool (only IDs + needed fields, no ORM)
    def load_target(conn):
        cur = conn.cursor()
        placeholders = ','.join(str(x) for x in human_co_ids)
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
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    target_pool = fetch_with_retry(load_target, "target_pool")
    print(f"  Target pool: {len(target_pool)} records")

    # Load all existing emails for collision detection
    def load_emails(conn):
        cur = conn.cursor()
        cur.execute("SELECT email, recruiter_id FROM recruiters WHERE email IS NOT NULL AND email != ''")
        return {row[0].lower().strip(): row[1] for row in cur.fetchall()}

    existing_emails = fetch_with_retry(load_emails, "emails")
    print(f"  Loaded {len(existing_emails)} existing emails")

    # Load name index for duplicate detection
    def load_name_idx(conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT recruiter_id, recruiter_name, company_id, email
            FROM recruiters WHERE company_id IS NOT NULL
        """)
        idx = {}
        for row in cur.fetchall():
            key = (row[2], row[1].lower().strip() if row[1] else "")
            if key not in idx:
                idx[key] = []
            idx[key].append({'id': row[0], 'email': row[3]})
        return idx

    name_index = fetch_with_retry(load_name_idx, "name_index")
    print(f"  Built name index: {len(name_index)} unique (company, name) pairs")

    # --- Phase 2: Categorize all records in memory ---
    print("\nPhase 2: Categorizing records...")

    backup_export = []
    updates = []  # list of (recruiter_id, dict_of_field_updates)

    counts = {'clean_dup': 0, 'corr_pair': 0, 'personal': 0, 'safe_swap': 0, 'orphan': 0}

    for rec in target_pool:
        rid = rec['recruiter_id']
        rec_name = rec['recruiter_name'] or ""
        cid = rec['company_id']
        misplaced_human = company_map.get(cid, "")
        misplaced_lower = misplaced_human.lower().strip()

        backup_export.append({
            "recruiter_id": rid,
            "recruiter_name": rec_name,
            "company_id": cid,
            "company_name": misplaced_human,
            "email": rec['email'],
            "is_active": rec['is_active'],
            "needs_review": rec['needs_review'],
            "repair_reason": rec['repair_reason'],
            "raw_data": rec['raw_data'],
            "metadata_json": rec['metadata_json']
        })

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
        is_plan_a = (is_email_like or is_buzzword or not worker.is_human_name(rec_name, ""))

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
                    updates.append((rid, {
                        'needs_review': True,
                        'repair_reason': 'merged_corrupted_duplicate_pending_review'
                    }))
                else:
                    counts['corr_pair'] += 1
                    updates.append((rid, {
                        'needs_review': True,
                        'repair_reason': 'duplicate_pair_both_corrupted_pending_review'
                    }))
            else:
                is_personal = False
                if "@" in primary_email_string:
                    dom = primary_email_string.split('@')[1].split('.')[0].lower()
                    if any(f in dom for f in FREE_DOMAINS):
                        is_personal = True

                if is_personal:
                    counts['personal'] += 1
                    updates.append((rid, {
                        'needs_review': True,
                        'repair_reason': 'repair_blocked_personal_email_domain'
                    }))
                else:
                    counts['safe_swap'] += 1

                    meta = json.loads(rec['metadata_json']) if rec['metadata_json'] else {}
                    meta["pre_repair_corrupted"] = {
                        "recruiter_name": rec_name,
                        "company_id": cid,
                        "email": rec['email']
                    }

                    upd = {
                        'recruiter_name': misplaced_human,
                        'company_id': matched_id,
                        'metadata_json': json.dumps(meta),
                        'repair_reason': 'repaired_column_swap'
                    }

                    if gen_email and gen_email_lower not in existing_emails:
                        upd['email'] = gen_email
                        existing_emails[gen_email_lower] = rid

                    updates.append((rid, upd))
        else:
            counts['orphan'] += 1
            sjid = rec['source_job_id'] or 'location_workbook'
            updates.append((rid, {
                'needs_review': True,
                'repair_reason': f'unrecoverable_import_corruption:{sjid}'
            }))

    total_cat = sum(counts.values())
    print(f"\n=== CATEGORIZATION RESULTS ===")
    print(f"  Clean Duplicate Artifacts: {counts['clean_dup']}")
    print(f"  Corrupted Duplicate Pairs: {counts['corr_pair']}")
    print(f"  Personal Domain Blocked  : {counts['personal']}")
    print(f"  Safely Repairable Swaps  : {counts['safe_swap']}")
    print(f"  Unrecoverable Orphans    : {counts['orphan']}")
    print(f"  Total                    : {total_cat}")
    assert total_cat == len(target_pool), f"Count mismatch: {total_cat} vs {len(target_pool)}"

    # --- Phase 3: Write backup ---
    print("\nPhase 3: Writing backup...")
    backup_path = f"backend/backup_18774_cohort_{run_id}.json"
    with open(backup_path, "w", encoding="utf-8") as bf:
        json.dump(backup_export, bf, indent=2)
    print(f"  [OK] Backup: {backup_path} ({len(backup_export)} rows)")

    # --- Phase 4: Commit in batches ---
    print(f"\nPhase 4: Committing {len(updates)} updates in batches of {BATCH_SIZE}...")

    committed = 0
    failed_batches = []
    total_batches = (len(updates) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_start in range(0, len(updates), BATCH_SIZE):
        batch = updates[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        success = False
        for attempt in range(MAX_RETRIES):
            try:
                conn = get_conn()
                cur = conn.cursor()

                for rid, fields in batch:
                    set_parts = []
                    vals = []
                    for k, v in fields.items():
                        set_parts.append(f"{k} = %s")
                        vals.append(v)
                    set_parts.append("updated_at = now()")
                    vals.append(rid)

                    sql = f"UPDATE recruiters SET {', '.join(set_parts)} WHERE recruiter_id = %s"
                    cur.execute(sql, vals)

                conn.commit()
                conn.close()
                committed += len(batch)
                success = True

                if batch_num % 20 == 0 or batch_num == total_batches:
                    print(f"  Batch {batch_num}/{total_batches}: {committed}/{len(updates)} committed")
                break
            except Exception as e:
                try:
                    conn.close()
                except:
                    pass
                wait = min(2 ** attempt, 16)
                print(f"  Batch {batch_num} attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)

        if not success:
            failed_batches.append((batch_num, batch_start, str(e)))
            print(f"  [FAIL] Batch {batch_num} PERMANENTLY FAILED!")

    # --- Phase 5: Verification ---
    print(f"\n=== POST-REPAIR VERIFICATION ===")

    def verify(conn):
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM recruiters")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*) FROM recruiters
            WHERE repair_reason IN (
                'merged_corrupted_duplicate_pending_review',
                'duplicate_pair_both_corrupted_pending_review',
                'repaired_column_swap',
                'repair_blocked_personal_email_domain'
            ) OR repair_reason LIKE 'unrecoverable_import_corruption%%'
        """)
        tagged = cur.fetchone()[0]

        cur.execute("""
            SELECT count(*) FROM recruiters 
            WHERE repair_reason = 'repaired_column_swap'
            AND (email LIKE '%%@missing.local%%' OR email LIKE '%%@invalid.local%%')
        """)
        bad_emails = cur.fetchone()[0]
        return total, tagged, bad_emails

    total, tagged, bad_emails = fetch_with_retry(verify, "verification")
    print(f"  1. Total Recruiters: {total} (Expected: 91333)")
    print(f"  2. Total Tagged/Repaired: {tagged}")
    print(f"  3. Repaired rows with placeholder emails: {bad_emails} (Expected: 0)")
    print(f"\n  Committed: {committed}/{len(updates)}")
    if failed_batches:
        print(f"  FAILED BATCHES: {len(failed_batches)}")
        for fb in failed_batches:
            print(f"    Batch {fb[0]} (offset {fb[1]}): {fb[2]}")
    else:
        print(f"  ALL BATCHES COMMITTED SUCCESSFULLY!")

    print(f"\n=== REPAIR COMPLETE ===")


if __name__ == "__main__":
    main()
