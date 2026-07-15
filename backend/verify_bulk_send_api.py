import requests
import time

def verify_bulk_send():
    url = "http://localhost:8000/campaigns/bulk-send"
    payload = {
        "emails": ["test1@example.com", "test2@example.com"],
        "subject": "Verification Test",
        "body": "This is a verification test",
        "from_email": "test@talentops.ai"
    }
    
    print("Starting 3x API Verification for /campaigns/bulk-send...")
    for i in range(1, 4):
        print(f"--- API Verification Loop {i} ---")
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"SUCCESS: Received 200 OK -> {response.json()}")
            else:
                print(f"ERROR: Received {response.status_code} -> {response.text}")
        except Exception as e:
            print(f"ERROR: Request failed: {e}")
            
        time.sleep(2)
        
    print("All 3 checks complete.")

if __name__ == "__main__":
    verify_bulk_send()
