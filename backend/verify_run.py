import os
import sys
from sqlalchemy import create_engine, text

sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv()

e = create_engine(os.getenv('DATABASE_URL'))
with e.connect() as c:
    print('--- LAST CHECKPOINT ---')
    run = c.execute(text("SELECT last_processed_id, inspected_count FROM enrichment_runs WHERE run_id='full-enrichment-20260623-221909'")).fetchone()
    print(f'Last Checkpoint ID: {run[0]}, Inspected: {run[1]}')
    
    print('--- MISSING/DUPLICATE RESULTS BEFORE CHECKPOINT ---')
    res = c.execute(text("SELECT recruiter_id, count(*) FROM enrichment_results WHERE run_id='full-enrichment-20260623-221909' AND recruiter_id <= :lid GROUP BY recruiter_id HAVING count(*) > 1"), {'lid': run[0]}).fetchall()
    print(f'Duplicates: {len(res)}')
    
    expected_res = c.execute(text("SELECT count(*) FROM recruiters WHERE recruiter_id <= :lid"), {'lid': run[0]}).scalar()
    actual_res = c.execute(text("SELECT count(*) FROM enrichment_results WHERE run_id='full-enrichment-20260623-221909' AND recruiter_id <= :lid"), {'lid': run[0]}).scalar()
    print(f'Expected: {expected_res}, Actual: {actual_res}, Missing: {expected_res - actual_res}')
    
    print('--- RESULTS AFTER CHECKPOINT (Partial Batch) ---')
    after_res = c.execute(text("SELECT count(*) FROM enrichment_results WHERE run_id='full-enrichment-20260623-221909' AND recruiter_id > :lid"), {'lid': run[0]}).scalar()
    print(f'Results after checkpoint: {after_res}')
