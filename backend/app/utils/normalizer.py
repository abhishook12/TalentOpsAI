import re
from urllib.parse import urlparse

def normalize_text(text: str) -> str:
    """
    Aggressively strips spaces, punctuation, and non-alphanumeric characters,
    and lowercases the string for highly tolerant fuzzy matching.
    e.g. 'INSIGHT GLOBAL!' -> 'insightglobal'
    """
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def extract_domain(url: str) -> str:
    """
    Extracts the root domain from a URL or email address.
    e.g. 'https://www.insightglobal.com/careers' -> 'insightglobal.com'
    e.g. 'john@sub.insightglobal.com' -> 'insightglobal.com'
    """
    if not url:
        return ""
    
    url = str(url).strip().lower()
    
    # Handle emails
    if '@' in url:
        url = url.split('@')[-1]
        
    # Handle URLs
    if not url.startswith('http'):
        url = 'http://' + url
        
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Strip www.
        if domain.startswith('www.'):
            domain = domain[4:]
        # Extract root domain (simple heuristic for now)
        parts = domain.split('.')
        if len(parts) > 2 and parts[-1] in ('com', 'org', 'net', 'io', 'co', 'us', 'uk'):
            domain = '.'.join(parts[-2:])
        return domain
    except:
        return ""
