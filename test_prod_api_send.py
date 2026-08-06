import requests
import time
import uuid

API_URL = "https://talentopsai-1.onrender.com"

def run_test(iteration):
    print(f"\n--- ATTEMPT {iteration} ---")
    session = requests.Session()
    
    email = f"e2e_api_{uuid.uuid4().hex[:6]}@talentops.com"
    password = "Password123!"
    
    # 0. Register
    print("0. Registering new user...")
    res = session.post(f"{API_URL}/auth/register", json={
        "first_name": "API",
        "last_name": "Tester",
        "email": email,
        "password": password
    })
    if res.status_code not in [200, 201]:
        print(f"Registration failed: {res.status_code} {res.text}")
        # Proceed anyway in case it already exists, or just return False
        return False
        
    # 1. Login
    print("1. Logging in...")
    res = session.post(f"{API_URL}/auth/login", json={
        "email": email,
        "password": password,
        "remember_me": False
    })
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        return False
        
    print("2. Creating campaign...")
    res = session.post(f"{API_URL}/campaigns", json={
        "name": f"API Test Campaign {iteration} {uuid.uuid4().hex[:6]}"
    })
    if res.status_code != 200:
        print(f"Failed to create campaign: {res.text}")
        return False
    campaign_id = res.json()["id"]
    print(f"Campaign created: {campaign_id}")
    
    print("3. Adding recipient...")
    res = session.post(f"{API_URL}/campaigns/validate-recipients", json={
        "emails": [f"test_target_{uuid.uuid4().hex[:6]}@example.com"]
    })
    recipients = res.json().get("recipients", [])
    if not recipients:
        print("Failed to validate recipient")
        return False
        
    res = session.post(f"{API_URL}/campaigns/{campaign_id}/recipients", json={
        "recipients": recipients
    })
    if res.status_code != 200:
        print(f"Failed to add recipient: {res.text}")
        return False
        
    print("4. Updating template...")
    res = session.put(f"{API_URL}/campaigns/{campaign_id}", json={
        "subject": "Automated API Test",
        "body": "This is an automated API test email."
    })
    
    print("5. Generating preview (The step that had the IntegrityError bug!)...")
    res = session.post(f"{API_URL}/campaigns/{campaign_id}/prepare-preview")
    if res.status_code != 200:
        print(f"FAILED TO GENERATE PREVIEW: {res.text}")
        return False
        
    print("6. Launching campaign...")
    res = session.post(f"{API_URL}/campaigns/{campaign_id}/launch")
    if res.status_code != 200:
        print(f"Failed to launch: {res.text}")
        return False
        
    print("Campaign successfully launched!")
    return True

if __name__ == "__main__":
    success_count = 0
    for i in range(1, 4):
        if run_test(i):
            success_count += 1
        time.sleep(2)
        
    print(f"\nFinal Result: {success_count}/3 successful sends.")
    if success_count == 3:
        print("3-pass verification successful!")
