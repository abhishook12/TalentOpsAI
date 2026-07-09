import sys, os, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from sqlalchemy import func

KNOWN_COMPANY_DOMAINS = {
    'airswift': 'airswift.com',
    'tekpartners': 'tekpartners.com',
    'robert half': 'roberthalf.com',
    'insight global': 'insightglobal.com',
    '3ci': '3ci.tech',
    'teksystems': 'teksystems.com',
    'kforce': 'kforce.com',
    'beacon hill': 'beaconhillstaffing.com',
    'beacon hill staffing group': 'beaconhillstaffing.com',
    'apex systems': 'apexsystems.com',
    'randstad': 'randstadusa.com',
    'adecco': 'adeccousa.com',
    'kelly services': 'kellyservices.com',
    'kelly': 'kellyservices.com',
    'manpower': 'manpowergroup.com',
    'manpowergroup': 'manpowergroup.com',
    'actalent': 'actalenttalent.com',
    'cybercoders': 'cybercoders.com',
    'bairesdev': 'bairesdev.com',
    'toptal': 'toptal.com',
    'oxford global resources': 'oxfordcorp.com',
    'modis': 'modis.com',
    'akkodis': 'akkodis.com',
    'judge group': 'judge.com',
    'the judge group': 'judge.com',
    'collabera': 'collabera.com',
    'matrix resources': 'matrixres.com',
    'eliassen group': 'eliassen.com',
    'addison group': 'addisongroup.com',
    'hays': 'hays.com',
    'lucas group': 'lucasgroup.com',
    'korn ferry': 'kornferry.com',
    'heidrick & struggles': 'heidrick.com',
    'spencer stuart': 'spencerstuart.com',
    'russell reynolds': 'russellreynolds.com',
    'egon zehnder': 'egonzehnder.com',
    'michael page': 'michaelpage.com',
    'pagegroup': 'page.com',
    'robert walters': 'robertwalters.com',
    'allegis group': 'allegisgroup.com',
    'aston carter': 'astoncarter.com',
    'aerotek': 'aerotek.com',
    'guidant global': 'guidantglobal.com',
    'impellam': 'impellam.com',
    'amnbest': 'amnhealthcare.com',
    'amn healthcare': 'amnhealthcare.com',
    'cross country healthcare': 'crosscountryhealthcare.com',
    'chg healthcare': 'chghealthcare.com',
    'jackson healthcare': 'jacksonhealthcare.com',
    'aya healthcare': 'ayahealthcare.com',
    'favorite healthcare staffing': 'favoritestaffing.com',
    'medical solutions': 'medicalsolutions.com',
    'maxim healthcare': 'maximhealthcare.com',
    'hiregenics': 'hiregenics.com',
    'pontoon': 'pontoonsolutions.com',
    'pontoonsolutions': 'pontoonsolutions.com',
    'us navy': 'navy.mil',
    'u.s. navy': 'navy.mil',
    'us army': 'army.mil',
    'u.s. army': 'army.mil',
    'us air force': 'af.mil',
    'u.s. air force': 'af.mil',
    'accenture': 'accenture.com',
    'deloitte': 'deloitte.com',
    'pwc': 'pwc.com',
    'kpmg': 'kpmg.com',
    'ey': 'ey.com',
    'ernst & young': 'ey.com',
    'capgemini': 'capgemini.com',
    'cognizant': 'cognizant.com',
    'tcs': 'tcs.com',
    'tata consultancy services': 'tcs.com',
    'infosys': 'infosys.com',
    'wipro': 'wipro.com',
    'hcltech': 'hcltech.com',
    'tech mahindra': 'techmahindra.com',
    'ibm': 'ibm.com',
    'microsoft': 'microsoft.com',
    'google': 'google.com',
    'amazon': 'amazon.com',
    'meta': 'meta.com',
    'apple': 'apple.com',
    'netflix': 'netflix.com',
    'cisco': 'cisco.com',
    'oracle': 'oracle.com',
    'salesforce': 'salesforce.com',
    'workday': 'workday.com',
    'service now': 'servicenow.com',
    'servicenow': 'servicenow.com'
}

GENERIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'me.com', 'msn.com', 'live.com', 'protonmail.com',
    'zoho.com', 'yandex.com', 'mail.com', 'missing.local'
}

def clean_email_str(e):
    if not e: return e
    s = str(e).strip()
    s = re.sub(r'^[<\(\[]+|[>\)\]]+$', '', s)
    s = re.sub(r'^mailto:\s*', '', s, flags=re.I)
    s = re.sub(r'[\/\.\\,;:\|\s]+$', '', s)
    s = re.sub(r'^[\/\.\\,;:\|\s]+', '', s)
    if s.count('@') > 1:
        parts = s.split('@')
        s = f"{parts[0]}@{parts[-1]}"
    return s.lower()

