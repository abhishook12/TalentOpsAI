import os
import requests, json
RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
headers = {'authorization': f'Bearer {RENDER_API_KEY}', 'accept': 'application/json'}
resp = requests.get('https://api.render.com/v1/services/srv-d8bkagugvqtc73cvie6g/env-vars', headers=headers)
vars_dict = {ev['envVar']['key']: ev['envVar']['value'] for ev in resp.json()}
print("SUPABASE_URL:", vars_dict.get("SUPABASE_URL", "NOT FOUND")[:30])
print("SUPABASE_KEY:", vars_dict.get("SUPABASE_KEY", "NOT FOUND")[:20])

with open("C:/TalentOpsAI/backend/.env", "a") as f:
    if "SUPABASE_URL" in vars_dict:
        f.write(f"\nSUPABASE_URL={vars_dict['SUPABASE_URL']}\n")
    if "SUPABASE_KEY" in vars_dict:
        f.write(f"SUPABASE_KEY={vars_dict['SUPABASE_KEY']}\n")
