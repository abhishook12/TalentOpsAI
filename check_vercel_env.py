import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')
vercel_key = os.getenv('VERCEL_TOKEN')

# Project ID: prj_4TFHAL3GkqvEoIcIg3R7yLdTaKr3
project_id = 'prj_4TFHAL3GkqvEoIcIg3R7yLdTaKr3'

headers = {
    'Authorization': f'Bearer {vercel_key}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

r = requests.get(f'https://api.vercel.com/v9/projects/{project_id}/env', headers=headers)
print("VERCEL ENVS:")
if r.status_code == 200:
    for e in r.json().get('envs', []):
        print(f"{e['key']} = {e['value']}")
        # update if wrong
        if e['key'] == 'VITE_API_URL' and e['value'] != 'https://talentopsai-1.onrender.com':
            print("Fixing VITE_API_URL...")
            patch_data = {
                "value": "https://talentopsai-1.onrender.com",
                "type": "plain",
                "target": ["production", "preview", "development"]
            }
            patch_req = requests.patch(f"https://api.vercel.com/v9/projects/{project_id}/env/{e['id']}", headers=headers, json=patch_data)
            print("Patch Status:", patch_req.status_code)
            
            # Trigger a new deployment!
            print("Triggering new Vercel deployment...")
            deploy_data = {
                "name": "talent-ops-ai",
                "target": "production",
                "project": project_id
            }
            # Actually, to trigger a deployment via API without files, you'd use a Deploy Hook or github push.
            # I can just push an empty commit to trigger it!
else:
    print("Failed", r.text)
