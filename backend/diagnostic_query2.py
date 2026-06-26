import json
from sqlalchemy import text
from app.database import SessionLocal
db = SessionLocal()
results = {}
try:
    results['applied_updates_verified'] = db.execute(text('SELECT count(*) FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND overall_outcome = \'APPLIED\'')).scalar()
    
    rejections = db.execute(text('SELECT rejection_reason, count(*) as cnt FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND overall_outcome = \'REJECTED\' GROUP BY rejection_reason ORDER BY cnt DESC LIMIT 10')).fetchall()
    results['top_rejections'] = [{'reason': r[0], 'count': r[1]} for r in rejections]
    
    skips = db.execute(text('SELECT skip_reason, count(*) as cnt FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND overall_outcome = \'SKIPPED\' GROUP BY skip_reason ORDER BY cnt DESC LIMIT 10')).fetchall()
    results['top_skips'] = [{'reason': r[0], 'count': r[1]} for r in skips]
    
    samples = db.execute(text('SELECT recruiter_id, details_json, updated_at FROM enrichment_results WHERE run_id = \'full-enrichment-20260623-221909\' AND overall_outcome = \'APPLIED\' LIMIT 20')).fetchall()
    results['samples'] = [{'recruiter_id': s[0], 'details': s[1], 'updated_at': str(s[2])} for s in samples]
    
    print(json.dumps(results, indent=2))
finally:
    db.close()
