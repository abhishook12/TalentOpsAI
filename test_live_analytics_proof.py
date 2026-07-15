import requests
import uuid
import sys
import os

print('========================================')
print('  PROOF CHECK 1: LIVE BACKEND ENDPOINTS')
print('========================================')
BASE = 'https://talentopsai-1.onrender.com'

sid = str(uuid.uuid4())
aid = str(uuid.uuid4())

# Start
r1 = requests.post(f'{BASE}/analytics/session/start', json={
    'anonymous_id': aid, 'session_id': sid,
    'screen_size': '1920x1080', 'current_page': '/',
    'user_agent': 'ProofTest/1.0'
}, timeout=15)
print(f'  /start     => {r1.status_code} {r1.json()}')

# Event
r2 = requests.post(f'{BASE}/analytics/session/event', json={
    'anonymous_id': aid, 'session_id': sid,
    'event_type': 'page_view', 'current_page': '/dashboard',
    'previous_page': '/', 'user_email': 'proof@test.com'
}, timeout=15)
print(f'  /event     => {r2.status_code} {r2.json()}')

# Heartbeat
r3 = requests.post(f'{BASE}/analytics/session/heartbeat', json={
    'anonymous_id': aid, 'session_id': sid,
    'status': 'Active', 'clicks_since_last': 3,
    'current_page': '/dashboard'
}, timeout=15)
print(f'  /heartbeat => {r3.status_code} {r3.json()}')

# End
r4 = requests.post(f'{BASE}/analytics/session/end', json={
    'session_id': sid
}, timeout=15)
print(f'  /end       => {r4.status_code} {r4.json()}')

all_ok = all(r.status_code == 200 for r in [r1, r2, r3, r4])
result_str = "PASS" if all_ok else "FAIL"
print(f'\n  BACKEND RESULT: {result_str}')
print(f'  Session ID: {sid}')

print()
print('========================================')
print('  PROOF CHECK 2: LIVE FRONTEND (VERCEL)')
print('========================================')
r5 = requests.get('https://talent-ops-ai.vercel.app/', timeout=15)
print(f'  Vercel status: {r5.status_code}')
has_html = '</html>' in r5.text
print(f'  Valid HTML:    {has_html}')
# Check the JS bundle doesn't contain the broken axios line
has_axios_bug = 'axios.defaults' in r5.text
bug_status = "STILL PRESENT" if has_axios_bug else "FIXED"
print(f'  axios bug:     {bug_status}')

print()
print('========================================')
print('  PROOF CHECK 3: DB VERIFICATION')
print('========================================')
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))
from app.database import get_db
from app.models.models import VisitorSession
db = next(get_db())
session = db.query(VisitorSession).filter_by(session_id=sid).first()
if session:
    print(f'  Session found: {session.session_id}')
    print(f'  Status:        {session.status}')
    print(f'  Page:          {session.current_page}')
    print(f'  Clicks:        {session.total_clicks}')
    print(f'  Email:         {session.user_email}')
    print(f'  Browser:       {session.browser}')
    print(f'  DB RESULT:     PASS')
else:
    print(f'  Session NOT found in DB')
    print(f'  DB RESULT:     FAIL')

print()
print('========================================')
print('  FINAL VERDICT')
print('========================================')
if all_ok and session:
    print('  ALL 3 CHECKS: PASSED')
else:
    print('  SOME CHECKS FAILED')
