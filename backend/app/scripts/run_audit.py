import os
import sys
import json
from collections import Counter
from sqlalchemy import func, text

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import SessionLocal
from app.models.models import Recruiter, Company, UploadJob

def run_audit():
    db = SessionLocal()
    report = {}
    
    # 1. Total recruiters
    report['Total Recruiters'] = db.query(func.count(Recruiter.recruiter_id)).scalar()
    
    # 2. Total companies
    report['Total Companies'] = db.query(func.count(Company.company_id)).scalar()
    
    # 3. Total states detected
    states = db.execute(text("SELECT DISTINCT state FROM recruiters WHERE state IS NOT NULL AND state != ''")).fetchall()
    report['Total States Detected'] = len(states)
    report['States List'] = [s[0] for s in states]
    
    # 4. Recruiters with real email
    real_emails = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE email NOT LIKE '%@missing.local%' AND email IS NOT NULL")).scalar()
    report['Recruiters with Real Email'] = real_emails
    
    # 5. Recruiters with phone
    phones = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL AND phone != ''")).scalar()
    report['Recruiters with Phone'] = phones
    
    # 6. Recruiters with company
    has_comp = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL")).scalar()
    report['Recruiters with Company'] = has_comp
    
    # 7. Recruiters with state
    has_state = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != ''")).scalar()
    report['Recruiters with State'] = has_state
    
    # 8. Recruiters with location
    has_loc = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE location IS NOT NULL AND location != ''")).scalar()
    report['Recruiters with Location'] = has_loc
    
    # 9, 10, 11, 12. Multiple emails/phones
    report['Recruiters with 2+ emails'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE email2 IS NOT NULL AND email2 != ''")).scalar()
    report['Recruiters with 2+ phones'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE phone2 IS NOT NULL AND phone2 != ''")).scalar()
    report['Recruiters with 4 emails'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE email4 IS NOT NULL AND email4 != ''")).scalar()
    report['Recruiters with 4 phones'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE phone4 IS NOT NULL AND phone4 != ''")).scalar()
    
    # 13, 14. Metadata/Raw
    report['Recruiters with metadata_json'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE metadata_json IS NOT NULL")).scalar()
    report['Recruiters with raw_data'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE raw_data IS NOT NULL")).scalar()
    
    # 15. Needs review
    report['Needs Review Count'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE needs_review = true")).scalar()
    
    # 17. Empty/invalid name count
    report['Empty/Invalid Name Count'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE recruiter_name IS NULL OR recruiter_name = '' OR recruiter_name = 'Unknown'")).scalar()
    
    # 18. Empty company count
    report['Empty Company Count'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE company_id IS NULL")).scalar()
    
    # 19. Empty state count
    report['Empty State Count'] = report['Total Recruiters'] - has_state
    
    # 20. Bad email count
    report['Bad/Missing Email Count'] = db.execute(text("SELECT COUNT(*) FROM recruiters WHERE email LIKE '%@missing.local%'")).scalar()
    
    # 22. Duplicate email count
    dup_emails = db.execute(text("SELECT email, COUNT(*) FROM recruiters GROUP BY email HAVING COUNT(*) > 1 AND email NOT LIKE '%@missing.local%'")).fetchall()
    report['Duplicate Real Email Count'] = len(dup_emails)
    
    # 23. Duplicate phone count
    dup_phones = db.execute(text("SELECT phone, COUNT(*) FROM recruiters GROUP BY phone HAVING COUNT(*) > 1 AND phone IS NOT NULL AND phone != ''")).fetchall()
    report['Duplicate Phone Count'] = len(dup_phones)
    
    # 24. Same name + same company count
    same_nc = db.execute(text("SELECT recruiter_name, company_id, COUNT(*) FROM recruiters WHERE recruiter_name != 'Unknown' GROUP BY recruiter_name, company_id HAVING COUNT(*) > 1")).fetchall()
    report['Same Name + Company Count'] = len(same_nc)
    
    # 25. Companies with no state/location
    comp_no_loc = db.execute(text("SELECT COUNT(*) FROM companies WHERE (location IS NULL OR location = '') AND (state IS NULL OR state = '')")).scalar()
    report['Companies with No State/Location'] = comp_no_loc
    
    # 27. Import jobs that failed or 0 rows
    jobs_fail = db.execute(text("SELECT COUNT(*) FROM upload_jobs WHERE status = 'failed' OR inserted_rows = 0")).scalar()
    report['Failed/0-row Import Jobs'] = jobs_fail

    # States distribution
    state_dist = db.execute(text("SELECT state, COUNT(*) FROM recruiters WHERE state IS NOT NULL AND state != '' GROUP BY state")).fetchall()
    report['State Distribution'] = {row[0]: row[1] for row in state_dist}

    print(json.dumps(report, indent=2))
    db.close()

if __name__ == '__main__':
    run_audit()
