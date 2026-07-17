import os
import glob
import re

for filepath in glob.glob('C:/TalentOpsAI/frontend/src/**/*.jsx', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    
    # We replace var(--text-inverse) with var(--text-primary) everywhere except in buttons with var(--accent)
    # Wait, it's easier to just replace all var(--text-inverse) with var(--text-primary) first
    content = content.replace("color: 'var(--text-inverse)'", "color: 'var(--text-primary)'")
    
    # Now for buttons or badges that explicitly had var(--accent) or #3b82f6 or #ef4444 or #dc2626 or #059669
    # We should make their color #ffffff (always white text on solid color buttons)
    content = re.sub(r"background:\s*'(var\(--accent\)|#3b82f6|#ef4444|#dc2626|#059669)',\s*color:\s*'var\(--text-primary\)'", r"background: '\1', color: '#ffffff'", content)
    
    # Also if the background is var(--text-primary) (e.g. inverted badge), text should be var(--main-bg)
    content = re.sub(r"background:\s*'var\(--text-primary\)',\s*color:\s*'var\(--text-primary\)'", r"background: 'var(--text-primary)', color: 'var(--main-bg)'", content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")
