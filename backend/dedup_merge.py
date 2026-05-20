"""
TalentOps AI — Smart Deduplication Merge Script
Merges recruiters where email2 of one == primary email of another.
Run with: python dedup_merge.py [--execute]  (default = dry run)
"""
import os, sys, re
from pathlib import Path
from dotenv import load_dotenv

# Load .env from same directory as this script
load_dotenv(Path(__file__).parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

import sqlalchemy as sa
from sqlalchemy import text

engine = sa.create_engine(DATABASE_URL)

DRY_RUN = "--execute" not in sys.argv

def is_better_name(n1, n2):
    """Returns True if n1 is a better-formatted name than n2."""
    def score(n):
        if not n: return 0
        # Proper capitalized words score higher
        words = n.strip().split()
        score = 0
        score += sum(1 for w in words if w and w[0].isupper() and w[1:].islower()) * 3
        score += len(words)  # more words = fuller name
        score -= 1 if n == n.lower() else 0  # all lower = bad
        score -= 1 if n == n.upper() else 0  # all upper = bad
        return score
    return score(n1) >= score(n2)

def clean_phone(p):
    if not p: return None
    digits = re.sub(r'[^\d]', '', p)
    if len(digits) >= 10:
        return digits[-10:]  # last 10 digits (strip country code for comparison)
    return None

def merge_phones(phones):
    """Given a list of phone strings, return up to 2 unique normalized phones."""
    seen, result = set(), []
    for p in phones:
        c = clean_phone(p)
        if c and c not in seen:
            seen.add(c)
            result.append(p.strip())  # keep original format
        if len(result) == 2:
            break
    return result

with engine.connect() as conn:
    # Step 1: Find all pairs where r1.email2 == r2.email (primary)
    rows = conn.execute(text("""
        SELECT
            r1.recruiter_id  AS id1,
            r1.recruiter_name AS name1,
            r1.email         AS email1,
            r1.email2        AS email2_1,
            r1.phone         AS phone1,
            r1.phone2        AS phone2_1,
            r1.linkedin      AS linkedin1,
            r1.specialization AS spec1,
            r1.notes         AS notes1,
            r1.company_id    AS company1,
            r2.recruiter_id  AS id2,
            r2.recruiter_name AS name2,
            r2.email         AS email2,
            r2.email2        AS email2_2,
            r2.phone         AS phone2,
            r2.phone2        AS phone2_2,
            r2.linkedin      AS linkedin2,
            r2.specialization AS spec2,
            r2.notes         AS notes2,
            r2.company_id    AS company2
        FROM recruiters r1
        JOIN recruiters r2
            ON LOWER(TRIM(r1.email2)) = LOWER(TRIM(r2.email))
            AND r1.recruiter_id != r2.recruiter_id
        WHERE r1.email2 IS NOT NULL AND TRIM(r1.email2) != ''
        ORDER BY r1.recruiter_id
    """)).mappings().all()

    print(f"\n{'='*70}")
    print(f"  TalentOps AI — Duplicate Merge  ({'DRY RUN' if DRY_RUN else 'LIVE EXECUTE'})")
    print(f"{'='*70}")
    print(f"  Found {len(rows)} duplicate pair(s) to merge\n")

    merge_plan = []

    for row in rows:
        # Decide which record to KEEP
        # Prefer: better name, work email (non-gmail/yahoo/hotmail/hotmail)
        personal_domains = {'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com','icloud.com','live.com','msn.com'}
        domain1 = row['email1'].split('@')[-1].lower() if '@' in str(row['email1']) else ''
        domain2 = row['email2'].split('@')[-1].lower() if '@' in str(row['email2']) else ''
        is1_personal = domain1 in personal_domains
        is2_personal = domain2 in personal_domains

        # Keep the one with work email if possible, else better name
        if is1_personal and not is2_personal:
            keep_id, del_id = row['id2'], row['id1']
            keep_email, keep_email2 = row['email2'], row['email1']
        elif is2_personal and not is1_personal:
            keep_id, del_id = row['id1'], row['id2']
            keep_email, keep_email2 = row['email1'], row['email2']
        elif is_better_name(row['name1'], row['name2']):
            keep_id, del_id = row['id1'], row['id2']
            keep_email, keep_email2 = row['email1'], row['email2']
        else:
            keep_id, del_id = row['id2'], row['id1']
            keep_email, keep_email2 = row['email2'], row['email1']

        # Determine which is the keep/del row
        if keep_id == row['id1']:
            keep_name = row['name1']
            all_phones = [row['phone1'], row['phone2_1'], row['phone2'], row['phone2_2']]
            keep_linkedin = row['linkedin1'] or row['linkedin2']
            keep_spec = row['spec1'] or row['spec2']
            keep_notes = '; '.join(filter(None, [row['notes1'], row['notes2']])) or None
            keep_company = row['company1'] or row['company2']
        else:
            keep_name = row['name2']
            all_phones = [row['phone2'], row['phone2_2'], row['phone1'], row['phone2_1']]
            keep_linkedin = row['linkedin2'] or row['linkedin1']
            keep_spec = row['spec2'] or row['spec1']
            keep_notes = '; '.join(filter(None, [row['notes2'], row['notes1']])) or None
            keep_company = row['company2'] or row['company1']

        # Merge phones (keep up to 2 unique)
        merged = merge_phones([p for p in all_phones if p])
        merged_phone  = merged[0] if len(merged) > 0 else None
        merged_phone2 = merged[1] if len(merged) > 1 else None

        plan = {
            'keep_id':    keep_id,
            'del_id':     del_id,
            'keep_name':  keep_name,
            'keep_email': keep_email,
            'keep_email2':keep_email2,
            'phone':      merged_phone,
            'phone2':     merged_phone2,
            'linkedin':   keep_linkedin,
            'specialization': keep_spec,
            'notes':      keep_notes,
            'company_id': keep_company,
        }
        merge_plan.append(plan)

        # Print preview
        print(f"  MERGE ──────────────────────────────────────────────────────")
        print(f"  KEEP   #{keep_id:<6} {keep_name} <{keep_email}>")
        print(f"  DELETE #{del_id:<6} {row['name1'] if del_id == row['id1'] else row['name2']} <{row['email1'] if del_id == row['id1'] else row['email2']}>")
        print(f"  Phones : {merged_phone} / {merged_phone2}")
        print()

    print(f"{'='*70}")
    print(f"  Total: {len(merge_plan)} merges, {len(merge_plan)} deletions")
    print(f"{'='*70}\n")

    if DRY_RUN:
        print("  ⚠  DRY RUN — no changes made.")
        print("  Run with --execute to apply.\n")
        sys.exit(0)

    # Step 2: Execute merges
    print("  Executing merges...")
    success, errors = 0, 0

    for plan in merge_plan:
        try:
            with conn.begin():
                # Update the kept record with merged data
                conn.execute(text("""
                    UPDATE recruiters SET
                        recruiter_name   = :name,
                        email            = :email,
                        email2           = :email2,
                        phone            = :phone,
                        phone2           = :phone2,
                        linkedin         = COALESCE(:linkedin, linkedin),
                        specialization   = COALESCE(:spec, specialization),
                        notes            = COALESCE(:notes, notes),
                        company_id       = COALESCE(:company_id, company_id)
                    WHERE recruiter_id = :keep_id
                """), {
                    'name':       plan['keep_name'],
                    'email':      plan['keep_email'],
                    'email2':     plan['keep_email2'],
                    'phone':      plan['phone'],
                    'phone2':     plan['phone2'],
                    'linkedin':   plan['linkedin'],
                    'spec':       plan['specialization'],
                    'notes':      plan['notes'],
                    'company_id': plan['company_id'],
                    'keep_id':    plan['keep_id'],
                })
                # Delete the duplicate record
                conn.execute(text("DELETE FROM recruiters WHERE recruiter_id = :del_id"),
                             {'del_id': plan['del_id']})
            print(f"  ✓ Merged #{plan['keep_id']} ← #{plan['del_id']}")
            success += 1
        except Exception as e:
            print(f"  ✗ Error merging #{plan['keep_id']} ← #{plan['del_id']}: {e}")
            errors += 1

    print(f"\n  Done. {success} merged, {errors} errors.")
    print(f"  New total recruiters: ", end="")
    total = conn.execute(text("SELECT COUNT(*) FROM recruiters")).scalar()
    print(total)
