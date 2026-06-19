import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')
correct_db_url = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

services = ['srv-d8bkagugvqtc73cvie6g', 'srv-d8hdoqs2m8qs73b1o9q0'] # Prod, Staging

headers = {
    'Authorization': f'Bearer {render_key}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

for sid in services:
    # Get current vars
    print(f"Fetching vars for {sid}...")
    r = requests.get(f'https://api.render.com/v1/services/{sid}/env-vars', headers=headers)
    if r.status_code != 200:
        print(f"Failed to fetch for {sid}: {r.text}")
        continue
    
    current_vars = r.json()
    new_vars = []
    
    for v in current_vars:
        key = v['envVar']['key']
        val = v['envVar']['value']
        
        # Override the database URLs
        if key in ['DATABASE_URL', 'SUPABASE_DATABASE_URL']:
            new_vars.append({'key': key, 'value': correct_db_url})
        else:
            new_vars.append({'key': key, 'value': val})
            
    # Check if DATABASE_URL was missing, if so add it
    keys_present = [v['key'] for v in new_vars]
    if 'DATABASE_URL' not in keys_present:
        new_vars.append({'key': 'DATABASE_URL', 'value': correct_db_url})
        
    print(f"Updating vars for {sid}...")
    put_req = requests.put(f'https://api.render.com/v1/services/{sid}/env-vars', headers=headers, json=new_vars)
    if put_req.status_code in [200, 201]:
        print(f"Successfully updated {sid}!")
    else:
        print(f"Failed to update {sid}: {put_req.text}")
