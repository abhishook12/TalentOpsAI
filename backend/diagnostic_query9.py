import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
try:
    results = {}
    results['total_recruiters'] = db.execute(text('SELECT count(*) FROM recruiters')).scalar()
    results['with_email'] = db.execute(text('SELECT count(*) FROM recruiters WHERE email IS NOT NULL AND email != \'\'')).scalar()
    results['with_phone'] = db.execute(text('SELECT count(*) FROM recruiters WHERE phone IS NOT NULL AND phone != \'\'')).scalar()
    results['with_location'] = db.execute(text('SELECT count(*) FROM recruiters WHERE location IS NOT NULL AND location != \'\'')).scalar()
    results['with_company'] = db.execute(text('SELECT count(*) FROM recruiters WHERE company_name IS NOT NULL AND company_name != \'\'')).scalar()
    results['with_alt_email'] = db.execute(text('SELECT count(*) FROM recruiters WHERE alternate_emails IS NOT NULL AND alternate_emails != \'\' AND alternate_emails != \'[]\'')).scalar()
    results['with_alt_phone'] = db.execute(text('SELECT count(*) FROM recruiters WHERE alternate_phones IS NOT NULL AND alternate_phones != \'\' AND alternate_phones != \'[]\'')).scalar()
    print(json.dumps(results, indent=2))
finally:
    db.close()
