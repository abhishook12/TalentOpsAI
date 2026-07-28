import re

with open(r'C:\TalentOpsAI\backend\app\routes\companies.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'Company\.user_id == current_user\.id,\s*', '', content)
content = re.sub(r'Company\.user_id == current_user\.id\)', ')', content)
content = re.sub(r'\.filter\(Company\.user_id == current_user\.id\)', '', content)

mutations = [
    "@router.post(\"/\")",
    "@router.put(\"/{company_id}\")",
    "@router.delete(\"/{company_id}\")"
]

admin_check = """
    is_admin = current_user.role and current_user.role.name.lower() in ('admin', 'superadmin')
    if not is_admin:
        raise HTTPException(status_code=403, detail="Read-only access: Cannot modify global company database")
"""

for mut in mutations:
    pattern = re.compile(re.escape(mut) + r'\s+def\s+[a-zA-Z0-9_]+\(.*?\)\s*(?:->\s*.*?)?:\n', re.DOTALL)
    match = pattern.search(content)
    if match:
        end = match.end()
        content = content[:end] + admin_check + content[end:]

with open(r'C:\TalentOpsAI\backend\app\routes\companies.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("companies.py patched successfully.")
