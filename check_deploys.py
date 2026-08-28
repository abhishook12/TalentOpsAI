import os
import requests, json
RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
headers = {'accept': 'application/json', 'authorization': f'Bearer {RENDER_API_KEY}'}
res = requests.get('https://api.render.com/v1/services/srv-d8bkagugvqtc73cvie6g/deploys?limit=2', headers=headers).json()
for d in res:
    dep = d['deploy']
    print(f"{dep['id']} ({dep['commit']['id'][:7]}): {dep['status']} ({dep['createdAt']} -> {dep.get('finishedAt', 'None')})")
