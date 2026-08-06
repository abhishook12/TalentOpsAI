import requests
import re
import sys

url = 'https://talent-ops-ai.vercel.app/admin/devices'
r = requests.get(url)
html = r.text

js_files = re.findall(r'src=\"/assets/(.*?\.js)\"', html)
if not js_files:
    print('No JS files found')
    sys.exit(1)

for js_file in js_files:
    js_url = f'https://talent-ops-ai.vercel.app/assets/{js_file}'
    js_r = requests.get(js_url)
    if 'f399f87' in js_r.text:
        print('SUCCESS: FIX (f399f87) VERIFIED IN VERCEL DEPLOYMENT!')
        sys.exit(0)

print('FAILED: New commit hash not found in any JS file. Vercel might still be building or serving old cache.')
sys.exit(1)
