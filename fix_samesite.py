import re
path = 'C:\\TalentOpsAI\\backend\\app\\routes\\auth.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'samesite="lax"', 
    r'samesite="none" if IS_PRODUCTION else "lax"', 
    content
)

content = re.sub(
    r'SameSite=Lax',
    r'SameSite=None',
    content
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated auth.py SameSite cookies')
