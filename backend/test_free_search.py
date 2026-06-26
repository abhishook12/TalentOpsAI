#!/usr/bin/env python
import urllib.request
import urllib.parse
import re

def free_fallback_search(name: str, company: str):
    try:
        query = urllib.parse.quote(f'"{name}" "{company}" recruiter email phone')
        url = f"https://html.duckduckgo.com/html/?q={query}"
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            clean_text = re.sub(r'<[^>]+>', ' ', html)
            phone_regex = r'\(?\b[2-9][0-9]{2}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
            phones = re.findall(phone_regex, clean_text)
            phone = phones[0] if phones else None
            
            email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
            emails = [e for e in re.findall(email_regex, clean_text) if not any(x in e.lower() for x in ['duckduckgo', 'w3.org', 'schema.org', 'example.com', 'missing.local', 'png', 'jpg', 'css', 'js'])]
            email = emails[0] if emails else None
            return phone, email
    except Exception as e:
        print(f"Failed: {e}")
        return None, None

print("Testing Free DuckDuckGo Fallback Search...")
p, e = free_fallback_search("Abhishek Pathak", "Consulting Solutions")
print(f"Result -> Phone: {p} | Email: {e}")
