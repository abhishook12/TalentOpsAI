import os
import re

files_to_process = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.jsx', '.js', '.tsx', '.ts')):
            files_to_process.append(os.path.join(root, f))

# Mappings of stray hex codes to 4-color palette:
# Black: #000000
# White: #ffffff
# Crimson Red: #e41937, #fe063f
# Grey: #121212, #18181b, #27272a, #71717a, #a1a1aa, #d4d4d8

hex_replacements = [
    # Emerald / Green variants -> White or Grey
    (r'#4ade80\b', '#ffffff'),
    (r'#22c55e\b', '#ffffff'),
    (r'#10b981\b', '#ffffff'),
    (r'#16a34a\b', '#ffffff'),
    (r'#86efac\b', '#ffffff'),
    (r'#15803d\b', '#a1a1aa'),
    (r'#059669\b', '#ffffff'),
    (r'#047857\b', '#a1a1aa'),

    # Amber / Orange / Yellow -> White, Muted Grey (#a1a1aa), or Crimson Red (#e41937)
    (r'#fbbf24\b', '#a1a1aa'),
    (r'#f59e0b\b', '#a1a1aa'),
    (r'#d97706\b', '#e41937'),
    (r'#b45309\b', '#e41937'),
    (r'#eab308\b', '#a1a1aa'),
    (r'#facc15\b', '#a1a1aa'),
    (r'#ca8a04\b', '#e41937'),
    (r'#f97316\b', '#e41937'),
    (r'#ea580c\b', '#e41937'),

    # Red variants -> Standardize to #e41937 or #fe063f
    (r'#f87171\b', '#e41937'),
    (r'#ef4444\b', '#e41937'),
    (r'#dc2626\b', '#e41937'),
    (r'#b91c1c\b', '#c0152e'),
    (r'#ff4444\b', '#e41937'),
    (r'#f43f5e\b', '#e41937'),

    # Blue / Cyan / Sky / Indigo / Purple -> Standardize to #e41937 (accent) or #ffffff
    (r'#60a5fa\b', '#e41937'),
    (r'#3b82f6\b', '#e41937'),
    (r'#2563eb\b', '#e41937'),
    (r'#1d4ed8\b', '#e41937'),
    (r'#93c5fd\b', '#e41937'),
    (r'#38bdf8\b', '#e41937'),
    (r'#0ea5e9\b', '#e41937'),
    (r'#0284c7\b', '#e41937'),
    (r'#22d3ee\b', '#e41937'),
    (r'#06b6d4\b', '#e41937'),
    (r'#0891b2\b', '#e41937'),
    (r'#67e8f9\b', '#ffffff'),
    (r'#0078d4\b', '#e41937'),
    (r'#8b5cf6\b', '#e41937'),
    (r'#a855f7\b', '#e41937'),
    (r'#7c3aed\b', '#e41937'),
    (r'#9333ea\b', '#e41937'),
    (r'#c084fc\b', '#fe063f'),
    (r'#6366f1\b', '#e41937'),
    (r'#4f46e5\b', '#e41937'),
    (r'#818cf8\b', '#fe063f'),

    # Dark blue/indigo surfaces -> Pure black/grey
    (r'#0f172a\b', '#000000'),
    (r'#1e293b\b', '#121212'),
    (r'#334155\b', '#27272a'),
    (r'#475569\b', '#71717a'),
    (r'#64748b\b', '#a1a1aa'),
    (r'#94a3b8\b', '#d4d4d8'),
    (r'#cbd5e1\b', '#e4e4e7'),
    (r'#f1f5f9\b', '#18181b'),
    (r'#f8fafc\b', '#000000'),
    (r'#111116\b', '#121212'),
    (r'#24242e\b', '#27272a'),
    (r'#0b0b0e\b', '#000000'),
    (r'#1a1a24\b', '#121212'),
    (r'#1e1e2d\b', '#121212'),
    (r'#14141f\b', '#0a0a0a'),
    (r'#171722\b', '#0a0a0a'),
]

modified = 0
for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    new_content = content
    for pattern, repl in hex_replacements:
        new_content = re.sub(pattern, repl, new_content, flags=re.IGNORECASE)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        modified += 1
        print(f"Purged hex in: {filepath}")

print(f"\nTotal files cleaned: {modified}")
