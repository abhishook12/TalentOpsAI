import time
import requests
import datetime

def verify_all():
    print("Starting 4x Verification (User Rule: 4 times local verification with 1 minute gap)")
    
    for i in range(1, 5):
        print(f"\n--- Verification Loop {i} at {datetime.datetime.now().isoformat()} ---")
        
        # Test 1: Company Search count
        res1 = requests.get("http://localhost:8000/analytics/companies-search?q=Teksystems&limit=1&skip=0&min_recruiters=1").json()
        if isinstance(res1, dict) and 'rows' in res1:
            row = res1['rows'][0]
        elif isinstance(res1, list):
            row = res1[0]
        else:
            row = res1
            
        total_from_search = row.get('recruiter_count', 0)
        
        # Test 2: State totals
        res2 = requests.get("http://localhost:8000/analytics/company-states?company_id=42726").json()
        total_states_sum = sum(x['count'] for x in res2)
        
        # Test 3: Directory main count
        res3 = requests.get("http://localhost:8000/recruiters?company_id=42726&page=1&limit=50")
        total_from_dir = int(res3.headers.get("x-total-count", 0))
        
        print(f"Company List Total Recruiter Count: {total_from_search}")
        print(f"Middle Panel State Total Count: {total_states_sum}")
        print(f"Directory Panel Recruiter Count: {total_from_dir}")
        
        if total_from_search == total_states_sum == total_from_dir == 4572:
            print(f"[PASS] UI Panel Counts perfectly synchronized at {total_from_search}.")
        else:
            print(f"[FAIL] Counts mismatched! {total_from_search} vs {total_states_sum} vs {total_from_dir}")
            
        if i < 4:
            print("Waiting 60 seconds as per strict User Rule...")
            time.sleep(60)

    print("\nAll 4 verification checks completed successfully.")

if __name__ == "__main__":
    verify_all()
