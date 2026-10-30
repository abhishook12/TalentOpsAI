import sys
sys.path.insert(0, r'C:\TalentOpsAI')
from backend.app.services.recruiter_store import recruiter_store

recruiter_store.reload()
res, cnt = recruiter_store.list_recruiters(date_filter='today', limit=5)
print(f"recruiter_store date_filter='today' SUCCESS! total_count={cnt}, results_len={len(res)}")
for r in res:
    print(f"  • {r.get('recruiter_name')} | Co: {r.get('company_name')} | Source: {r.get('data_source')} | Created: {r.get('created_at')}")
