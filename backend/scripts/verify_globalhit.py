"""3-check verification for Global HIT roster upload."""
import sys, os, requests, time

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.services.recruiter_store import recruiter_store

print('=== CHECK 1: PARQUET DATASET QUERY ===')
recruiter_store._loaded = False
recruiter_store._ensure_loaded()
conn = recruiter_store._conn

df = conn.execute("""
    SELECT recruiter_id, recruiter_name, email, title, seniority_level, quality_score, email_status, logo_url, linkedin
    FROM recruiters
    WHERE LOWER(email) LIKE '%@globalhit.com'
    ORDER BY recruiter_id
""").df()
print(f'Total @globalhit.com profiles: {len(df)}')
for _, r in df.iterrows():
    print(f'  {r["recruiter_id"]:>8} | {r["recruiter_name"]:25s} | {r["email"]:30s} | {r["seniority_level"]:28s} | QS:{r["quality_score"]} | {r["email_status"]}')
assert len(df) >= 35, f'Expected 35+ profiles, got {len(df)}'
print('  [PASSED] Check 1!')

print()
print('=== CHECK 2: API SEARCH VERIFICATION ===')
for _ in range(10):
    try:
        r = requests.get('http://127.0.0.1:8000/health', timeout=1)
        if r.status_code == 200: break
    except: time.sleep(1)

res_auth = requests.post('http://127.0.0.1:8000/auth/login', json={'email': 'admin@talentops.ai', 'password': 'Admin@12345'})
token = res_auth.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
search_res = requests.get('http://127.0.0.1:8000/recruiters?search=globalhit&limit=40', headers=headers)
data = search_res.json()
print(f'API Search matched {data.get("total_count")} for keyword "globalhit"')
assert data.get('total_count') >= 35
print('  [PASSED] Check 2!')

print()
print('=== CHECK 3: KEY PROFILE SPOT-CHECK ===')
spot_checks = [
    ('Nash Castle', 'ncastle@globalhit.com'),
    ('Jack Lanni', 'jlanni@globalhit.com'),
    ('Mia DeGuzman', 'mdeguzman@globalhit.com'),
]
for name_check, email_check in spot_checks:
    row = conn.execute(f"SELECT recruiter_name, email, seniority_level, quality_score, email_status, linkedin, logo_url FROM recruiters WHERE LOWER(email) = '{email_check}'").fetchone()
    assert row is not None, f'{name_check} not found!'
    assert row[4] == 'verified', f'{name_check} not verified'
    assert row[3] >= 80, f'{name_check} low quality'
    assert 'linkedin.com' in (row[5] or ''), f'{name_check} missing linkedin'
    assert 'http' in (row[6] or ''), f'{name_check} missing logo'
    print(f'  {name_check:20s} | {row[1]:30s} | {row[2]:28s} | QS:{row[3]} | {row[4]} | LinkedIn OK | Logo OK')
print('  [PASSED] Check 3!')

print()
total = conn.execute('SELECT COUNT(*) FROM recruiters').fetchone()[0]
print(f'Total Dataset: {total:,} recruiters')
print('ALL 3 CHECKS PASSED!')
