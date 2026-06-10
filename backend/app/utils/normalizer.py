import re
from urllib.parse import urlparse

MULTI_PART_SUFFIXES = {
    ("co", "uk"),
    ("org", "uk"),
    ("ac", "uk"),
    ("gov", "uk"),
    ("ltd", "uk"),
    ("com", "au"),
    ("net", "au"),
    ("org", "au"),
    ("edu", "au"),
    ("co", "in"),
    ("firm", "in"),
    ("net", "in"),
    ("org", "in"),
    ("com", "br"),
    ("com", "mx"),
    ("com", "sg"),
    ("com", "my"),
    ("com", "ph"),
    ("co", "nz"),
    ("co", "za"),
    ("com", "tr"),
}

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
        # Extract root domain with a slightly smarter public-suffix heuristic.
        parts = domain.split('.')
        if len(parts) > 2:
            suffix = tuple(parts[-2:])
            if suffix in MULTI_PART_SUFFIXES:
                domain = '.'.join(parts[-3:])
            elif parts[-1] in ('com', 'org', 'net', 'io', 'co', 'us', 'ca', 'ai', 'biz', 'info', 'me'):
                domain = '.'.join(parts[-2:])
        return domain
    except:
        return ""
