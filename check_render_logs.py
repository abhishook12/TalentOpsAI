import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')

r = requests.get('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
for s in r.json():
    if s['service']['name'] in ['talentops-api', 'TalentOpsAI-1']:
        srv_id = s['service']['id']
        dep = requests.get(f"https://api.render.com/v1/services/{srv_id}/deploys", headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
        latest = dep.json()[0]['deploy']
        if latest['status'] == 'update_failed':
            print(f"--- LOGS FOR {s['service']['name']} ---")
            deploy_id = latest['id']
            # Unfortunately Render API doesn't have an endpoint for deploy logs directly without a specific log stream or external integration? Wait, no, we can usually see logs in the dashboard, but let's check the API docs. 
            # Actually, Render doesn't expose deploy logs via API easily, only a stream. Let me just print the deploy object.
            import pprint
            pprint.pprint(latest)
            print("To see exact failure reason, we might need to look at the dashboard.")
