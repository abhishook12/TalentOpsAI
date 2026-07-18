import requests
import time
import uuid

API_URL = "https://talentopsai-1.onrender.com"

def run_campaign(name, sender, recipients, token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Campaign
    print(f"\n--- Starting Campaign: {name} ---")
    camp_res = requests.post(f"{API_URL}/campaigns", json={
        "name": name,
        "from_email": sender,
        "status": "draft",
        "is_active": True
    }, headers=headers)
    camp_res.raise_for_status()
    cid = camp_res.json()["campaign_id"]
    print(f"[OK] Campaign created. ID: {cid}")
    
    # 2. Add Template
    subject = f"Live Production Test [{uuid.uuid4().hex[:8]}] - {name}"
    tmpl_res = requests.post(f"{API_URL}/campaigns/{cid}/templates", json={
        "name": "Template 1",
        "subject": subject,
        "body": f"This is a live production test for {name}. This email confirms the TalentOps Campaign Engine is fully operational.\nTimestamp: {time.time()}"
    }, headers=headers)
    tmpl_res.raise_for_status()
    print("[OK] Template added.")
    
    # 3. Enroll Recipients
    enr_res = requests.post(f"{API_URL}/campaigns/{cid}/enroll-emails", json={
        "emails": recipients
    }, headers=headers)
    enr_res.raise_for_status()
    print(f"[OK] Enrolled {len(recipients)} recipients.")
    
    # 4. Start Campaign
    start_res = requests.post(f"{API_URL}/campaigns/{cid}/start", headers=headers)
    start_res.raise_for_status()
    print(f"[OK] Campaign {cid} started.")
    
    # 5. Monitor via GET /campaigns/{cid}
    print("[WAIT] Waiting for campaign to complete...")
    for _ in range(60):
        time.sleep(5)
        res = requests.get(f"{API_URL}/campaigns/{cid}", headers=headers).json()
        status = res["status"]
        cr_status = [cr["status"] for cr in res["campaign_recruiters"]]
        print(f"   Status: {status} | Recipients: {cr_status}")
        if status in ["completed", "failed"]:
            print(f"[OK] Campaign {cid} finished with status: {status}")
            break

def main():
    test_email = f"test_{int(time.time())}@example.com"
    test_pass = "Password123!"
    
    print(f"Registering {test_email}...")
    requests.post(f"{API_URL}/auth/register", json={
        "email": test_email, "password": test_pass, "first_name": "Live", "last_name": "Test"
    }).raise_for_status()
    
    import subprocess
    subprocess.run(["python", "activate_user.py", test_email], check=True)
    
    res = requests.post(f"{API_URL}/auth/login", json={"email": test_email, "password": test_pass})
    res.raise_for_status()
    token = res.json()["token"]
    print("[OK] Logged in.")
    
    sender = "abhishek.jadon@technovion.com"
    run_campaign("Test 1 (Single Recipient)", sender, ["abhishekjadon706@gmail.com"], token)
    run_campaign("Test 2 (Multiple Recipients)", sender, ["abhishekjadon706@gmail.com", "abhishekjadon824@gmail.com"], token)
    
    print("\n--- ALL TESTS TRIGGERED ---")

if __name__ == "__main__":
    main()
