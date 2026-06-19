import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')

render_key = os.getenv('RENDER_API_KEY')
vercel_key = os.getenv('VERCEL_TOKEN')

print("--- RENDER SERVICES ---")
r = requests.get('https://api.render.com/v1/services', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
if r.status_code == 200:
    for s in r.json():
        print(f"Service: {s['service']['name']} ({s['service']['id']}) - Type: {s['service']['type']}")
        
        # Get deploys for service
        dep = requests.get(f"https://api.render.com/v1/services/{s['service']['id']}/deploys", headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
        if dep.status_code == 200 and dep.json():
            latest = dep.json()[0]['deploy']
            print(f"  Latest Deploy: {latest['id']} | Status: {latest['status']} | Created: {latest['createdAt']}")
            if latest['status'] != 'live':
                print("  => Deploy issue detected!")
else:
    print(f"Failed to fetch Render services: {r.text}")

print("\n--- VERCEL PROJECTS ---")
v = requests.get('https://api.vercel.com/v9/projects', headers={'Authorization': f'Bearer {vercel_key}'})
if v.status_code == 200:
    for p in v.json().get('projects', []):
        print(f"Project: {p['name']} ({p['id']})")
        # Get latest deployments
        dep_v = requests.get(f"https://api.vercel.com/v6/deployments?projectId={p['id']}", headers={'Authorization': f'Bearer {vercel_key}'})
        if dep_v.status_code == 200 and dep_v.json().get('deployments'):
            latest_v = dep_v.json()['deployments'][0]
            print(f"  Latest Deploy: {latest_v['uid']} | State: {latest_v['state']} | Created: {latest_v['created']}")
            if latest_v['state'] == 'ERROR':
                print("  => Vercel Deploy Error detected!")
else:
    print(f"Failed to fetch Vercel projects: {v.text}")
