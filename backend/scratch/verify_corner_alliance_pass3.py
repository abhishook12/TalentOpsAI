import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store

def run_pass3():
    print("=" * 80)
    print("CHECK 3 (PASS 3): LIVE UNIFIED RECRUITERSTORE QUERY ENGINE VERIFICATION")
    print("=" * 80)

    recruiter_store._ensure_loaded()
    
    # 1. Search by domain query
    items_dom = recruiter_store.search("corneralliance", limit=50)
    print(f"[3.1] RecruiterStore.search('corneralliance') returned {len(items_dom)} items")
    assert len(items_dom) == 14, f"Expected 14 items, got {len(items_dom)}"

    # 2. Search by candidate name
    items_name = recruiter_store.search("Nolan Johnson", limit=50)
    print(f"[3.2] RecruiterStore.search('Nolan Johnson') returned {len(items_name)} item(s)")
    assert len(items_name) >= 1, f"Expected at least 1 item, got {len(items_name)}"
    assert items_name[0]['email'] == "njohnson@corneralliance.com"

    # 3. Search by email
    items_email = recruiter_store.search("aspence@corneralliance.com", limit=50)
    print(f"[3.3] RecruiterStore.search('aspence@corneralliance.com') returned {len(items_email)} item(s)")
    assert len(items_email) == 1, f"Expected 1 item, got {len(items_email)}"
    assert items_email[0]['recruiter_name'] == "Amie Spence"

    for r in items_dom:
        print(f"      - ID {r['recruiter_id']}: {r['recruiter_name']} | {r['email']} | Status: {r.get('email_status')} | Deliverable: {r.get('is_deliverable')}")
        assert r.get("email_status") == "verified"
        assert r.get("is_deliverable") == True

    print("\n" + "=" * 80)
    print("CHECK 3 (PASS 3) RESULT: LIVE UNIFIED QUERY ENGINE 100% VERIFIED!")
    print("=" * 80)

if __name__ == "__main__":
    run_pass3()
