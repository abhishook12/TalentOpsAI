import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if "alert(" not in content:
        return

    # Basic replacements
    content = content.replace("alert('Settings saved successfully!');", "toast.success('Settings saved successfully!');")
    content = content.replace("alert(\"User has been logged out.\");", "toast.success(\"User has been logged out.\");")
    
    # Catch all error alerts
    content = re.sub(r'return alert\((.*?)\)', r'return toast.error(\1)', content)
    content = re.sub(r'alert\((.*?failed.*?|.*?Error.*?|.*?error.*?)\)', r'toast.error(\1)', content, flags=re.IGNORECASE)
    content = re.sub(r'alert\((.*?)\)', r'toast.error(\1)', content) # default to error for remaining

    # Check if toast is imported
    if "from 'react-hot-toast'" not in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import '):
                lines.insert(i, "import { toast } from 'react-hot-toast'")
                break
        content = '\n'.join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            process_file(os.path.join(root, file))

print("Global alerts replaced.")
