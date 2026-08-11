import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def run_tests():
    print("=== Campaign Infrastructure E2E Tests ===")
    
    # 1. Register a test user
    email = f"test_e2e_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StrongPass123!"
    print(f"[*] Registering user {email}...")
    r = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": pwd, "first_name": "Test", "last_name": "User", "company_name": "Test Co"})
    assert r.status_code in [200, 201], r.text
    
    # 2. Login
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    token = r.json().get("access_token") or r.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create Campaign
    print("[*] Creating campaign...")
    r = requests.post(f"{BASE_URL}/campaigns", headers=headers, json={"name": "E2E Test Campaign"})
    assert r.status_code == 200
    campaign_id = r.json()["campaign_id"]
    
    # 4. Add Recipient
    print(f"[*] Enrolling recipient to campaign {campaign_id}...")
    r = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/prepare-preview", headers=headers, json={
        "name": "E2E Test Campaign",
        "subject": "Test Subject",
        "body": "<p>Hello</p>",
        "recipients": [{"email": "target@example.com", "name": "Target Person", "role": "Engineer"}]
    })
    assert r.status_code == 200, f"prepare-preview failed: {r.text}"
    
    # 5. TEST C: Invalid Sender UX
    print("[*] Executing TEST C: Invalid Sender Validation...")
    r = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start", headers=headers)
    assert r.status_code == 400
    err = r.json()["detail"]
    assert "Your sending account needs attention. No sender selected." in err, f"Unexpected error: {err}"
    print("    [PASS] TEST C Passed: Correctly caught missing sender with friendly message.")
    
    # 6. Add Mock Sender
    r = requests.post(f"{BASE_URL}/accounts/smtp", headers=headers, json={
        "email_address": "sender@test.com",
        "smtp_host": "mock.local",
        "smtp_port": 587,
        "smtp_user": "sender",
        "smtp_pass": "pass"
    })
    assert r.status_code == 200, r.text
    account_id = r.json()["account_id"]
    
    # Update campaign sender
    r = requests.post(f"{BASE_URL}/campaigns/{campaign_id}/prepare-preview", headers=headers, json={
        "name": "E2E Test Campaign",
        "from_email": "sender@test.com",
        "subject": "Test Subject",
        "body": "<p>Hello</p>",
        "recipients": [{"email": "target@example.com", "name": "Target Person", "role": "Engineer"}]
    })
    assert r.status_code == 200, r.text
    
    # We must patch the campaign's sender_account_id to simulate what the UI does on saveDraft.
    # We will use /campaigns/{id} PUT
    r = requests.put(f"{BASE_URL}/campaigns/{campaign_id}", headers=headers, json={"sender_account_id": account_id})
    assert r.status_code == 200, r.text
    
    # 7. TEST A & D: Multiple Clicks Idempotency & Send
    print("[*] Executing TEST D: Idempotency (Sending multiple concurrent start requests)...")
    import concurrent.futures
    def start_campaign():
        return requests.post(f"{BASE_URL}/campaigns/{campaign_id}/start", headers=headers)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(start_campaign) for _ in range(5)]
        results = [f.result() for f in futures]
    
    success_starts = 0
    idempotent_skips = 0
    errors = 0
    
    for res in results:
        if res.status_code == 200:
            if "already running" in res.json().get("message", ""):
                idempotent_skips += 1
            else:
                success_starts += 1
        else:
            errors += 1
            print(f"Error: {res.status_code} - {res.text}")
            
    print(f"    Starts: {success_starts}, Skips: {idempotent_skips}, Errors: {errors}")
    assert success_starts == 1, f"Expected 1 start, got {success_starts}"
    assert idempotent_skips == 4, f"Expected 4 idempotent skips, got {idempotent_skips}"
    assert errors == 0
    print("    [PASS] TEST D Passed: Only one start succeeded, duplicates safely bypassed.")
    print("    [PASS] TEST A Passed: Campaign accepted by SendEngine.")
    
    print("\n[SUCCESS] All infrastructure tests passed successfully!")

if __name__ == "__main__":
    run_tests()
