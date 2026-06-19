import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')

r = requests.get('https://api.render.com/v1/services/srv-d8bkagugvqtc73cvie6g/env-vars', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
print("ENV VARS:")
for e in r.json():
    print(f"  {e['envVar']['key']} = {e['envVar']['value']}")
