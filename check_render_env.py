import os
import requests

RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
url = "https://api.render.com/v1/services/srv-d8bkagugvqtc73cvie6g/env-vars"

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {RENDER_API_KEY}"
}

response = requests.get(url, headers=headers)
env_vars = response.json()
for env in env_vars:
    print(f"{env['envVar']['key']} = {env['envVar']['value']}")
