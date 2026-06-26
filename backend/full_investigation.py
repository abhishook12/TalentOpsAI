import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from enrich_recruiter_contacts import EnrichmentWorker
from types import SimpleNamespace
from collections import Counter

db = SessionLocal()
args = SimpleNamespace(
    dry_run=True, apply=False, minimum_confidence=70, 
    batch_size=500, max_updates=500, all_recruiters=True
)
worker = EnrichmentWorker(db, args)

total_recs = db.query(Recruiter).count()
print(f"Total records in table: {total_recs}")

all_companies = db.query(Company).all()
human_company_ids = set()
for c in all_companies:
    co = c.company_name or ""
    if co and ' ' in co and worker.is_human_name(co, ''):
        human_company_ids.add(c.company_id)

swapped_recruiters = db.query(Recruiter).filter(Recruiter.company_id.in_(human_company_ids)).all()
swapped_count = len(swapped_recruiters)
pct = (swapped_count / total_recs) * 100 if total_recs else 0
print(f"\nSTEP 1: Total swapped records across full table: {swapped_count} ({pct:.2f}%)")

prefixes = Counter()
for r in swapped_recruiters:
    em = r.email or ""
    if '@missing.local' in em or '@invalid.local' in em:
        pref = em.split('_')[0] if '_' in em else 'other'
        prefixes[pref + '_placeholder'] += 1
    else:
        prefixes['real_or_other_email'] += 1

print("\nSTEP 2: Prefix breakdown:")
for k, v in prefixes.most_common():
    print(f"  {k}: {v}")

sources = Counter([str(r.data_source) for r in swapped_recruiters])
jobs = Counter([str(r.source_job_id) for r in swapped_recruiters])
dates = Counter([str(r.created_at)[:10] for r in swapped_recruiters if r.created_at])

print("\nSTEP 3: Batch/Date correlation:")
print("Top data_sources:", sources.most_common(5))
print("Top source_job_ids:", jobs.most_common(5))
print("Top created_at dates:", dates.most_common(5))

safe_swap = 0
ambiguous_swap = 0
for r in swapped_recruiters:
    name_field = r.recruiter_name or ""
    if not worker.is_human_name(name_field, "") or any(w in name_field.lower() for w in ['llc', 'inc', 'group', 'technologies', 'solutions', 'partners', 'associates', 'staffing', 'consulting']):
        safe_swap += 1
    else:
        ambiguous_swap += 1

print(f"\nSTEP 4: Safe auto-fix estimate: {safe_swap} | Ambiguous/Risky: {ambiguous_swap}")

