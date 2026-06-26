import re

with open('backend/enrich_recruiter_contacts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Bug 1
old1 = '''        # 6. Evaluate existing email
        if r.email and str(r.email).strip():'''
new1 = '''        # 6. Evaluate existing email
        is_placeholder = False
        if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email):
            is_placeholder = True

        if r.email and str(r.email).strip() and not is_placeholder:'''
content = content.replace(old1, new1)

# Bug 2
old2_def = '''    def is_human_name(self, name: str, company_name: str = "") -> bool:'''
new2_def = '''    def is_human_name(self, name: str, company_name: str = "", existing_email: str = "") -> bool:'''
content = content.replace(old2_def, new2_def)

old2_logic = '''        # Reject initials (like "J. Smith" or single letter first names)
        if any(len(p) == 1 for p in parts):
            return False'''
new2_logic = '''        # Reject initials (like "J. Smith" or single letter first names)
        # UNLESS the existing email already confirms that exact pattern
        if any(len(p) == 1 for p in parts):
            corroborated = False
            if existing_email and "@" in existing_email and "missing.local" not in existing_email:
                local_part = existing_email.split('@')[0].lower()
                name_concat = "".join(parts)
                local_concat = re.sub(r'[^a-z0-9]', '', local_part)
                if name_concat == local_concat:
                    corroborated = True
                else:
                    segments = re.split(r'[._-]', local_part)
                    single_letters = [p for p in parts if len(p) == 1]
                    if all(sl in segments for sl in single_letters):
                        corroborated = True
            if not corroborated:
                return False'''
content = content.replace(old2_logic, new2_logic)

old2_caller = '''        # Re-check human name after extraction
        if not self.is_human_name(f"{fn} {ln}", company.company_name if company else ""):'''
new2_caller = '''        # Re-check human name after extraction
        if not self.is_human_name(f"{fn} {ln}", company.company_name if company else "", r.email):'''
content = content.replace(old2_caller, new2_caller)

# Bug 3
old3 = '''    local = pattern.replace("{first}", f).replace("{last}", l).replace("{f1}", f1).replace("{l1}", l1)
    local = re.sub(r'[^a-z0-9._-]', '', local)
    return f"{local}@{domain}"'''
new3 = '''    local = pattern.replace("{first}", f).replace("{last}", l).replace("{f1}", f1).replace("{l1}", l1)
    local = re.sub(r'[^a-z0-9._-]', '', local)
    
    # Strip double dots and trailing/leading punctuation
    local = re.sub(r'\\.{2,}', '.', local)
    local = local.strip('._-')
    
    return f"{local}@{domain}"'''
content = content.replace(old3, new3)

with open('backend/enrich_recruiter_contacts.py', 'w', encoding='utf-8') as f:
    f.write(content)
