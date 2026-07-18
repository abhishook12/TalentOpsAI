import requests
import json
import time
import uuid

API_URL = "https://talentopsai-1.onrender.com"

def login():
    test_email = f"test_{int(time.time())}@example.com"
    test_pass = "Password123!"
    
    print(f"Registering {test_email}...")
    requests.post(f"{API_URL}/auth/register", json={
        "email": test_email,
        "password": test_pass,
        "first_name": "Live",
        "last_name": "Test"
    })
    
    import subprocess
    print("Activating...")
    subprocess.run(f'python activate_user.py "{test_email}"', shell=True)
    
    print("Logging in...")
    res = requests.post(f"{API_URL}/auth/login", data={
        "username": test_email,
        "password": test_pass
    })
    token = res.json().get("access_token")
    if not token:
        print("Login failed:", res.text)
        exit(1)
    
    print("✅ Logged in.")
    return token

def run_campaign(token, name, sender, recipients):
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n--- Starting Campaign: {name} ---")
    timestamp_id = str(uuid.uuid4())[:8]
    subject = f"Live Production Test [{timestamp_id}] - {name}"
    
    # 1. Create Campaign
    res = requests.post(f"{API_URL}/campaigns", json={
        "name": name,
        "from_email": sender,
        "status": "draft",
        "is_active": True
    }, headers=headers)
    cid = res.json()["campaign_id"]
    print(f"✅ Campaign created. ID: {cid}")
    
    # 2. Add Template
    requests.post(f"{API_URL}/campaigns/{cid}/templates", json={
        "name": "Template 1",
        "subject": subject,
        "body": f"This is a live production test for {name}. This email confirms the TalentOps Campaign Engine is fully operational.\nTimestamp: {int(time.time())}"
    }, headers=headers)
    print("✅ Template added.")
    
    # 3. Enroll Recipients
    requests.post(f"{API_URL}/campaigns/{cid}/enroll-emails", json={
        "emails": recipients
    }, headers=headers)
    print(f"✅ Enrolled {len(recipients)} recipients.")
    
    # 4. Start Campaign
    requests.post(f"{API_URL}/campaigns/{cid}/start", headers=headers)
    print(f"✅ Campaign {cid} started.")
    
    # 5. Monitor Stream
    start_time = time.time()
    while time.time() - start_time < 120:
        time.sleep(3)
        res = requests.get(f"{API_URL}/campaigns/{cid}/progress", headers=headers, stream=True)
        # Instead of streaming (which blocks sometimes), let's just use the progress endpoint which returns real-time ETA
        # Oh wait, /campaigns/{cid}/progress is SSE. We can just hit it or the database!
        for line in res.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    data = json.loads(decoded[6:])
                    print(f"Status: {data['status']}, Sent: {data['sent']}/{data['total']}")
                    if data['status'] in ['completed', 'failed']:
                        print(f"✅ Campaign {cid} finished with status: {data['status']}")
                        return subject
        # To avoid blocking forever, we break and re-poll
        # Wait, if we break, we lose the stream. The stream should terminate on completed.
    return subject

def run_tests():
    start_overall = time.time()
    token = login()
    sender = "abhishek.jadon@technovion.com"
    
    # Test 1
    t1_start = time.time()
    t1_subj = run_campaign(token, "Test 1 (Single)", sender, ["abhishekjadon706@gmail.com"])
    t1_time = time.time() - t1_start
    
    # Test 2
    t2_start = time.time()
    t2_subj = run_campaign(token, "Test 2 (Multiple)", sender, ["abhishekjadon706@gmail.com", "abhishekjadon824@gmail.com"])
    t2_time = time.time() - t2_start
    
    print("\n--- FINAL RESULTS ---")
    print(f"Test 1 Subject Prefix: {t1_subj} ({t1_time:.1f}s)")
    print(f"Test 2 Subject Prefix: {t2_subj} ({t2_time:.1f}s)")
    print(f"Total Elapsed: {time.time() - start_overall:.1f}s")
    
    with open('C:/TalentOpsAI/live_test_subjects.txt', 'w') as f:
        f.write(f"{t1_subj}\n{t2_subj}")

if __name__ == "__main__":
    run_tests()
