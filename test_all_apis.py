import requests, time

API = 'http://127.0.0.1:8000'

s = requests.Session()
r = s.post(f'{API}/auth/login', json={'email':'admin@talentops.com','password':'Password123!','remember_me':False})
print(f'Login: {r.status_code}')
token = r.json().get('token','')

headers = {'Authorization': f'Bearer {token}'}

endpoints = [
    ('GET', '/analytics/dashboard'),
    ('GET', '/analytics/data-quality'),
    ('GET', '/analytics/visit-stats'),
    ('GET', '/analytics/companies-search?state=ALL&limit=6&skip=0&min_recruiters=1'),
    ('GET', '/version'),
    ('GET', '/admin/devices/pending/count'),
    ('GET', '/notifications'),
    ('GET', '/updates/status'),
    ('GET', '/recruiters/?page=1&limit=50'),
    ('GET', '/analytics/taxonomy-distribution'),
    ('GET', '/sentinel/health'),
    ('GET', '/campaigns?page=1&limit=20'),
    ('GET', '/auth/me'),
    ('GET', '/analytics/data-health'),
    ('GET', '/analytics/enrichment-feed'),
    ('GET', '/admin/stats'),
    ('GET', '/users/analytics'),
    ('GET', '/admin/visitor-analytics/overview'),
]

print()
for method, ep in endpoints:
    start = time.time()
    try:
        r = s.get(f'{API}{ep}', headers=headers, timeout=15, cookies=s.cookies)
        elapsed = (time.time() - start) * 1000
        body_size = len(r.text)
        status_icon = 'OK' if r.status_code < 400 else 'FAIL'
        print(f'  [{status_icon:4s}] {r.status_code} {elapsed:7.0f}ms {body_size:7d}b  {ep}')
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f'  [ERR ] --- {elapsed:7.0f}ms         {ep}  ({str(e)[:50]})')
