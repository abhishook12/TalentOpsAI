import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import SessionLocal
from sqlalchemy import text
import json
from datetime import datetime

db = SessionLocal()

def default_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)

def dump_to_file(filename, query, params=None):
    res = db.execute(text(query), params or {}).mappings().all()
    with open(f"C:/TalentOpsAI/backend/backups/repair-run-20260624-001/{filename}", "w") as f:
        json.dump([dict(r) for r in res], f, indent=2, default=default_converter)
    print(f"Backed up {len(res)} rows to {filename}")

# Backup recruiter records
dump_to_file("recruiters.json", """
    SELECT r.recruiter_id, r.recruiter_name, r.email, r.email_status, r.email_confidence, r.updated_at, c.company_name
    FROM recruiters r 
    LEFT JOIN companies c ON r.company_id = c.company_id
    WHERE r.recruiter_name IN ('Vito Scutero', 'Dennys Hernandez', 'Caren Galit', 'Freddy Engel', 'Fred Engel')
    AND c.company_name = 'TekPartners'
""")

# Backup audit records
dump_to_file("audit_records.json", """
    SELECT a.* 
    FROM enrichment_audit a
    JOIN recruiters r ON a.recruiter_id = r.recruiter_id
    LEFT JOIN companies c ON r.company_id = c.company_id
    WHERE c.company_name = 'TekPartners'
""")

# Backup company patterns
dump_to_file("company_patterns.json", """
    SELECT p.*
    FROM company_email_patterns p
    JOIN companies c ON p.company_id = c.company_id
    WHERE c.company_name = 'TekPartners'
""")
