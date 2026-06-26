import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
results = {}

try:
    # 1. Pipeline Design & Checkpoint
    results['checkpoint_id_meaning'] = 'Recruiter ID (primary key of recruiters table)'
    
    # 2. Check 96 applied updates from enrichment_outcomes
    updates = db.execute(text('SELECT count(*) FROM enrichment_outcomes WHERE run_id = \'full-enrichment-20260623-221909\' AND status = \'applied\'')).scalar()
    results['applied_updates_verified'] = updates
    
    # 3. Top rejection reasons
    rejections = db.execute(text('SELECT reason, count(*) as cnt FROM enrichment_outcomes WHERE run_id = \'full-enrichment-20260623-221909\' AND status = \'rejected\' GROUP BY reason ORDER BY cnt DESC LIMIT 10')).fetchall()
    results['top_rejections'] = [{'reason': r[0], 'count': r[1]} for r in rejections]
    
    # 4. Top skip reasons
    skips = db.execute(text('SELECT reason, count(*) as cnt FROM enrichment_outcomes WHERE run_id = \'full-enrichment-20260623-221909\' AND status = \'skipped\' GROUP BY reason ORDER BY cnt DESC LIMIT 10')).fetchall()
    results['top_skips'] = [{'reason': r[0], 'count': r[1]} for r in skips]
    
    # 5. Get 20 updated records
    samples = db.execute(text('SELECT target_id, previous_data, new_data, fields_changed, source_used, confidence_score, updated_at FROM enrichment_outcomes WHERE run_id = \'full-enrichment-20260623-221909\' AND status = \'applied\' LIMIT 20')).fetchall()
    results['samples'] = [{'recruiter_id': s[0], 'previous_values': s[1], 'new_values': s[2], 'fields_changed': s[3], 'source_used': s[4], 'confidence': s[5], 'updated_at': str(s[6])} for s in samples]
    
    # 6. Global stats
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