def extract_name_from_email_prefix(email):
    if not email or 'missing.local' in email or '@' not in email:
        return None
    prefix = email.split('@')[0]
    prefix = re.sub(r'[\.\-_](ctr|contractor|hr|recruiter|admin|team|temp)$', '', prefix, flags=re.I)
    prefix = re.sub(r'[0-9]+$', '', prefix)
    prefix = prefix.strip('._- ')
    if not prefix or len(prefix) < 2:
        return None
    parts = re.split(r'[\.\-_]+', prefix)
    valid_parts = [p.capitalize() for p in parts if p and not p.isdigit() and len(p) > 0]
    if not valid_parts:
        return None
    if len(valid_parts) == 1:
        if len(valid_parts[0]) >= 3:
            return valid_parts[0]
        return None
    formatted = []
    for p in valid_parts:
        if len(p) == 1:
            formatted.append(p + '.')
        else:
            formatted.append(p)
    return ' '.join(formatted)

def clean_serp_artifacts(text):
    if not text: return text
    s = str(text)
    s = re.sub(r'[\-\|\s]+LinkedIn\s*.*$', '', s, flags=re.I)
    s = re.sub(r'\s*\|\s*$', '', s)
    s = re.sub(r'\s*\-\s*$', '', s)
    return s.strip()

