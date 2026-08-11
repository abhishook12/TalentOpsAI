import time
import requests

API_URL = "https://talentopsai-1.onrender.com"

print("--- PROD VERIFICATION START ---")
print("Target:", API_URL)
print("Waiting 15 seconds to ensure Render deployment is live...")
time.sleep(15)

# Authenticate first
s = requests.Session()
login_res = s.post(f'{API_URL}/auth/login', json={
    "email": "admin@talentops.com",
    "password": "admin123456"
})

if login_res.status_code != 200:
    print(f"Failed to login: {login_res.status_code} {login_res.text}")
    print("Cannot proceed with verification.")
    exit(1)

token = login_res.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

print("Waiting for Render deployment to finish and data to load (up to 5 minutes)...")

massive_data_live = False
for attempt in range(1, 31):
    try:
        resp = s.get(f"{API_URL}/analytics/recruiters-by-state", headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            total_sum = sum(x['count'] for x in data)
            if total_sum > 1_500_000:
                print(f"\\n[Attempt {attempt}] MASSIVE DATA DETECTED! Total: {total_sum:,}")
                massive_data_live = True
                break
            else:
                print(f"  [Attempt {attempt}] Data still small ({total_sum:,}). Waiting for deploy...")
        else:
            print(f"  [Attempt {attempt}] Error {resp.status_code}")
    except Exception as e:
        print(f"  [Attempt {attempt}] Request failed: {e}")
        
    time.sleep(10)

if not massive_data_live:
    print("Verification failed: Deployment did not serve massive data in time.")
    exit(1)

print("\\n--- PERFORMING MANDATORY 3 CHECKS ---")
for i in range(1, 4):
    print(f"\\n[Check {i}/3] Requesting /analytics/recruiters-by-state...")
    start_t = time.time()
    resp = s.get(f"{API_URL}/analytics/recruiters-by-state", headers=headers, timeout=30)
    dur = time.time() - start_t
    
    if resp.status_code == 200:
        data = resp.json()
        tx_count = next((x['count'] for x in data if x['state'] == 'TX'), 0)
        ca_count = next((x['count'] for x in data if x['state'] == 'CA'), 0)
        total_sum = sum(x['count'] for x in data)
        
        print(f"  [SUCCESS] (took {dur:.2f}s)")
        print(f"  > Total recruiter count across states: {total_sum:,}")
        print(f"  > TX Count: {tx_count:,}")
        print(f"  > CA Count: {ca_count:,}")
        if total_sum > 1_500_000:
            print("  => VERDICT: MASSIVE DATA IS LIVE!")
        else:
            print("  => VERDICT: FAIL!")
    else:
        print(f"  [FAIL] Status code: {resp.status_code}")
    time.sleep(2)

print("\\n--- PROD VERIFICATION COMPLETE ---")

