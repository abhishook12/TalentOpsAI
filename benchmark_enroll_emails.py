import time
import asyncio
import httpx
from datetime import datetime

# Point to local backend
BASE_URL = "http://localhost:8000"

async def main():
    # 1. Login to get a token
    # We will just login as the admin account used in the critical paths test
    print("Logging in...")
    async with httpx.AsyncClient() as client:
        login_res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@talentops.com",
            "password": "1012"
        })
        
        if login_res.status_code != 200:
            print(f"Failed to login: {login_res.text}")
            return
            
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create a temporary campaign for testing
        print("Creating test campaign...")
        camp_res = await client.post(f"{BASE_URL}/campaigns", json={
            "name": f"Benchmark Campaign {datetime.now().timestamp()}"
        }, headers=headers)
        
        if camp_res.status_code != 200:
            print(f"Failed to create campaign: {camp_res.text}")
            return
            
        campaign_id = camp_res.json()["campaign_id"]
        
        # 3. Create a dummy sequence step so it allows enrollment
        await client.post(f"{BASE_URL}/campaigns/{campaign_id}/sequence", json={
            "steps": [
                {
                    "step_order": 1,
                    "delay_days": 0,
                    "template_id": None
                }
            ]
        }, headers=headers)
        
        # 4. Generate 5000 recipients
        print("Generating 5000 dummy recipients...")
        recipients = []
        for i in range(5000):
            recipients.append({
                "email": f"dummy{i}_{int(time.time())}@example.com",
                "name": f"Dummy {i}",
                "company": "Acme Corp",
                "role": "Engineer"
            })
            
        # 5. Measure time to enroll (3 checks)
        for check in range(1, 4):
            print(f"\n--- Check {check} ---")
            print(f"Enrolling 5000 recipients to campaign {campaign_id}...")
            start_time = time.time()
            
            enroll_res = await client.post(
                f"{BASE_URL}/campaigns/{campaign_id}/enroll-emails", 
                json={"recipients": recipients}, 
                headers=headers,
                timeout=120.0
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            if enroll_res.status_code != 200:
                print(f"Failed to enroll: {enroll_res.text}")
            else:
                enrolled = enroll_res.json().get("enrolled_count", 0)
                print(f"Successfully enrolled {enrolled} recipients.")
                print(f"Execution time: {elapsed:.3f} seconds!")
                
            # Clear recipients for next iteration to ensure it inserts new ones or processes updates
            if check < 3:
                recipients = []
                for i in range(5000):
                    recipients.append({
                        "email": f"dummy{i}_{int(time.time())}_{check}@example.com",
                        "name": f"Dummy {i}",
                        "company": "Acme Corp",
                        "role": "Engineer"
                    })
                time.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
