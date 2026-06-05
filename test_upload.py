import requests
import json
import time

BASE_URL = "https://talentopsai-staging.onrender.com/api/import"
HEALTH_URL = "https://talentopsai-staging.onrender.com/api/health"
FILE_PATH = r"C:\Users\User\Desktop\for talent ops.xlsx"

print(f"--- 1. Testing Backend Health ---")
try:
    health = requests.get(f"{HEALTH_URL}")
    print(f"Health check: {health.status_code} - {health.text}")
except Exception as e:
    print(f"Health check failed: {e}")

print(f"\n--- 2. Uploading File for Parsing ---")
try:
    with open(FILE_PATH, 'rb') as f:
        files = {'file': ('for talent ops.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        res = requests.post(f"{BASE_URL}/parse", files=files)
        print(f"Parse response: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            job_id = data.get("job_id")
            print(f"Job ID: {job_id}")
            print(f"Total Rows Detected: {data.get('total_rows')}")
            print(f"Format Detected: {data.get('detected_format')}")
        else:
            print(res.text)
            job_id = None
except Exception as e:
    print(f"Upload failed: {e}")
    job_id = None

if job_id:
    print(f"\n--- 3. Validating (Manual Mapping) ---")
    mapping = {
        "company": "RMC Integration Services LLC",
        "name": "Michael Yurukov",
        "email": "myurukov@rmcintservices.com",
    }
    try:
        res = requests.post(f"{BASE_URL}/validate/{job_id}", json={"mapping": mapping})
        print(f"Validate response: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Validation failed: {e}")

    print(f"\n--- 4. Polling Validation Progress ---")
    for _ in range(60): # wait up to 120s
        time.sleep(2)
        try:
            res = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
            if res.status_code == 200:
                status = res.json()
                print(f"Status: {status.get('status')} - {status.get('progress_percent')}% - {status.get('current_step')}")
                if status.get('status') == 'preview_ready':
                    print(f"Validation Finished!")
                    print(json.dumps(status, indent=2))
                    break
        except Exception as e:
            print(f"Status check failed: {e}")

    print(f"\n--- 5. Committing Import ---")
    try:
        res = requests.post(f"{BASE_URL}/commit/{job_id}")
        print(f"Commit response: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Commit failed: {e}")

    print(f"\n--- 6. Polling Import Progress ---")
    for _ in range(60):
        time.sleep(2)
        try:
            res = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
            if res.status_code == 200:
                status = res.json()
                print(f"Status: {status.get('status')} - {status.get('progress_percent')}% - {status.get('current_step')}")
                if status.get('status') in ('completed', 'failed'):
                    print(f"Import Finished!")
                    print(json.dumps(status, indent=2))
                    break
        except Exception as e:
            pass
