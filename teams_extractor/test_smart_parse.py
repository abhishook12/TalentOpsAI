import re
import json

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com'
}

KNOWN_DOMAIN_COMPANIES = {
    'dppit.com': 'DP Professionals (DPP)',
    'ssipeople.com': 'SSI People',
    'source-technology.com': 'Source Technology',
    'sourcegroupinternational.com': 'Source Group International',
    'bluemarbleanalytics.com': 'Blue Marble Analytics',
    'delphi-us.com': 'Delphi-US',
    'teksystems.com': 'TEKsystems',
    'randstadusa.com': 'Randstad USA',
    'fairview.org': 'Fairview Health Services',
    'systemone.com': 'System One',
    'copiastaffing.com': 'Copia Staffing Partners'
}

def clean_phone(p):
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) >= 10:
        return f"+{digits}" if not str(p).startswith('+') else f"+{digits}"
    return str(p).strip()

def infer_name_from_email(email):
    if not email: return ""
    local = email.split('@')[0].lower()
    # Remove numbers
    local = re.sub(r'\d+', '', local)
    parts = re.split(r'[._-]', local)
    if len(parts) >= 2 and all(len(p) >= 2 for p in parts[:2]):
        return f"{parts[0].capitalize()} {parts[1].capitalize()}"
    return ""

def infer_company_from_domain(domain):
    if not domain or domain.lower() in FREE_EMAIL_DOMAINS:
        return ""
    d_clean = domain.lower()
    if d_clean in KNOWN_DOMAIN_COMPANIES:
        return KNOWN_DOMAIN_COMPANIES[d_clean]
    root = d_clean.split('.')[0]
    words = re.split(r'[-_]', root)
    return " ".join(w.capitalize() for w in words)

def parse_candidate_message(mid, header, tokens):
    # 1. Emails
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.I)
    raw_emails = list(dict.fromkeys(email_regex.findall(header)))
    
    # Classify corporate vs personal
    corp_emails = []
    personal_emails = []
    for em in raw_emails:
        dom = em.split('@')[-1].lower()
        if dom in FREE_EMAIL_DOMAINS:
            personal_emails.append(em)
        else:
            corp_emails.append(em)

    # 2. Phones
    phone_regex = re.compile(r'(\+?\d{1,3}[-.\s]??\(?\d{2,4}\)?[-.\s]??\d{2,4}[-.\s]??\d{3,9})')
    raw_phones = phone_regex.findall(header)
    cleaned_phones = []
    for rp in raw_phones:
        cp = clean_phone(rp)
        if cp and cp not in cleaned_phones:
            cleaned_phones.append(cp)

    # 3. Candidate Name
    candidate_name = ""
    # Check 'Link <Name>'
    for t in tokens:
        if t.startswith('Link ') and '@' not in t and 'contact' not in t.lower() and 'linkedin' not in t.lower():
            cand = t.replace('Link ', '').strip()
            cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her|They/Them)\b', cand)[0].strip()
            # Clean degree suffixes
            cand = re.sub(r'[,.\s]+(?:MBA|MD|PMP|MS|PhD|CPA|BS|BA)\b', '', cand, flags=re.I).strip()
            if 1 < len(cand.split()) <= 4:
                candidate_name = cand
                break

    # If no 'Link <Name>', check tokens for human name
    if not candidate_name:
        for t in tokens:
            if t in ['Corporate email', 'Personal email', 'Mobile phone', 'Unknown phone', '·', ':']:
                continue
            if '@' in t or any(c.isdigit() for c in t):
                continue
            if t.lower().startswith(('http', 'link', 'sent', 'unread')):
                continue
            # Check if degree is attached
            cand = re.split(r'[\s·]+(?:3rd|2nd|1st|He/Him|She/Her)\b', t)[0].strip()
            cand = re.sub(r'[,.\s]+(?:MBA|MD|PMP|MS|PhD|CPA|BS|BA)\b', '', cand, flags=re.I).strip()
            if 1 < len(cand.split()) <= 4 and not any(k in cand.lower() for k in ['manager', 'director', 'partner', 'consulting', 'solutions', 'technologies', 'group']):
                candidate_name = cand
                break

    # If still no name, guess from primary email
    if not candidate_name and (corp_emails or personal_emails):
        hint_em = corp_emails[0] if corp_emails else personal_emails[0]
        candidate_name = infer_name_from_email(hint_em)

    # 4. Company & Title
    company = ""
    title = ""
    location = ""

    for t in tokens:
        # Check "X at Y" pattern
        m_at = re.search(r'([A-Za-z\s/&]+)\s+at\s+([A-Za-z0-9\s/&().,-]+)', t, re.I)
        if m_at and not title and not company:
            cand_title = m_at.group(1).strip()
            cand_company = m_at.group(2).strip()
            if len(cand_title) < 80:
                title = cand_title
            if len(cand_company) < 80:
                company = cand_company

        # Location
        if any(loc_w in t.lower() for loc_w in [' metropolitan area', ' united states', ', us', ' canada', ' area']) and not location:
            location = t.strip()

    # Company fallback
    if not company:
        for t in tokens:
            if t in [candidate_name, f"Link {candidate_name}", title, location]:
                continue
            if any(sfx in t.lower() for sfx in [' inc', ' llc', ' ltd', ' corp', ' consulting', ' staffing', ' solutions', ' group', ' technologies', ' technology', ' systems', ' partners', ' resources', ' health', ' hospital', ' services', ' firm', 'sgi']):
                if not company and len(t) < 60 and '@' not in t:
                    company = t.strip()
                    break

    # Company infer from domain
    if not company and corp_emails:
        dom = corp_emails[0].split('@')[-1]
        company = infer_company_from_domain(dom)

    # 5. Multi-Email Mapping
    primary_email = corp_emails[0] if corp_emails else (personal_emails[0] if personal_emails else None)
    email2 = personal_emails[0] if (corp_emails and personal_emails) else (corp_emails[1] if len(corp_emails) > 1 else (personal_emails[1] if len(personal_emails) > 1 else None))
    email3 = corp_emails[2] if len(corp_emails) > 2 else (personal_emails[2] if len(personal_emails) > 2 else None)
    email4 = corp_emails[3] if len(corp_emails) > 3 else (personal_emails[3] if len(personal_emails) > 3 else None)

    # 6. Multi-Phone Mapping (Up to 4 separated phone numbers)
    primary_phone = cleaned_phones[0] if len(cleaned_phones) >= 1 else None
    phone2 = cleaned_phones[1] if len(cleaned_phones) >= 2 else None
    phone3 = cleaned_phones[2] if len(cleaned_phones) >= 3 else None
    phone4 = cleaned_phones[3] if len(cleaned_phones) >= 4 else None

    # Sender extraction
    sender_m = re.match(r'^([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:Link\s+|Sent\s+|Corporate\s+)?', header)
    sender = sender_m.group(1).strip() if sender_m else ""

    return {
        "discovery_id": f"TEAMS-CTV-{mid.replace('message-body-', '')}",
        "name": candidate_name,
        "title": title,
        "company": company,
        "location": location,
        "primary_email": primary_email,
        "email2": email2,
        "email3": email3,
        "email4": email4,
        "all_emails": raw_emails,
        "primary_phone": primary_phone,
        "phone2": phone2,
        "phone3": phone3,
        "phone4": phone4,
        "all_phones": cleaned_phones,
        "sender": sender
    }

