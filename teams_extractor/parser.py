import re

def parse_contact_fields(text):
    """
    Parses a single message bubble's text to extract contact fields.
    Returns a dictionary of fields.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'(\+?\d{1,3}[-.\s]??\(\d{1,4}\)[-.\s]??\d{1,4}[-.\s]??\d{1,9}|\+?\d{1,4}[-.\s]??\d{1,4}[-.\s]??\d{1,9})'
    
    all_emails = re.findall(email_pattern, text)
    all_phones = []
    
    # Clean phones
    raw_phones = re.findall(phone_pattern, text)
    for p in raw_phones:
        digits = re.sub(r'\D', '', p)
        if len(digits) >= 10:
            all_phones.append(p)
            
    primary_email = all_emails[0] if all_emails else ""
    primary_phone = all_phones[0] if all_phones else ""
    
    # Try to find name (usually first or second line before email/phone)
    name = ""
    title = ""
    linkedin = ""
    
    for i, line in enumerate(lines):
        if primary_email in line or primary_phone in line:
            if i >= 1 and not name:
                name = lines[i-1]
            if i >= 2 and not title:
                title = lines[i-2]
        if "linkedin.com/in/" in line.lower():
            linkedin = line

    return {
        "primary_name": name,
        "primary_email": primary_email,
        "all_emails": "; ".join(all_emails),
        "primary_phone": primary_phone,
        "all_phones": "; ".join(all_phones),
        "company": "",
        "title": title,
        "location": "",
        "linkedin": linkedin,
        "notes": text.replace('\n', ' | ')
    }
