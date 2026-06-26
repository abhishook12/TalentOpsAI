import json
from sqlalchemy import text
from app.database import SessionLocal
import re

db = SessionLocal()
records = json.load(open('96_records.json'))
bad_records = []
correct = 0

for r in records:
    rid = r['recruiter_id']
    old_email = r['original']
    new_email = r['final']
    name = db.execute(text(f"SELECT recruiter_name FROM recruiters WHERE recruiter_id={rid}")).scalar()
    
    is_bad = False
    reason = ''
    
    lower_name = name.lower() if name else ''
    
    bad_words = ['global', 'tech', 'vm', 'developers', 'resourcing', 'interactive', 'system', 'systems', 'staffing', 'partners', 'group', 'solutions']
    if not name or any(x in lower_name for x in bad_words):
        is_bad = True
        reason = 'Role-based or non-human name'
    elif old_email and len(old_email.strip()) > 0:
        is_bad = True
        reason = 'Overwrote existing non-empty email'
    elif new_email:
        local_part = new_email.split('@')[0]
        if local_part in ['iglobal', 'cdevelopers', 'left.vm', 'jcw.resourcing', 'stech', 'btech', 'tech']:
            is_bad = True
            reason = 'Role-based generated email'
        elif len(local_part) <= 2:
            is_bad = True
            reason = 'Malformed generated email (too short)'

    if is_bad:
        bad_records.append((rid, old_email, new_email, name, reason))
    else:
        correct += 1

# Two pass rollback to avoid Unique constraints
# Pass 1: Set to temp emails
for rid, old_email, new_email, name, reason in bad_records:
    db.execute(text("UPDATE recruiters SET email = :email WHERE recruiter_id = :rid"), {'email': f"temp_{rid}@temp.com", 'rid': rid})
db.commit()

# Pass 2: Set to true old emails
rolled_back = 0
for rid, old_email, new_email, name, reason in bad_records:
    try:
        db.execute(text("UPDATE recruiters SET email = :email WHERE recruiter_id = :rid"), {'email': old_email, 'rid': rid})
        db.execute(text("UPDATE enrichment_results SET overall_outcome = 'ROLLED_BACK' WHERE recruiter_id = :rid AND run_id = 'full-enrichment-20260623-221909'"), {'rid': rid})
        rolled_back += 1
        print(f"Rolled back {rid}: {name} ({new_email} -> {old_email}) - {reason}")
    except Exception as e:
        print(f"Failed to rollback {rid}: {e}")
        db.rollback()

db.commit()
db.close()
print(f"Rolled back {rolled_back} records. Kept {correct} records.")
