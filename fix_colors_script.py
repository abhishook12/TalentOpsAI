import os
import re

replacements = [
    (r"color:\s*['\"]rgba\(255,\s*255,\s*255,\s*0\.6\)['\"]", "color: 'var(--text-muted)'"),
    (r"color:\s*['\"]rgba\(255,\s*255,\s*255,\s*0\.5\)['\"]", "color: 'var(--text-secondary)'"),
    (r"color:\s*['\"]rgba\(255,\s*255,\s*255,\s*0\.4\)['\"]", "color: 'var(--text-muted)'"),
    (r"color:\s*['\"]rgba\(255,\s*255,\s*255,\s*0\.7\)['\"]", "color: 'var(--text-secondary)'"),
    (r"color=[\"']rgba\(255,\s*255,\s*255,\s*0\.[4567]\)[\"']", "color=\"var(--text-muted)\""),
    (r"color:\s*['\"]#f3f3f3['\"]", "color: 'var(--text-primary)'"),
    (r"background:\s*['\"]#fff['\"]", "background: 'var(--text-primary)'"),
    (r"color:\s*['\"]#000['\"]", "color: 'var(--main-bg)'"),
]

changed_files = 0
for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements:
                new_content = re.sub(old, new, new_content, flags=re.IGNORECASE)
                
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                changed_files += 1

print(f"Fixed colors in {changed_files} files.")
