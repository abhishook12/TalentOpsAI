import time
import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv('.env.deploy')
k = os.getenv('RENDER_API_KEY')

print("Waiting for Render deployments to become 'live'...")
while True:
    r = requests.get('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {k}', 'Accept': 'application/json'})
    all_live = True
    for s in r.json():
        if s['service']['name'] in ['talentops-api', 'TalentOpsAI-1']:
            dep = requests.get(f"https://api.render.com/v1/services/{s['service']['id']}/deploys", headers={'Authorization': f'Bearer {k}', 'Accept': 'application/json'})
            status = dep.json()[0]['deploy']['status']
            if status != 'live':
                all_live = False
    if all_live:
        print('RENDER DEPLOY COMPLETE')
        sys.exit(0)
    time.sleep(10)
