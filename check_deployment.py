import requests
import time
import sys

BACKEND_URL = "https://talentopsai-1.onrender.com"
FRONTEND_URL = "https://talent-ops-ai.vercel.app"

def wait_for_deployment():
    print("Waiting for Render backend deployment to finish...")
    # Wait up to 10 minutes
    max_retries = 60
    for i in range(max_retries):
        try:
            # The root endpoint or /auth/login
            res = requests.get(f"{BACKEND_URL}/", timeout=10)
            if res.status_code in [200, 404]: # If it responds with anything other than 502/503/timeout, it's up
                print(f"Backend is up! (Status: {res.status_code})")
                
                # Verify that the new /auth/google endpoint is now present
                # It should return 401/500/405/422 for a bad POST, NOT 404.
                auth_res = requests.post(f"{BACKEND_URL}/auth/google", json={"credential": "test"}, timeout=10)
                print(f"/auth/google returned: {auth_res.status_code}")
                if auth_res.status_code != 404:
                    print("SUCCESS: The new auth endpoints are deployed on the backend!")
                    return True
                else:
                    print("Backend is up but /auth/google returned 404. It might still be running the old version.")
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries}: Backend not ready yet... ({type(e).__name__})")
        
        time.sleep(10)
    
    print("Failed to verify backend deployment within the timeout.")
    return False

if __name__ == "__main__":
    success = wait_for_deployment()
    if not success:
        sys.exit(1)
