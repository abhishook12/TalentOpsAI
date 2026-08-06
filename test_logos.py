import requests
import re
import json

with open('frontend/src/utils/domain.js', 'r') as f:
    content = f.read()

match = re.search(r'export const knownStaffingDomains = (\{.*?\})', content, re.DOTALL)
if match:
    obj_str = match.group(1).replace("'", '"')
    domains = list(set(re.findall(r':\s*"([^"]+)"', obj_str)))
    
    print(f'Found {len(domains)} unique known domains.')
    
    success = 0
    failed = []
    
    for domain in domains:
        url = f'https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128'
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                success += 1
            else:
                failed.append((domain, res.status_code))
        except Exception as e:
            failed.append((domain, str(e)))
            
    print(f'Success: {success}/{len(domains)}')
    if failed:
        print('Failed domains:')
        for d, s in failed:
            print(f'  {d} ({s})')
else:
    print('Could not parse domains.')
