import os
import sys
sys.path.append('C:/TalentOpsAI/backend')

from app.services.recruiter_store import recruiter_store

print(f"Total count loaded: {recruiter_store.total_count}")

print("Testing list_recruiters...")
results, total = recruiter_store.list_recruiters(limit=2)
print(f"Found {total}, returning {len(results)}")
for r in results:
    print(f" - {r.get('recruiter_name')} ({r.get('email')}) - Company ID: {r.get('company_id')}")

print("\nTesting search...")
search_res = recruiter_store.search(q="john", limit=2)
for r in search_res:
    print(f" - {r.get('recruiter_name')} ({r.get('email')}) - Score: {r.get('relevance_score')}")

print("\nTesting company_recruiter_counts...")
counts = recruiter_store.company_recruiter_counts()
print(f"Found counts for {len(counts)} companies. Example: {list(counts.items())[:3]}")
