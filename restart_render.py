import os
import requests

RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
SRV_ID = "srv-d8bkagugvqtc73cvie6g"
url = f"https://api.render.com/v1/services/{SRV_ID}/deploys"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {RENDER_API_KEY}"
}

print("Triggering new deploy (restart) for TalentOpsAI-1...")
res = requests.post(url, json={"clearCache": "clear"}, headers=headers)
print(res.status_code, res.text)
