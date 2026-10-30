import ctypes
import sys
import re
import json
from pywinauto import Application

sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32
hdesk = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if hdesk:
    user32.SetThreadDesktop(hdesk)

app = Application(backend='uia').connect(handle=263026)
win = app.window(handle=263026)

EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PHONE_REGEX = r'(\+?\d{1,3}[-.\s]??\(?\d{2,4}\)?[-.\s]??\d{2,4}[-.\s]??\d{3,9})'

msg_bodies = [d for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]
print(f'Total messages found: {len(msg_bodies)}')

results = []
for m in msg_bodies:
    mid = m.element_info.automation_id
    header = m.element_info.name or ''
    
    contents = [c for c in m.children() if (c.element_info.automation_id or '').startswith('content-')]
    tokens = []
    if contents:
        tokens = [child.element_info.name.strip() for child in contents[0].children() if child.element_info.name and child.element_info.name.strip()]
    
    # Extract sender
    sender = ''
    sender_match = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:Link\s+|Sent\s+)?', header)
    if sender_match:
        sender = sender_match.group(1).strip()
        
    # Extract all emails & phones
    all_emails = list(dict.fromkeys(re.findall(EMAIL_REGEX, header)))
    raw_phones = re.findall(PHONE_REGEX, header)
    all_phones = []
    for p in raw_phones:
        clean = re.sub(r'[^\d+]', '', p)
        if len(re.sub(r'\D', '', clean)) >= 10:
            if clean not in all_phones:
                all_phones.append(clean)
                
    # Parse candidate name, title, company from tokens
    name = ''
    title = ''
    company = ''
    corp_email = ''
    personal_email = ''
    corp_phone = ''
    mobile_phone = ''
    linkedin = ''
    location = ''
    
    # Check linkedin
    for t in tokens:
        if 'linkedin.com' in t.lower():
            linkedin = t
            
    mode = None
    for t in tokens:
        if t in ['Corporate email', 'Personal email', 'Corporate phone', 'Mobile phone', 'Unknown phone']:
            mode = t
            continue
        if mode == 'Corporate email':
            if '@' in t and not corp_email:
                corp_email = t
        elif mode == 'Personal email':
            if '@' in t and not personal_email:
                personal_email = t
        elif mode == 'Corporate phone':
            if any(c.isdigit() for c in t) and not corp_phone:
                corp_phone = t
        elif mode == 'Mobile phone':
            if any(c.isdigit() for c in t) and not mobile_phone:
                mobile_phone = t
                
    # Candidate name extraction
    for t in tokens:
        if t.startswith('Link ') and '@' not in t and 'Contact' not in t and 'linkedin' not in t.lower():
            cand_cand = t.replace('Link ', '').strip()
            # Clean '· 3rd' or titles if attached
            if '·' in cand_cand:
                cand_cand = cand_cand.split('·')[0].strip()
            if len(cand_cand.split()) <= 4:
                name = cand_cand
                break
            
    if not name and tokens:
        # Fallback to first non-action token
        candidate_t = tokens[0]
        if not candidate_t.startswith('Link ') and '@' not in candidate_t and not any(k in candidate_t.lower() for k in ['sent', 'corporate', 'personal']):
            if len(candidate_t.split()) <= 4:
                name = candidate_t
                
    # Company extraction heuristics
    for t in tokens:
        if t in [name, f'Link {name}', corp_email, personal_email, corp_phone, mobile_phone]:
            continue
        if any(corp_suffix in t.lower() for corp_suffix in [' inc', ' llc', ' ltd', ' corp', ' consulting', ' staffing', ' solutions', ' group', ' technologies', ' technology', ' systems', ' partners', ' resources', ' health']):
            company = t
            break
            
    # Location heuristics
    for t in tokens:
        if any(loc_suffix in t.lower() for loc_suffix in [' metropolitan area', ' united states', ', us', ' canada', ' area']):
            location = t
            break

    primary_email = corp_email or (all_emails[0] if all_emails else None)
    primary_phone = mobile_phone or corp_phone or (all_phones[0] if all_phones else None)
    
    if name or primary_email or primary_phone:
        results.append({
            'message_id': mid,
            'sender': sender,
            'name': name,
            'company': company,
            'title': title,
            'location': location,
            'primary_email': primary_email,
            'primary_phone': primary_phone,
            'all_emails': all_emails,
            'all_phones': all_phones,
            'tokens_sample': tokens[:4]
        })

print(f'Parsed {len(results)} valid candidate contact cards:')
for r in results[:10]:
    print(f"ID: {r['message_id']} | Sender: {r['sender']} | Candidate: {r['name']} | Company: {r['company']} | Email: {r['primary_email']} | Phone: {r['primary_phone']}")
