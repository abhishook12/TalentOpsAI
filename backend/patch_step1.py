import re

with open('backend/enrich_recruiter_contacts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. extract_names
old_extract = '''    def extract_names(self, full_name: str, email: str = None) -> Tuple[str, str]:
        if not full_name:
            return "", ""'''
new_extract = '''    def extract_names(self, full_name: str, email: str = None) -> Tuple[str, str]:
        if email and ("@missing.local" in email or "@invalid.local" in email or "@example.com" in email):
            email = None
        if not full_name:
            return "", ""'''
content = content.replace(old_extract, new_extract)

# 2. process_recruiter start existing check
old_proc1 = '''        is_placeholder = False
        if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email):
            is_placeholder = True

        if r.email and str(r.email).strip() and not is_placeholder:'''
new_proc1 = '''        is_placeholder = False
        if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email or "@example.com" in r.email):
            is_placeholder = True

        if r.email and str(r.email).strip() and not is_placeholder:'''
content = content.replace(old_proc1, new_proc1)

# 3. get_email_pattern in global?
# Let's check get_email_pattern usages of email
# The grep search didn't show get_email_pattern checking it, but let's check.
