import requests
import os
import json
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')

r2 = requests.get('https://api.render.com/v1/services/srv-d8hdoqs2m8qs73b1o9q0', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
print(json.dumps(r2.json(), indent=2))
