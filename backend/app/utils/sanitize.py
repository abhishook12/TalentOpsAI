import re

def sanitize_html(text: str | None) -> str | None:
    if not text:
        return text
    # Basic HTML tag stripping
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
