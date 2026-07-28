import os
import sys
import json
import urllib.request
import urllib.error

# Add backend directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.database import SessionLocal
from app.models.auth_models import User
from app.services.auth_service import create_access_token
from datetime import timedelta

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@talentops.com").first()
token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=30))

try:
    # Create campaign first to get a valid cid
    req_camp = urllib.request.Request('http://127.0.0.1:8000/campaigns/', data=json.dumps({"name":"test", "from_email": "admin@talentops.com"}).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    res_camp = urllib.request.urlopen(req_camp)
    cid = json.loads(res_camp.read())['campaign_id']
    
    # Create template
    req_tpl = urllib.request.Request(f'http://127.0.0.1:8000/campaigns/{cid}/templates', data=json.dumps({"name":"test", "subject": "test", "body": "test"}).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    urllib.request.urlopen(req_tpl)
    
    # Now enroll emails
    req2 = urllib.request.Request(f'http://127.0.0.1:8000/campaigns/{cid}/enroll-emails', data=json.dumps({'recipients': [{'email': 'admin@talentops.com', 'status': 'valid'}]}).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    res2 = urllib.request.urlopen(req2)
    print("SUCCESS:", res2.read().decode())
except urllib.error.HTTPError as e:
    print('ERROR CODE:', e.code)
    print('ERROR BODY:', e.read().decode())

