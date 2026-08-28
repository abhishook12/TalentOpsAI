import os
import requests
import time
import sys

RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
SRVS = ["srv-d8bkagugvqtc73cvie6g", "srv-d8q3be1kh4rs73c36730"]

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {RENDER_API_KEY}"
}

print("Waiting for deployments to finish...")

for srv in SRVS:
    while True:
        url = f"https://api.render.com/v1/services/{srv}/deploys?limit=1"
        res = requests.get(url, headers=headers).json()
        status = res[0]['deploy']['status']
        print(f"Service {srv} status: {status}")
        if status == "live":
            break
        if status in ["build_failed", "update_failed", "canceled"]:
            print(f"Deployment failed for {srv}!")
            sys.exit(1)
        time.sleep(10)

print("ALL DEPLOYMENTS LIVE!")
