import os
import re

found = 0
for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.css'):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                content = f.read()
                
            matches = re.findall(r'(#fff|#ffffff|rgba\(255,\s*255,\s*255,[^\)]+\)|#000|#000000|rgba\(0,\s*0,\s*0,[^\)]+\))', content, re.IGNORECASE)
            if matches:
                print(f"{os.path.join(root, file)}: {len(matches)} matches")
                found += len(matches)

print(f"Total hardcoded colors found: {found}")
