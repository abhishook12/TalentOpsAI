import json
from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()
run_id = 'full-enrichment-20260623-221909'

with open('96_records.json', 'r') as f:
    records = json.load(f)

initial_map = {r['recruiter_id']: r['original'] for r in records}
final_map = {r['recruiter_id']: r['final'] for r in records}

bad_words = ['global', 'tech', 'vm', 'developers', 'resourcing', 'interactive', 'system', 'systems', 'staffing', 'partners', 'group', 'solutions']
bad_locals = ['iglobal', 'cdevelopers', 'left.vm', 'jcw.resourcing', 'stech', 'btech', 'tech', 'admin', 'info']

rolled_backs = db.execute(text(f"SELECT recruiter_id, created_at FROM enrichment_audit WHERE run_id = '{run_id}' AND action = 'rolled_back'")).fetchall()
rolled_map = {r[0]: r[1] for r in rolled_backs}

recruiters = db.execute(text(f"SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.email FROM recruiters r LEFT JOIN companies c ON r.company_id = c.company_id WHERE r.recruiter_id IN ({','.join([str(x) for x in initial_map.keys()])})")).fetchall()

classification_counts = {'confirmed correct': 0, 'likely correct': 0, 'uncertain': 0, 'clearly incorrect': 0}
export_rows = []
exact_matches = 0
mismatches = 0
missing_audit = 0
null_restorations = 0

print("--- ITEM 1, 2, 3: ROLLBACKS ---")
for rid, name, company, current_email in recruiters:
    old_email = initial_map.get(rid)
    gen_email = final_map.get(rid)
    
    if rid not in rolled_map:
        missing_audit += 1
        ts = "N/A"
    else:
        ts = rolled_map[rid]
    
    classification = 'clearly incorrect'
    reason = ''
    lower_name = (name or '').lower()
    
    if not name or any(x in lower_name for x in bad_words):
        reason = 'Role-based or non-human name'
    elif old_email and len(old_email.strip()) > 0:
        reason = 'Overwrote existing non-empty email'
    elif gen_email:
        local_part = gen_email.split('@')[0] if '@' in gen_email else gen_email
        if local_part in bad_locals:
            reason = 'Role-based generated email'
        elif len(local_part) <= 2:
            reason = 'Malformed generated email (too short)'
    
    if not reason:
        # None of the rules hit?
        classification = 'likely correct'
        reason = 'Matched but reverted anyway for safety'
        
    classification_counts[classification] += 1
    
    export_rows.append(f"{rid} | {name} | {company} | {old_email} | {gen_email} | ROLLED_BACK | {classification} | {reason} | {ts}")
    
    if current_email == old_email:
        exact_matches += 1
        if not current_email:
            null_restorations += 1
    else:
        mismatches += 1
        print(f"Mismatch: RID {rid} Expected: {old_email} Found: {current_email}")

print("Counts:", classification_counts)
print("Rows verified:", len(export_rows))
print("Exact matches:", exact_matches)
print("Mismatches:", mismatches)
print("Null restorations:", null_restorations)
print("Missing audit:", missing_audit)

print("\n--- EXPORT ---")
print("ID | Name | Company | Old | New | Status | Class | Reason | Audit Time")
for row in export_rows: # Print first 10
    print(row)
print("... (total 96)")

print("\n--- ITEM 9: COUNTERS ---")
after_cp = 39961
results = db.execute(text(f"SELECT overall_outcome, count(*) FROM enrichment_results WHERE run_id = '{run_id}' AND recruiter_id >= {after_cp} GROUP BY overall_outcome")).fetchall()
print("Results:", results)

audits = db.execute(text(f"SELECT action, count(*) FROM enrichment_audit WHERE run_id = '{run_id}' AND recruiter_id >= {after_cp} GROUP BY action")).fetchall()
print("Audits:", audits)

print("\n--- ITEM 10: 20 RECORDS ---")
fills = db.execute(text(f"SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.email, a.final_value, 0 AS confidence FROM enrichment_audit a JOIN recruiters r ON a.recruiter_id = r.recruiter_id LEFT JOIN companies c ON r.company_id = c.company_id WHERE a.run_id = '{run_id}' AND a.recruiter_id >= {after_cp} AND a.action = 'applied' LIMIT 5")).fetchall()
print("Fills:", fills)

pendings = db.execute(text(f"SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.email, p.proposed_value, p.confidence FROM enrichment_proposals p JOIN recruiters r ON p.recruiter_id = r.recruiter_id LEFT JOIN companies c ON r.company_id = c.company_id WHERE p.run_id = '{run_id}' AND p.recruiter_id >= {after_cp} LIMIT 5")).fetchall()
print("Pendings:", pendings)

rejects = db.execute(text(f"SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.email, e.overall_outcome FROM enrichment_results e JOIN recruiters r ON e.recruiter_id = r.recruiter_id LEFT JOIN companies c ON r.company_id = c.company_id WHERE e.run_id = '{run_id}' AND e.recruiter_id >= {after_cp} AND e.overall_outcome LIKE 'REJECTED%' LIMIT 5")).fetchall()
print("Rejects:", rejects)

skips = db.execute(text(f"SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.email, e.overall_outcome FROM enrichment_results e JOIN recruiters r ON e.recruiter_id = r.recruiter_id LEFT JOIN companies c ON r.company_id = c.company_id WHERE e.run_id = '{run_id}' AND e.recruiter_id >= {after_cp} AND e.overall_outcome LIKE 'SKIPPED%' LIMIT 5")).fetchall()
print("Skips:", skips)

db.close()
