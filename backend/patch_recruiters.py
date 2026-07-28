import re
import sys

with open(r'C:\TalentOpsAI\backend\app\routes\recruiters.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove Recruiter.user_id == current_user.id from filter() calls
# This makes reads global.
content = re.sub(r'Recruiter\.user_id == current_user\.id,\s*', '', content)
content = re.sub(r'Recruiter\.user_id == current_user\.id\)', ')', content)
content = re.sub(r'\.filter\(Recruiter\.user_id == current_user\.id\)', '', content)

# Remove user_id=current_user.id from Recruiter(...) instantiations
# We still want to track who created it, but wait, does Recruiter even have a user_id?
# Yes, it does. But let's leave user_id on creation so we know who made it.

# Now we need to add admin checks to mutations.
# The user wants "read-only access" for regular users.
# We should add:
# is_admin = current_user.role and current_user.role.name.lower() in ('admin', 'superadmin')
# if not is_admin: raise HTTPException(403, "Not authorized to modify global recruiter database")

mutations = [
    "@router.post(\"/import-sheet\")",
    "@router.post(\"/upload\")",
    "@router.post(\"/\")",
    "@router.put(\"/{recruiter_id}\")",
    "@router.delete(\"/{recruiter_id}\")",
    "@router.post(\"/bulk-delete\")",
    "@router.post(\"/bulk-edit\")",
    "@router.post(\"/delete-all\")",
    "@router.post(\"/{recruiter_id}/verify\")"
]

admin_check = """
    is_admin = current_user.role and current_user.role.name.lower() in ('admin', 'superadmin')
    if not is_admin:
        raise HTTPException(status_code=403, detail="Read-only access: Cannot modify global recruiter database")
"""

for mut in mutations:
    # Find the function def after the decorator
    # e.g., @router.post("/")\ndef create_recruiter(...):\n
    pattern = re.compile(re.escape(mut) + r'\s+def\s+[a-zA-Z0-9_]+\(.*?\)\s*(?:->\s*.*?)?:\n', re.DOTALL)
    match = pattern.search(content)
    if match:
        end = match.end()
        # insert admin_check
        content = content[:end] + admin_check + content[end:]

with open(r'C:\TalentOpsAI\backend\app\routes\recruiters.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("recruiters.py patched successfully.")
