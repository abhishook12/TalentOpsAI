import os
import requests

RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
url = "https://api.render.com/v1/services"
headers = {"accept": "application/json", "authorization": f"Bearer {RENDER_API_KEY}"}
response = requests.get(url, headers=headers)
services = response.json()
for srv in services:
    print(f"{srv['service']['name']} ({srv['service']['id']})")