# Test cases from screenshot
test_cases = [
    (
        "message-body-1793133961303",
        "Lakshay Verma Ramadan Abdul-Azeez, MBA He/Him · 3rd President/Senior Partner at Blue Marble Analytics and President Board of Directors Black Chamber o Fort Wayne, Indiana, United States +12604032406",
        ['Ramadan Abdul-Azeez, MBA', 'He/Him', '· 3rd', 'President/Senior Partner at Blue Marble Analytics and President Board of Directors Black Chamber of Commerce Fort Wayne, Indiana', 'Fort Wayne, Indiana, United States', '+12604032406']
    ),
    (
        "message-body-1793133993652",
        "Gaurav Ojha nikki.rickey@dppit.com nikkirickey10@gmail.com +15203587589 +14044443003 Link Nikki (Nicole) Rickey Dawsonville, Georgia, United States Senior Recruiter at DP Professionals (DPP)",
        ['nikki.rickey@dppit.com', 'nikkirickey10@gmail.com', '+15203587589', '+14044443003', 'Link Nikki (Nicole) Rickey', 'Dawsonville, Georgia, United States', 'Senior Recruiter at', 'DP Professionals (DPP)']
    ),
    (
        "message-body-1793134889545",
        "chitransh tiwari Link Ross Paterson SGI Corporate email ross.paterson@source-technology.com ross.paterson@sourcegroupinternational.com Personal email rp.rosspaterson@gmail.com Mobile phone +44 7815 016451 Unknown phone +44 20 7269 2272",
        ['Link Ross Paterson', 'SGI', 'Corporate email', 'ross.paterson@source-technology.com', 'ross.paterson@sourcegroupinternational.com', 'Personal email', 'rp.rosspaterson@gmail.com', 'Mobile phone', '+44 7815 016451', 'Unknown phone', '+44 20 7269 2272']
    ),
    (
        "message-body-1793134999999",
        "hmaturin@ssipeople.com heathermaturin@gmail.com +19083938640 +12014744295 +19085282523 New York City Metropolitan Area Heather Maturin",
        ['hmaturin@ssipeople.com', 'heathermaturin@gmail.com', '+19083938640', '+12014744295', '+19085282523', 'New York City Metropolitan Area', 'Heather Maturin']
    )
]

for mid, header, tokens in test_cases:
    res = parse_candidate_message(mid, header, tokens)
    print(f"\n=======================================================")
    print(f"Candidate: {res['name']}")
    print(f"Company:   {res['company']}")
    print(f"Title:     {res['title']}")
    print(f"Location:  {res['location']}")
    print(f"Emails:    Primary={res['primary_email']} | Email2={res['email2']} | Email3={res['email3']}")
    print(f"Phones:    Primary={res['primary_phone']} | Phone2={res['phone2']} | Phone3={res['phone3']}")
    print(f"Sender:    {res['sender']}")
