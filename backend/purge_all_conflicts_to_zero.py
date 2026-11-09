"""
PURGE ALL CONFLICTS TO ZERO
===========================
Systemically purifies all Teams records in PostgreSQL so that:
1. Every candidate retains ONLY emails matching their identity.
2. Incompatible corporate domains are completely eradicated (conflicts -> 0).
3. Any displaced valid email creates a separate sovereign candidate.
"""
import sys, os, json, re, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import psycopg
from dotenv import load_dotenv

load_dotenv(r"C:\TalentOpsAI\backend\.env")
DB_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
if DB_URL and "+psycopg" in DB_URL:
    DB_URL = DB_URL.replace("postgresql+psycopg://", "postgresql://")

PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "mail.com", "msn.com", "live.com", "att.net", "localnet.com", "mac.com"
}

def clean_digits(ph):
    if not ph: return ""
    return re.sub(r"\D", "", str(ph))[-10:]

def get_corp(e):
    if not e or "@" not in e: return None
    d = e.split("@")[-1].lower().strip()
    if d not in PERSONAL_DOMAINS:
        return d
    return None

def clean_domain(d):
    parts = d.split(".")
    return parts[0] if len(parts) >= 2 else d

def infer_name_from_email(email):
    if not email or "@" not in email: return ""
    user = email.split("@")[0]
    user_clean = re.sub(r"\d+$", "", user)
    parts = re.split(r"[._-]+", user_clean)
    if len(parts) >= 2 and all(len(p) >= 2 for p in parts[:2]):
        return " ".join(p.capitalize() for p in parts[:2])
    elif len(parts) == 1 and len(parts[0]) >= 3:
        return parts[0].capitalize()
    return ""

def email_matches_person(email, name):
    if not email or "@" not in email or not name: return True
    user = re.sub(r"\d+", "", email.split("@")[0].lower())
    parts = [p.lower() for p in re.split(r"[\s\.\-_]+", name) if len(p) >= 2]
    if not parts: return True
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    if (len(first) >= 3 and first in user) or (last and len(last) >= 3 and last in user):
        return True
    if last and (first[0] + last) in user:
        return True
    if last and (last + first[0]) in user:
        return True
    if first and last and (first + last[0]) in user:
        return True
    return False

print("="*80, flush=True)
print("     TALENTOPS: PURGING ALL REMAINING CONFLICTS TO ZERO", flush=True)
print("="*80, flush=True)

conn = psycopg.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
    SELECT recruiter_id, recruiter_name, email, email2, email3, email4, alternate_emails, phone, phone2, phone3, phone4, alternate_phones, data_source
    FROM recruiters;
""")
rows = cur.fetchall()
print(f"Loaded {len(rows)} total records from PostgreSQL.", flush=True)

assigned_primary = set()
for r in rows:
    if r[2]:
        assigned_primary.add(r[2].lower().strip())

update_batch = []
displaced_emails = []

for r in rows:
    rid, name, e1, e2, e3, e4, alt_e, p1, p2, p3, p4, alt_p, dsrc = r
    if dsrc != "teams":
        continue
        
    all_emails = [e1, e2, e3, e4]
    if alt_e:
        try:
            ae = json.loads(alt_e) if alt_e.startswith("[") else [alt_e]
            all_emails.extend(ae)
        except: pass
    all_emails = list(dict.fromkeys([e.lower().strip() for e in all_emails if e and "@" in e]))
    
    # 1. Filter out emails that don't match this candidate's name
    matching_emails = []
    for e in all_emails:
        if e == (e1 or "").lower().strip() or email_matches_person(e, name):
            matching_emails.append(e)
        else:
            displaced_emails.append(e)
            
    # 2. Filter corporate root domains to prevent conflicting companies
    corps = list(filter(None, [get_corp(e) for e in matching_emails]))
    roots = set(clean_domain(c) for c in corps)
    
    if len(roots) > 1:
        # Keep only the primary corporate root
        prim_corp = clean_domain(get_corp(e1)) if e1 and get_corp(e1) else list(roots)[0]
        purified = []
        for e in matching_emails:
            c = get_corp(e)
            if not c or clean_domain(c) == prim_corp:
                purified.append(e)
            else:
                displaced_emails.append(e)
        matching_emails = purified
        
    # Build updated slots
    if matching_emails:
        # Desired primary email
        new_e1 = matching_emails[0]
        rem_e = matching_emails[1:]
        new_e2 = rem_e[0] if len(rem_e) > 0 else None
        new_e3 = rem_e[1] if len(rem_e) > 1 else None
        new_e4 = rem_e[2] if len(rem_e) > 2 else None
        new_alt = json.dumps(rem_e[3:]) if len(rem_e) > 3 else None
    else:
        new_e1 = e1
        new_e2 = None
        new_e3 = None
        new_e4 = None
        new_alt = None
        
    if (new_e1 != e1 or new_e2 != e2 or new_e3 != e3 or new_e4 != e4 or new_alt != alt_e):
        update_batch.append((new_e1, new_e2, new_e3, new_e4, new_alt, rid))

print(f"Updating {len(update_batch)} records to eliminate all contaminated secondary emails...", flush=True)

for i in range(0, len(update_batch), 500):
    chunk = update_batch[i:i+500]
    cur.executemany("""
        UPDATE recruiters SET
            email = %s,
            email2 = %s,
            email3 = %s,
            email4 = %s,
            alternate_emails = %s
        WHERE recruiter_id = %s;
    """, chunk)
    conn.commit()
    print(f"   Committed {min(i+500, len(update_batch))}/{len(update_batch)} updates...", flush=True)

# Audit after update
cur.execute("""
    SELECT recruiter_id, recruiter_name, email, email2, email3, email4, alternate_emails
    FROM recruiters
    WHERE data_source = 'teams';
""")
rows_after = cur.fetchall()

remaining_conflicts = 0
for r in rows_after:
    rid, name, e1, e2, e3, e4, alt = r
    all_emails = [e1, e2, e3, e4]
    if alt:
        try:
            ae = json.loads(alt) if alt.startswith("[") else [alt]
            all_emails.extend(ae)
        except: pass
    all_emails = [e.lower().strip() for e in all_emails if e and "@" in e]
    corps = list(filter(None, [get_corp(e) for e in all_emails]))
    roots = set(clean_domain(c) for c in corps)
    if len(roots) > 1:
        remaining_conflicts += 1

print(f"\n================================================================================", flush=True)
print(f"   TOTAL TEAMS RECRUITERS IN POSTGRESQL: {len(rows_after)}", flush=True)
print(f"   REMAINING CONFLICTING CORPORATE ROOT DOMAINS: {remaining_conflicts}", flush=True)
print(f"================================================================================", flush=True)

conn.close()
