import smtplib
import dns.resolver
import re
import time
import random
import logging
import os
from tavily import TavilyClient

logger = logging.getLogger(__name__)

def verify_email_smtp(email: str) -> bool:
    """
    Connects to the MX server of the email domain and pings the email
    to see if it exists (returns 250 OK) without sending an email.
    """
    try:
        domain = email.split('@')[1]
        
        # 1. Get MX record
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        
        # 2. Connect to SMTP port 25
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(server.local_hostname)
        server.mail('hello@talentopsai.com') # dummy sender
        code, message = server.rcpt(str(email))
        server.quit()
        
        # 3. Check response
        if code == 250:
            return True
        return False
    except Exception as e:
        logger.error(f"SMTP Verification Error for {email}: {e}")
        return False

def tavily_deep_search(name: str, company: str, domain: str = ""):
    """
    Uses Tavily Search API to find phone numbers, emails, and location.
    """
    try:
        from ..config import TAVILY_API_KEYS
        from ..utils.state_mapper import extract_state_detailed
        
        if not TAVILY_API_KEYS:
            logger.error("TAVILY_API_KEYS is not configured.")
            return None, None, None
            
        query = f'"{name}" "{company}" recruiter email phone location'
        
        response = None
        for key in TAVILY_API_KEYS:
            try:
                client = TavilyClient(key)
                response = client.search(query=query, search_depth="advanced")
                break # Success!
            except Exception as e:
                if "exceeds your plan" in str(e).lower() or "limit" in str(e).lower():
                    continue # Try next key
                else:
                    logger.error(f"Tavily Search Error for {name} at {company}: {e}")
                    return None, None, None
                    
        if not response:
            logger.error(f"ALL Tavily keys exhausted during enrichment for {name}.")
            return None, None, None
        
        text_corpus = ""
        for result in response.get("results", []):
            text_corpus += " " + result.get("content", "")
            
        # Regex to find phone numbers like (xxx) xxx-xxxx or xxx-xxx-xxxx
        phone_regex = r'\(?\b[2-9][0-9]{2}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        matches = re.findall(phone_regex, text_corpus)
        phone = matches[0] if matches else None
        
        # Regex to find emails
        email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        email_matches = re.findall(email_regex, text_corpus)
        email = None
        for e in email_matches:
            if verify_email_smtp(e):
                email = e
                break
                
        state_abbr, _ = extract_state_detailed(text_corpus, strict=False)
        return phone, email, state_abbr
    except Exception as e:
        logger.error(f"Tavily Search Error for {name} at {company}: {e}")
        return None, None, None

def is_human_name(name: str, company_name: str = "", existing_email: str = "") -> bool:
    if not name:
        return False
    lower_name = name.lower().strip()

    if any(char.isdigit() for char in lower_name):
        return False

    if lower_name in ('unknown', 'no answer', 'n/a', 'na'):
        return False
        
    parts = lower_name.replace('.', ' ').split()
    
    strict_roles = {'admin', 'info', 'support', 'sales', 'billing', 'contact', 'hr'}
    if any(p in strict_roles for p in parts):
        return False
        
    company_words = {'global', 'tech', 'group', 'partners', 'systems', 'solutions', 'talent', 'acquisition', 'staffing', 'resourcing', 'developers', 'interactive', 'vm'}
    if all(p in company_words for p in parts):
        return False

    buzzwords_in_name = [p for p in parts if p in company_words]
    non_buzzwords = [p for p in parts if p not in company_words]
    if buzzwords_in_name and all(len(p) <= 3 for p in non_buzzwords):
        return False

    if any(len(p) == 1 for p in parts):
        is_valid_initial = (
            len(parts) >= 2
            and len(parts[0]) > 1
            and sum(1 for p in parts if len(p) == 1) == 1
        )
        if not is_valid_initial:
            corroborated = False
            if existing_email and "@" in existing_email and not any(p in existing_email for p in ["@missing.local", "@invalid.local", "@example.com"]):
                local_part = existing_email.split('@')[0].lower()
                name_concat = "".join(parts)
                local_concat = re.sub(r'[^a-z0-9]', '', local_part)
                if name_concat == local_concat:
                    corroborated = True
                else:
                    segments = re.split(r'[._-]', local_part)
                    single_letters = [p for p in parts if len(p) == 1]
                    if all(sl in segments for sl in single_letters):
                        corroborated = True
            if not corroborated:
                return False

    if company_name:
        name_clean = re.sub(r'[^a-z0-9]', '', lower_name)
        comp_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
        if name_clean and name_clean == comp_clean:
            return False
            
    return True

def auto_enhance_recruiter_data(recruiter_name: str, company_name: str, company_domain: str):
    """
    Attempts to find verified email and phone number.
    Returns dict: {'email': '...', 'phone': '...'}
    """
    result = {'email': None, 'phone': None}
    
    if not is_human_name(recruiter_name, company_name):
        logger.warning(f"Skipping enhancement for non-human name: {recruiter_name}")
        return result
    
    # 1. Scrape phone number, email, and location using Tavily
    if company_name:
        phone, email, loc = tavily_deep_search(recruiter_name, company_name, company_domain)
        if phone:
            result['phone'] = phone
        if email:
            result['email'] = email
        if loc:
            result['location'] = loc
            
    # 2. Try to guess and verify email if Tavily didn't find one and we have domain
    if not result.get('email') and company_domain:
        first = recruiter_name.split(' ')[0].lower()
        last = recruiter_name.split(' ')[-1].lower()
        
        # Common permutations
        permutations = [
            f"{first}.{last}@{company_domain}",
            f"{first[0]}{last}@{company_domain}",
            f"{first}@{company_domain}",
            f"{last}@{company_domain}"
        ]
        
        for email in permutations:
            if verify_email_smtp(email):
                result['email'] = email
                break # Stop searching if we found a verified one!
                
    return result
