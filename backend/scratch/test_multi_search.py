import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.database import SessionLocal
from app.models.models import Company
from app.services.recruiter_store import recruiter_store

recruiter_store._ensure_loaded()
db = SessionLocal()

def test_search(query):
    matched_keys = []
    if query and query.strip():
        search_pattern = f"%{query.strip()}%"
        matching_pg = db.query(Company.company_id).filter(Company.company_name.ilike(search_pattern)).all()
        matched_keys = [str(r[0]) for r in matching_pg]
    
    res = recruiter_store.company_directory(query, matched_keys=matched_keys)
    print(f"\nSearch for '{query}' -> Found {len(res)} results:")
    for r in res[:5]:
        print(f"  - Key: {r['company_key']} | Count: {r['recruiter_count']} | Domain: {r['dominant_domain']}")

test_search("blueStone")
test_search("Robert")
test_search("Insight")
test_search("Manpower")

db.close()
