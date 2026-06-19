import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')

r = requests.get('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
all_live = True
if r.status_code == 200:
    for s in r.json():
        if s['service']['name'] in ['talentops-api', 'TalentOpsAI-1']:
            dep = requests.get(f"https://api.render.com/v1/services/{s['service']['id']}/deploys", headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
            latest = dep.json()[0]['deploy']
            status = latest['status']
            print(f"{s['service']['name']} -> {status}")
            if status != 'live':
                all_live = False
else:
    print("Failed")
    all_live = False

if all_live:
    print("ALL LIVE")
    sys.exit(0)
else:
    sys.exit(1)
