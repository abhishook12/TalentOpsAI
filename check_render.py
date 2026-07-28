import os
import requests

RENDER_API_KEY = "rnd_d9ssMhxT81Gp3Id45K7kaa7KOOIK"
url = "https://api.render.com/v1/services"

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {RENDER_API_KEY}"
}

response = requests.get(url, headers=headers)
services = response.json()
for srv in services:
    srv_id = srv['service']['id']
    name = srv['service']['name']
    print(f"Service: {name} ({srv_id})")
    
    # Get deployments
    dep_url = f"https://api.render.com/v1/services/{srv_id}/deploys?limit=5"
    deps = requests.get(dep_url, headers=headers).json()
    for d in deps:
        print(f"  Deploy {d['deploy']['id']}: {d['deploy']['status']} at {d['deploy']['updatedAt']} (Commit: {d['deploy']['commit']['id'] if d['deploy'].get('commit') else 'unknown'})")
