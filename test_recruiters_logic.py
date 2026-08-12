import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import SessionLocal
from app.routes.analytics import DOMAIN_DISPLAY_NAMES
from app.utils.logo_domains import select_logo_domain

# dummy results
results = [
    {
        "recruiter_id": 1,
        "email": "sbhagat@prolinksolutions.com",
        "company_id": 129651
    }
]

companies_dict = {}
free_domains = {'gmail.com', 'yahoo.com', 'hotmail.com'}

formatted_results = []
for r in results:
    comp = companies_dict.get(r.get('company_id'))
    
    pg_logo = select_logo_domain(comp.website, comp.email_pattern) if comp else None
    rec_domain = None
    email_val = r.get('email')
    if email_val and '@' in email_val:
        d = email_val.split('@')[-1].lower()
        if d not in free_domains:
            rec_domain = d
    company_domain = rec_domain or pg_logo

    raw_key = str(r.get('company_id')) if r.get('company_id') is not None else None
    if company_domain and company_domain in DOMAIN_DISPLAY_NAMES:
        c_name = DOMAIN_DISPLAY_NAMES[company_domain]
    elif comp and comp.company_name:
        c_name = comp.company_name
    elif company_domain:
        c_name = company_domain.split('.')[0].replace('-', ' ').title()
    else:
        c_name = "Unknown Company" if raw_key and raw_key.isdigit() else raw_key

    print(c_name)
    print(company_domain)
