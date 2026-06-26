import re

with open('backend/enrich_recruiter_contacts.py', 'r', encoding='utf-8') as f:
    content = f.read()

def repl(match):
    return 'if r.email and ("@missing.local" in r.email or "@invalid.local" in r.email or "@example.com" in r.email or r.email_status == "invalid"):'

content = re.sub(r'if "@missing.local" in r\.email or r\.email_status == "invalid":', repl, content)

# Let's fix line 407 to use a different status!
# Wait, the user did not say to fix line 407. The user said:
# "Patch the remaining missing.local leak... Search the entire file for every place r.email is checked... For each location found, apply the same is_placeholder exclusion... Log each location and diff in SESSION_LOG.md."

with open('backend/enrich_recruiter_contacts.py', 'w', encoding='utf-8') as f:
    f.write(content)
