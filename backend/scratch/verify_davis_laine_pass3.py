import sys
sys.path.insert(0, r"C:\TalentOpsAI\backend")
from app.services.recruiter_store import recruiter_store

def run_pass3():
    print("=" * 80, flush=True)
    print("CHECK 3 (PASS 3): LIVE UNIFIED RECRUITERSTORE QUERY ENGINE VERIFICATION", flush=True)
    print("=" * 80, flush=True)

    recruiter_store._ensure_loaded()
    
    # 1. Search by domain query
    items_dom = recruiter_store.search("davislaine", limit=50)
    print(f"[3.1] RecruiterStore.search('davislaine') returned {len(items_dom)} items", flush=True)
    assert len(items_dom) >= 10, f"Expected at least 10 items, got {len(items_dom)}"

    # 2. Search by candidate name
    items_name = recruiter_store.search("Duncan Blythe", limit=50)
    print(f"[3.2] RecruiterStore.search('Duncan Blythe') returned {len(items_name)} item(s)", flush=True)
    assert len(items_name) >= 1, f"Expected at least 1 item, got {len(items_name)}"
    dl_match = [i for i in items_name if i['email'] == "dblythe@davislaine.com"]
    assert len(dl_match) == 1, "Expected Duncan Blythe at dblythe@davislaine.com"
    assert dl_match[0]['phone'] == "(314) 725-9922"

    # 3. Search by email
    items_email = recruiter_store.search("ldavis@davislaine.com", limit=50)
    print(f"[3.3] RecruiterStore.search('ldavis@davislaine.com') returned {len(items_email)} item(s)", flush=True)
    assert len(items_email) == 1, f"Expected 1 item, got {len(items_email)}"
    assert items_email[0]['recruiter_name'] == "Lauren Davis, MPH, PMP"

    for r in items_dom:
        if r['email'] in ["dblythe@davislaine.com", "ldavis@davislaine.com", "mnicholas@davislaine.com"]:
            print(f"      - Live Query Verified: {r['recruiter_name']} | {r['email']} | Phone: {r.get('phone') or 'N/A'} | Status: {r.get('email_status')} | Deliverable: {r.get('is_deliverable')}", flush=True)
            assert r.get("email_status") == "verified"
            assert r.get("is_deliverable") == True

    print("\n" + "=" * 80, flush=True)
    print("CHECK 3 (PASS 3) RESULT: LIVE UNIFIED QUERY ENGINE 100% VERIFIED!", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    run_pass3()