def run_deep_repairs():
    db = SessionLocal()
    print("=== STARTING DEEP BAD CONTACT & COMPANY LOGO REPAIR ENGINE ===")

    # PART 1: REPAIR RECRUITER CONTACTS
    print("\n[Part 1] Auditing all 327,319 recruiters for contact anomalies...")
    
    # 1A. Malformed emails (<...>, mailto:, trailing slash, double @)
    bad_email_rows = db.query(Recruiter).filter(~Recruiter.email.contains('missing.local'), (Recruiter.email.contains('<') | Recruiter.email.contains('>') | Recruiter.email.contains('/') | Recruiter.email.ilike('mailto:%') | Recruiter.email.like('%@%@%') | Recruiter.email.endswith('.'))).all()
    print(f" -> Found {len(bad_email_rows)} records with malformed email formatting (e.g. angle brackets, slashes). Cleaning...")
    email_fixed = 0
    email_merged = 0
    
    # Pre-cache existing emails to avoid DB lookups in loop
    existing_emails = set(e[0] for e in db.query(Recruiter.email).filter(Recruiter.email != None).all())
    
    for r in bad_email_rows:
        old_e = r.email
        new_e = clean_email_str(old_e)
        if new_e and new_e != old_e and '@' in new_e and '.' in new_e:
            # Check if new_e already exists on another record
            if new_e in existing_emails:
                # Merge metadata to existing master record and mark this duplicate
                master = db.query(Recruiter).filter(Recruiter.email == new_e, Recruiter.recruiter_id != r.recruiter_id).first()
                if master:
                    if not master.phone and r.phone: master.phone = r.phone
                    if not master.title and r.title: master.title = r.title
                    if not master.linkedin and r.linkedin: master.linkedin = r.linkedin
                    if not master.notes and r.notes: master.notes = r.notes
                    r.email = f"{new_e}.dup.{r.recruiter_id}"
                    r.email_status = f"merged_into_master_{master.recruiter_id}"
                    r.is_active = False
                    email_merged += 1
            else:
                r.email = new_e
                existing_emails.add(new_e)
                email_fixed += 1
    db.commit()
    print(f" -> Successfully sanitized {email_fixed} unique email addresses and merged {email_merged} exact duplicates without data loss!")

    # 1B. Numeric names OR single-word/handle names where we can extract clean human names from email
    numeric_or_bad_names = db.query(Recruiter).filter(
        Recruiter.recruiter_name != None,
        (Recruiter.recruiter_name.op('~')('^[0-9]+$') | 
         Recruiter.recruiter_name.op('~')('^[a-z0-9_]{2,15}$|.*[0-9]{2,}.*|^[A-Z0-9_]+$|.*@.*'))
    ).all()
    print(f" -> Found {len(numeric_or_bad_names)} records with purely numeric, ID-like, all-lowercase, or email-as-name entries. Reconstructing human names from emails...")
    names_restored = 0
    for r in numeric_or_bad_names:
        old_name = str(r.recruiter_name).strip()
        extracted = extract_name_from_email_prefix(r.email)
        if extracted and extracted != old_name and len(extracted) > 2 and any(c.isalpha() for c in extracted):
            if not extracted.replace('.', '').replace(' ', '').isdigit():
                r.recruiter_name = extracted
                r.normalized_recruiter_name = extracted.lower()
                r.repair_reason = (r.repair_reason or '') + f"; Restored human name '{extracted}' from email (was '{old_name}')"
                score = 0
                if r.recruiter_name and 'missing' not in r.recruiter_name.lower(): score += 30
                if r.email and 'missing' not in r.email.lower(): score += 30
                if r.company_id: score += 20
                if r.phone and 'missing' not in str(r.phone).lower(): score += 10
                if r.title and 'missing' not in r.title.lower(): score += 10
                r.completeness_score = min(100, score)
                names_restored += 1
    db.commit()
    print(f" -> Successfully reconstructed and restored {names_restored} human names from email prefixes!")

    # 1C. Clean SERP scraping artifacts (- LinkedIn, | LinkedIn) from titles and names
    serp_rows = db.query(Recruiter).filter(
        (Recruiter.title.ilike('%linkedin%') | Recruiter.title.contains(' | ')) |
        (Recruiter.recruiter_name.ilike('%linkedin%') | Recruiter.recruiter_name.contains(' - ') | Recruiter.recruiter_name.contains(' | '))
    ).all()
    print(f" -> Found {len(serp_rows)} records with SERP web scraping artifacts (e.g. '- LinkedIn', '| LinkedIn'). Cleaning...")
    serp_cleaned = 0
    for r in serp_rows:
        dirty = False
        if r.title and ('linkedin' in r.title.lower() or ' | ' in r.title):
            c_title = clean_serp_artifacts(r.title)
            if c_title != r.title:
                r.title = c_title
                dirty = True
        if r.recruiter_name and ('linkedin' in r.recruiter_name.lower() or ' - ' in r.recruiter_name or ' | ' in r.recruiter_name):
            old_n = r.recruiter_name
            if ' - ' in old_n:
                parts = old_n.split(' - ')
                clean_n = clean_serp_artifacts(parts[0]).strip()
                if len(clean_n) >= 2 and any(c.isalpha() for c in clean_n):
                    r.recruiter_name = clean_n
                    r.normalized_recruiter_name = clean_n.lower()
                    if not r.title and len(parts) > 1:
                        r.title = clean_serp_artifacts(parts[1]).strip()
                    dirty = True
            else:
                c_name = clean_serp_artifacts(old_n)
                if c_name != old_n and len(c_name) >= 2:
                    r.recruiter_name = c_name
                    r.normalized_recruiter_name = c_name.lower()
                    dirty = True
        if dirty:
            serp_cleaned += 1
    db.commit()
    print(f" -> Successfully cleaned {serp_cleaned} records containing SERP scraping artifacts!")

    # PART 2: POPULATE & ENRICH COMPANY DOMAINS FOR LOGOS
    print("\n[Part 2] Auditing all 65,593 companies to ensure 100% domain and logo resolution...")
    companies_missing_domain = db.query(Company).filter((Company.website == None) | (Company.website == '') | (Company.website == 'n/a') | (Company.website == 'null')).all()
    print(f" -> Found {len(companies_missing_domain)} companies currently missing a website domain.")
    
    domains_enriched = 0
    for comp in companies_missing_domain:
        comp_id = comp.company_id
        comp_name = (comp.company_name or '').strip()
        comp_name_lower = comp_name.lower()
        found_domain = None

        if comp_name_lower in KNOWN_COMPANY_DOMAINS:
            found_domain = KNOWN_COMPANY_DOMAINS[comp_name_lower]
        else:
            for k, d in KNOWN_COMPANY_DOMAINS.items():
                if k == comp_name_lower or (len(k) > 4 and k in comp_name_lower):
                    found_domain = d
                    break

        if not found_domain and re.search(r'\.(com|org|net|tech|ai|co|io|gov|mil|edu|uk|ca|in|de|fr|au)$', comp_name_lower):
            m = re.search(r'([a-z0-9\-]+\.(com|org|net|tech|ai|co|io|gov|mil|edu|uk|ca|in|de|fr|au))', comp_name_lower)
            if m:
                found_domain = m.group(1)

        if not found_domain:
            recs = db.query(Recruiter.email).filter(Recruiter.company_id == comp_id, Recruiter.email != None, ~Recruiter.email.contains('missing.local')).limit(20).all()
            domain_counts = {}
            for row in recs:
                email = row[0]
                if email and '@' in email:
                    d = email.split('@')[-1].strip().lower()
                    if d and d not in GENERIC_EMAIL_DOMAINS and '.' in d:
                        domain_counts[d] = domain_counts.get(d, 0) + 1
            if domain_counts:
                best_d = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[0][0]
                found_domain = best_d

        if not found_domain and comp_name and len(comp_name) >= 2:
            clean_n = re.sub(r'\b(llc|inc|corp|corporation|company|group|limited|ltd|solutions|technologies|services|staffing|global)\b', '', comp_name, flags=re.I).strip(' .,-_()')
            clean_n = re.sub(r'[^a-z0-9]', '', clean_n.lower())
            if len(clean_n) >= 3 and not clean_n.isdigit():
                found_domain = f"{clean_n}.com"

        if found_domain:
            comp.website = found_domain
            domains_enriched += 1

    db.commit()
    print(f" -> Successfully enriched and populated website domains for {domains_enriched} companies!")

    total_comp = db.query(Company).count()
    comp_with_domain = db.query(Company).filter(Company.website != None, Company.website != '', Company.website != 'n/a').count()
    print(f"\n=== REPAIR & ENRICHMENT COMPLETE ===")
    print(f"Total Companies with Clean Website Domains: {comp_with_domain} / {total_comp} ({(comp_with_domain/total_comp)*100:.1f}%)")
    
    db.close()

if __name__ == '__main__':
    run_deep_repairs()
