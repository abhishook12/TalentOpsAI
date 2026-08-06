import requests
import re
import sys

url = 'https://talent-ops-ai.vercel.app/admin/devices'
print('Fetching index.html...')
r = requests.get(url)
html = r.text

match = re.search(r'src=\"/assets/(index-[^\"]+\.js)\"', html)
if not match:
    print('Could not find JS asset in HTML')
    sys.exit(1)

js_file = match.group(1)
js_url = f'https://talent-ops-ai.vercel.app/assets/{js_file}'
print(f'Fetching JS bundle: {js_url}')

js_r = requests.get(js_url)
js_code = js_r.text

if 'String(' in js_code and 'charCodeAt(0)' in js_code:
    for line in js_code.split(';'):
         if 'charCodeAt(0)' in line:
             print('Found line:', line.strip())
             if 'String(' in line:
                 print('✅ FIX CONFIRMED IN VERCEL DEPLOYMENT!')
                 sys.exit(0)
             else:
                 print('❌ FIX NOT FOUND IN LINE!')
                 sys.exit(1)
else:
    if 'charCodeAt(0)' in js_code:
        print('❌ OLD CODE FOUND! Vercel is still running the old deployment.')
        for line in js_code.split(';'):
            if 'charCodeAt(0)' in line:
                print('Line:', line.strip())
        sys.exit(1)
    print('❌ Could not find the code snippet at all.')
    sys.exit(1)
