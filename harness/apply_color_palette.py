import os
import re

SRC_DIR = r"C:\TalentOpsAI\frontend\src"

# Specific file-level transformations
def transform_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Direct Hex Replacements
    content = re.sub(r'#22[bB]8[cC][fF]', '#e41937', content)
    content = re.sub(r'#15aabf', '#fe063f', content)
    content = re.sub(r'#00eefc', '#e41937', content)
    content = re.sub(r'#38bdf8', '#fe063f', content)
    content = re.sub(r'#0ea5e9', '#e41937', content)
    content = re.sub(r'#0284c7', '#e41937', content)
    content = re.sub(r'#2563eb', '#e41937', content)
    content = re.sub(r'#3b82f6', '#e41937', content)
    content = re.sub(r'#1d4ed8', '#331219', content)

    # 2. Direct RGBA Replacements for Cyan/Blue
    content = re.sub(r'rgba\(\s*34\s*,\s*184\s*,\s*207\s*,\s*([0-9\.]+)\s*\)', r'rgba(228, 25, 55, \1)', content)
    content = re.sub(r'rgba\(\s*56\s*,\s*189\s*,\s*248\s*,\s*([0-9\.]+)\s*\)', r'rgba(228, 25, 55, \1)', content)
    content = re.sub(r'rgba\(\s*59\s*,\s*130\s*,\s*246\s*,\s*([0-9\.]+)\s*\)', r'rgba(228, 25, 55, \1)', content)
    content = re.sub(r'rgba\(\s*37\s*,\s*99\s*,\s*235\s*,\s*([0-9\.]+)\s*\)', r'rgba(228, 25, 55, \1)', content)
    content = re.sub(r'rgba\(\s*14\s*,\s*165\s*,\s*233\s*,\s*([0-9\.]+)\s*\)', r'rgba(228, 25, 55, \1)', content)

    # 3. Tailwind Classes for Cyan, Blue, Indigo, Sky
    # Backgrounds
    content = re.sub(r'\bbg-(?:cyan|blue|indigo|sky)-(?:500|600)\b', 'bg-[#e41937]', content)
    content = re.sub(r'\bbg-(?:cyan|blue|indigo|sky)-(?:700|800|900)\b', 'bg-[#18181b]', content)
    content = re.sub(r'\bbg-(?:cyan|blue|indigo|sky)-950\b', 'bg-[#0a0a0a]', content)
    content = re.sub(r'\bbg-(?:cyan|blue|indigo|sky)-(?:500|600)/(?:10|20|30)\b', 'bg-[#e41937]/15', content)
    content = re.sub(r'\bbg-(?:cyan|blue|indigo|sky)-(?:900|950)/(?:20|30|40|50)\b', 'bg-[#121212]', content)

    # Hover Backgrounds
    content = re.sub(r'\bhover:bg-(?:cyan|blue|indigo|sky)-(?:500|600)\b', 'hover:bg-[#fe063f]', content)
    content = re.sub(r'\bhover:bg-(?:cyan|blue|indigo|sky)-(?:700|800|900)\b', 'hover:bg-[#27272a]', content)

    # Text Colors
    content = re.sub(r'\btext-(?:cyan|blue|indigo|sky)-(?:400|300|200)\b', 'text-[#fe063f]', content)
    content = re.sub(r'\btext-(?:cyan|blue|indigo|sky)-(?:500|600)\b', 'text-[#e41937]', content)

    # Borders
    content = re.sub(r'\bborder-(?:cyan|blue|indigo|sky)-(?:400|500|600)\b', 'border-[#e41937]/50', content)
    content = re.sub(r'\bborder-(?:cyan|blue|indigo|sky)-(?:700|800|900)\b', 'border-white/10', content)
    content = re.sub(r'\bborder-(?:cyan|blue|indigo|sky)-(?:500|600)/(?:20|30|40)\b', 'border-[#e41937]/35', content)

    # Focus Rings
    content = re.sub(r'\b(?:ring|focus:ring)-(?:cyan|blue|indigo|sky)-(?:400|500|600)\b', 'focus:ring-[#e41937]', content)

    # Gradients
    content = re.sub(r'\bfrom-(?:cyan|blue|indigo|sky)-(?:400|500|600)\b', 'from-[#e41937]', content)
    content = re.sub(r'\bto-(?:cyan|blue|indigo|sky)-(?:400|500|600)\b', 'to-[#fe063f]', content)
    content = re.sub(r'\bvia-(?:cyan|blue|indigo|sky)-(?:400|500|600)\b', 'via-[#e41937]', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

modified_count = 0
for root, dirs, files in os.walk(SRC_DIR):
    for file in files:
        if file.endswith(('.jsx', '.js', '.tsx', '.ts', '.css')):
            fp = os.path.join(root, file)
            if transform_file(fp):
                modified_count += 1
                rel = os.path.relpath(fp, SRC_DIR)
                print(f"Updated: {rel}")

print(f"\nDone! Successfully updated {modified_count} files across the frontend.")
