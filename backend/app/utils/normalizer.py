import re

def normalize_text(text: str) -> str:
    """
    Aggressively strips spaces, punctuation, and non-alphanumeric characters,
    and lowercases the string for highly tolerant fuzzy matching.
    e.g. 'INSIGHT GLOBAL!' -> 'insightglobal'
    """
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())
