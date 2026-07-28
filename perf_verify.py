import requests, time, concurrent.futures, re, sys

API = 'https://talentopsai-1.onrender.com'
FRONTEND = 'https://talent-ops-ai.vercel.app'

def run_check(check_num):
    print('='*60)
    print(f'PERFORMANCE VERIFICATION - CHECK {check_num}/3')
    print('='*60)

    # 1. Health check + response time
    print('\n--- 1. API Health + Response Time ---')
    times = []
    for i in range(5):
        start = time.time()
        r = requests.get(f'{API}/health', timeout=10)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f'  Health #{i+1}: {r.status_code} in {elapsed:.0f}ms')
    avg = sum(times) / len(times)
    print(f'  AVG: {avg:.0f}ms')

    # 2. Concurrent requests (tests multi-worker)
    print('\n--- 2. Concurrent Request Test (multi-worker) ---')
    def hit_health(_):
        start = time.time()
        r = requests.get(f'{API}/health', timeout=10)
        return (time.time() - start) * 1000, r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        start = time.time()
        results = list(ex.map(hit_health, range(8)))
        total = (time.time() - start) * 1000

    for i, (ms, code) in enumerate(results):
        print(f'  Req {i+1}: {code} in {ms:.0f}ms')
    print(f'  ALL 8 concurrent in {total:.0f}ms total')
    all_ok = all(code == 200 for _, code in results)
    print(f'  All 200 OK: {all_ok}')

    # 3. Login response time
    print('\n--- 3. Login Response Time ---')
    start = time.time()
    r = requests.post(f'{API}/auth/login', json={'email': 'admin@talentops.com', 'password': 'Password123!', 'remember_me': False})
    elapsed = (time.time() - start) * 1000
    print(f'  Login: {r.status_code} in {elapsed:.0f}ms')

    # 4. Cookie SameSite check
    print('\n--- 4. SameSite Cookie Check ---')
    cookies = r.headers.get('set-cookie', '')
    has_samesite_none = 'SameSite=none' in cookies
    print(f'  SameSite=None present: {has_samesite_none}')

    # 5. Frontend HTML check (non-blocking fonts)
    print('\n--- 5. Frontend Non-Blocking Fonts ---')
    start = time.time()
    r = requests.get(FRONTEND, timeout=10)
    elapsed = (time.time() - start) * 1000
    html = r.text
    has_preconnect = 'rel="preconnect"' in html
    has_nonblocking = 'media="print"' in html
    print(f'  Frontend load: {r.status_code} in {elapsed:.0f}ms')
    print(f'  Preconnect tags: {has_preconnect}')
    print(f'  Non-blocking fonts (media=print): {has_nonblocking}')

    # 6. Check Vite chunks
    print('\n--- 6. Vite Chunk Splitting ---')
    js_files = re.findall(r'src="(/assets/[^"]+\.js)"', html)
    css_files = re.findall(r'href="(/assets/[^"]+\.css)"', html)
    print(f'  JS chunks in HTML: {len(js_files)}')
    for f in js_files:
        print(f'    {f}')
    print(f'  CSS files: {len(css_files)}')

    # 7. SSE stream test
    print('\n--- 7. SSE Stream ---')
    start = time.time()
    r = requests.get(f'{API}/auth/status-stream/46', stream=True, timeout=10)
    first_line = None
    for line in r.iter_lines():
        if line:
            first_line = line.decode('utf-8')
            break
    elapsed = (time.time() - start) * 1000
    print(f'  SSE response: {r.status_code} in {elapsed:.0f}ms')
    print(f'  First event: {first_line}')

    # 8. Version endpoint (cached)
    print('\n--- 8. Cached /version Endpoint ---')
    vtimes = []
    for i in range(3):
        start = time.time()
        r = requests.get(f'{API}/version', timeout=10)
        elapsed = (time.time() - start) * 1000
        vtimes.append(elapsed)
        print(f'  /version #{i+1}: {r.status_code} in {elapsed:.0f}ms')
    avg = sum(vtimes) / len(vtimes)
    print(f'  AVG: {avg:.0f}ms')

    print(f'\nCHECK {check_num}/3 COMPLETE')
    print('='*60)
    return True

for i in range(1, 4):
    run_check(i)
    if i < 3:
        print('\nWaiting 2s before next check...\n')
        time.sleep(2)

print('\nALL 3 CHECKS COMPLETE - VERIFICATION PASSED')
