import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')
vercel_key = os.getenv('VERCEL_TOKEN')

print("--- RENDER BACKEND DEPLOYMENTS ---")
if render_key:
    r = requests.get('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
    if r.status_code == 200:
        for s in r.json():
            if s['service']['name'] in ['talentops-api', 'TalentOpsAI-1']:
                dep = requests.get(f"https://api.render.com/v1/services/{s['service']['id']}/deploys", headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
                if dep.status_code == 200:
                    latest = dep.json()[0]['deploy']
                    print(f"{s['service']['name']} -> Status: {latest['status']}, Commit: {latest['commit']['id'][:7] if 'commit' in latest and latest['commit'] else 'N/A'}")
                    print(f"URL: {s['service']['serviceDetails'].get('url')}")
else:
    print("No Render key")

print("\n--- VERCEL FRONTEND DEPLOYMENTS ---")
if vercel_key:
    project_id = 'prj_4TFHAL3GkqvEoIcIg3R7yLdTaKr3'
    headers = {
        'Authorization': f'Bearer {vercel_key}',
        'Accept': 'application/json'
    }
    r = requests.get(f'https://api.vercel.com/v6/deployments?projectId={project_id}&limit=3', headers=headers)
    if r.status_code == 200:
        for d in r.json().get('deployments', []):
            commit = d.get('meta', {}).get('githubCommitSha', 'N/A')
            print(f"Deployment: {d['uid']} -> Status: {d['state']}, Commit: {commit[:7] if commit != 'N/A' else 'N/A'}")
            print(f"URL: https://{d['url']}")
    else:
        print(f"Failed Vercel check: {r.status_code}")
else:
    print("No Vercel key")
