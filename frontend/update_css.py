import json
import re

with open('c:/TalentOpsAI/frontend/tailwind.config.js', 'r') as f:
    text = f.read()

# Extract colors manually
colors = {}
for line in text.splitlines():
    if ':' in line and '#' in line:
        parts = line.split(':')
        key = parts[0].replace('"', '').replace("'", '').strip()
        val = parts[1].replace('"', '').replace("'", '').replace(',', '').strip()
        colors[key] = val

with open('c:/TalentOpsAI/frontend/src/index.css', 'r') as f:
    css = f.read()

theme_block = '\n@theme {\n'
for k, v in colors.items():
    theme_block += f'  --color-{k}: {v};\n'
theme_block += '}\n'

new_css = theme_block + '\n' + css
with open('c:/TalentOpsAI/frontend/src/index.css', 'w') as f:
    f.write(new_css)
print('Updated index.css with @theme block.')
