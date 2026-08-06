import os
import requests
import sys

sys.path.append('C:/TalentOpsAI/backend')
from dotenv import dotenv_values

local_env = dotenv_values('C:/TalentOpsAI/backend/.env')
tavily_keys = local_env.get('TAVILY_API_KEYS')
tavily_key = local_env.get('TAVILY_API_KEY')

if not tavily_keys:
    print("No TAVILY_API_KEYS in local .env!")
    sys.exit(1)

RENDER_API_KEY = "rnd_d9ssMhxT81Gp3Id45K7kaa7KOOIK"
headers = {
    "accept": "application/json",
    "authorization": f"Bearer {RENDER_API_KEY}",
    "content-type": "application/json"
}

service_ids = ['srv-d8bkagugvqtc73cvie6g', 'srv-d8q3be1kh4rs73c36730']

for srv_id in service_ids:
    print(f"Updating service ID: {srv_id}")
    
    env_url = f"https://api.render.com/v1/services/{srv_id}/env-vars"
    resp = requests.get(env_url, headers=headers)
    if resp.status_code != 200:
        print(f"Error fetching env: {resp.text}")
        continue
        
    existing_vars = []
    for ev in resp.json():
        existing_vars.append({
            "key": ev['envVar']['key'],
            "value": ev['envVar']['value']
        })

    # Update TAVILY_API_KEYS
    found_keys = False
    for ev in existing_vars:
        if ev['key'] == 'TAVILY_API_KEYS':
            ev['value'] = tavily_keys
            found_keys = True
        elif ev['key'] == 'TAVILY_API_KEY':
            ev['value'] = tavily_key
            
    if not found_keys:
        existing_vars.append({"key": "TAVILY_API_KEYS", "value": tavily_keys})
        existing_vars.append({"key": "TAVILY_API_KEY", "value": tavily_key})
        
    put_resp = requests.put(env_url, headers=headers, json=existing_vars)
    if put_resp.status_code == 200:
        print(f"Successfully updated env vars for {srv_id}!")
    else:
        print(f"Failed to update env vars for {srv_id}: {put_resp.status_code} {put_resp.text}")
