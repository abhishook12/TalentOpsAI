import requests
import os
from dotenv import load_dotenv

load_dotenv('.env.deploy')
render_key = os.getenv('RENDER_API_KEY')

# Fetch deploy details to see if there is an error message
r = requests.get('https://api.render.com/v1/services/srv-d8hdoqs2m8qs73b1o9q0/deploys/dep-d8or9d8g4nts73f8sl60', headers={'Authorization': f'Bearer {render_key}', 'Accept': 'application/json'})
print(r.json())
