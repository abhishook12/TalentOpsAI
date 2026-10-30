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

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'(\+?\d{1,3}[-.\s]??\(?\d{2,4}\)?[-.\s]??\d{2,4}[-.\s]??\d{3,9})')

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com', 'gateway.net'
}

def clean_phone(raw):
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) >= 10:
        if raw.startswith('+'):
            return f"+{digits}"
        return f"+{digits}"
    return None

def infer_company_from_domain(domain):
    if not domain or domain in FREE_EMAIL_DOMAINS:
        return ""
    root = domain.split('.')[0]
    # Clean common suffixes like tech, inc, etc.
    words = re.split(r'[-_]', root)
    return " ".join(w.capitalize() for w in words)

def parse_teams_message(mid, header, tokens):
    # Sender extraction
    sender = ""
    sender_m = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:Link\s+|Sent\s+|Corporate\s+)?', header)
    if sender_m:
        cand_sender = sender_m.group(1).strip()
        if cand_sender.lower() not in ['link', 'sent', 'corporate', 'personal']:
            sender = cand_sender

    # Emails & Phones from header text
    raw_emails = list(dict.fromkeys(EMAIL_REGEX.findall(header)))
    raw_phones = PHONE_REGEX.findall(header)
    cleaned_phones = []
    for rp in raw_phones:
        cp = clean_phone(rp)
        if cp and cp not in cleaned_phones:
            cleaned_phones.append(cp)

    # Classify Corporate vs Personal from labeled tokens
    corp_emails = []
    personal_emails = []
    corp_phones = []
    mobile_phones = []
    other_phones = []

    current_label = None
    for t in tokens:
        if t in ['Corporate email', 'Personal email', 'Corporate phone', 'Mobile phone', 'Unknown phone']:
            current_label = t
            continue
        if current_label == 'Corporate email':
            if '@' in t and t not in corp_emails:
                corp_emails.append(t)
        elif current_label == 'Personal email':
            if '@' in t and t not in personal_emails:
                personal_emails.append(t)
        elif current_label == 'Corporate phone':
            cp = clean_phone(t)
            if cp and cp not in corp_phones:
                corp_phones.append(cp)
        elif current_label == 'Mobile phone':
            cp = clean_phone(t)
            if cp and cp not in mobile_phones:
                mobile_phones.append(cp)
        elif current_label == 'Unknown phone':
            cp = clean_phone(t)
            if cp and cp not in other_phones:
                other_phones.append(cp)

    # Candidate Name Resolution
    candidate_name = ""
    # Heuristic 1: Look for 'Link <Name>'
    for t in tokens:
        if t.startswith('Link ') and '@' not in t and 'contact' not in t.lower() and 'linkedin' not in t.lower():
            cand = t.replace('Link ', '').strip()
            # Clean '· 3rd' or suffix
            cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her|They/Them)\b', cand)[0].strip()
            if '·' in cand:
                cand = cand.split('·')[0].strip()
            if 1 < len(cand.split()) <= 4 and not any(k in cand.lower() for k in ['sent', 'corporate', 'email', 'phone']):
                candidate_name = cand
                break

    # Heuristic 2: First non-label token if no 'Link <Name>'
    if not candidate_name:
        for t in tokens:
            if t in ['Corporate email', 'Personal email', 'Corporate phone', 'Mobile phone', 'Unknown phone', '·']:
                continue
            if '@' in t or any(c.isdigit() for c in t):
                continue
            if t.lower().startswith(('http', 'link', 'sent', 'unread')):
                continue
            cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her)\b', t)[0].strip()
            if 1 < len(cand.split()) <= 4:
                candidate_name = cand
                break

    # Title & Location extraction
    title = ""
    location = ""
    for t in tokens:
        # Title heuristics
        if any(role_w in t.lower() for role_w in ['developer', 'engineer', 'manager', 'director', 'partner', 'lead', 'analyst', 'consultant', 'founder', 'ceo', 'coo', 'officer', 'specialist', 'recruiter', 'architect']):
            if not title and len(t) < 150:
                title = t.strip()
        # Location heuristics
        if any(loc_w in t.lower() for loc_w in [' metropolitan area', ' united states', ', us', ' canada', ' area']):
            if not location:
                location = t.strip()

    # Company extraction
    company = ""
    for t in tokens:
        if t in [candidate_name, f"Link {candidate_name}", title, location]:
            continue
        if any(sfx in t.lower() for sfx in [' inc', ' llc', ' ltd', ' corp', ' consulting', ' staffing', ' solutions', ' group', ' technologies', ' technology', ' systems', ' partners', ' resources', ' health', ' hospital', ' services', ' firm']):
            if not company and len(t) < 80 and not '@' in t:
                company = t.strip()
                break

    # Email selection
    primary_email = ""
    if corp_emails:
        primary_email = corp_emails[0]
    else:
        # Check raw emails for corporate domain
        for em in raw_emails:
            domain = em.split('@')[-1].lower()
            if domain not in FREE_EMAIL_DOMAINS:
                primary_email = em
                break
        if not primary_email:
            if personal_emails:
                primary_email = personal_emails[0]
            elif raw_emails:
                primary_email = raw_emails[0]

    # Infer company from primary email if still missing
    if not company and primary_email:
        domain = primary_email.split('@')[-1].lower()
        company = infer_company_from_domain(domain)

    # Phone selection
    primary_phone = ""
    if mobile_phones:
        primary_phone = mobile_phones[0]
    elif corp_phones:
        primary_phone = corp_phones[0]
    elif other_phones:
        primary_phone = other_phones[0]
    elif cleaned_phones:
        primary_phone = cleaned_phones[0]

    # Combine all emails and all phones
    all_emails = list(dict.fromkeys(corp_emails + personal_emails + raw_emails))
    all_phones = list(dict.fromkeys(mobile_phones + corp_phones + other_phones + cleaned_phones))

    return {
        'message_id': mid,
        'sender': sender,
        'name': candidate_name,
        'title': title,
        'company': company,
        'location': location,
        'primary_email': primary_email,
        'primary_phone': primary_phone,
        'all_emails': all_emails,
        'all_phones': all_phones,
        'raw_tokens': tokens
    }

app = Application(backend='uia').connect(handle=263026)
win = app.window(handle=263026)
msg_bodies = [d for d in win.descendants() if (d.element_info.automation_id or '').startswith('message-body-')]

print(f"Total messages scanned: {len(msg_bodies)}")
parsed_records = []
for m in msg_bodies:
    mid = m.element_info.automation_id
    header = m.element_info.name or ''
    contents = [c for c in m.children() if (c.element_info.automation_id or '').startswith('content-')]
    tokens = []
    if contents:
        tokens = [child.element_info.name.strip() for child in contents[0].children() if child.element_info.name and child.element_info.name.strip()]
    parsed = parse_teams_message(mid, header, tokens)
    if parsed['name'] or parsed['primary_email'] or parsed['primary_phone']:
        parsed_records.append(parsed)

print(f"Successfully structured {len(parsed_records)} candidate cards:\n")
for i, r in enumerate(parsed_records[:15]):
    print(f"[{i+1}] {r['name']} | Company: {r['company']} | Title: {r['title'][:40]} | Email: {r['primary_email']} | Phone: {r['primary_phone']} | Sender: {r['sender']}")
