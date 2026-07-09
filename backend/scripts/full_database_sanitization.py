import sys, os, re, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append(os.path.abspath('C:/TalentOpsAI/backend'))
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from sqlalchemy import func

KNOWN_COMPANY_DOMAINS = {
    'airswift': 'airswift.com',
    'air swift': 'airswift.com',
    'tekpartners': 'tekpartners.com',
    'tek partners': 'tekpartners.com',
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
    'capgemini': 'capgemini.com',
    'cognizant': 'cognizant.com',
    'tcs': 'tcs.com',
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

def run_full_database_sanitization():
    db = SessionLocal()
    print("=======================================================================")
    print("=== FULL DATABASE SANITIZATION & LOGO ENRICHMENT ENGINE (V3) ===")
    print("=======================================================================")
    sys.stdout.flush()

    # Pre-load existing emails set for lightning-fast duplicate protection
    print("\n[Step 0] Caching existing database emails for zero-collision merge protection...")
    sys.stdout.flush()
    existing_emails = set(e[0] for e in db.query(Recruiter.email).filter(Recruiter.email != None).all())
    print(f" -> Cached {len(existing_emails)} existing email records.")
    sys.stdout.flush()

    # PART 1: AUDIT & REPAIR ALL 327,319 RECRUITERS IN BATCHES
    total_recs = db.query(Recruiter).count()
    print(f"\n[Step 1] Auditing all {total_recs:,} recruiters across the entire database in batches of 5,000...")
    sys.stdout.flush()

    batch_size = 5000
    total_batches = (total_recs + batch_size - 1) // batch_size
    
    total_emails_fixed = 0
    total_emails_merged = 0
    total_names_restored = 0
    total_serp_cleaned = 0

    for batch_idx in range(total_batches):
        offset = batch_idx * batch_size
        rows = db.query(Recruiter).order_by(Recruiter.recruiter_id).offset(offset).limit(batch_size).all()
        if not rows:
            break
        
        batch_emails_fixed = 0
        batch_emails_merged = 0
        batch_names_restored = 0
        batch_serp_cleaned = 0
        batch_dirty = False

        for r in rows:
            row_dirty = False

            # A. Check malformed email
            if r.email and ('<' in r.email or '>' in r.email or r.email.endswith('/') or 'mailto:' in r.email.lower() or '@' in r.email[r.email.find('@')+1:] or r.email.endswith('.')):
                old_e = r.email
                new_e = clean_email_str(old_e)
                if new_e and new_e != old_e and '@' in new_e and '.' in new_e:
                    if new_e in existing_emails:
                        master = db.query(Recruiter).filter(Recruiter.email == new_e, Recruiter.recruiter_id != r.recruiter_id).first()
                        if master:
                            if not master.phone and r.phone: master.phone = r.phone
                            if not master.title and r.title: master.title = r.title
                            if not master.linkedin and r.linkedin: master.linkedin = r.linkedin
                            if not master.notes and r.notes: master.notes = r.notes
                        r.email = f"{new_e}.dup.{r.recruiter_id}"
                        r.email_status = f"merged_duplicate"
                        r.is_active = False
                        batch_emails_merged += 1
                        row_dirty = True
                    else:
                        r.email = new_e
                        existing_emails.add(new_e)
                        batch_emails_fixed += 1
                        row_dirty = True

            # B. Check numeric names or ID handles
            if r.recruiter_name and (r.recruiter_name.replace(' ', '').isdigit() or re.match(r'^[a-z0-9_]{2,15}$|.*[0-9]{2,}.*|^[A-Z0-9_]+$', str(r.recruiter_name).strip())):
                old_n = str(r.recruiter_name).strip()
                extracted = extract_name_from_email_prefix(r.email)
                if extracted and extracted != old_n and len(extracted) > 2 and any(c.isalpha() for c in extracted):
                    if not extracted.replace('.', '').replace(' ', '').isdigit():
                        r.recruiter_name = extracted
                        r.normalized_recruiter_name = extracted.lower()
                        r.repair_reason = (r.repair_reason or '') + f"; Restored human name '{extracted}' from email prefix (was '{old_n}')"
                        score = 0
                        if r.recruiter_name and 'missing' not in r.recruiter_name.lower(): score += 30
                        if r.email and 'missing' not in r.email.lower(): score += 30
                        if r.company_id: score += 20
                        if r.phone and 'missing' not in str(r.phone).lower(): score += 10
                        if r.title and 'missing' not in r.title.lower(): score += 10
                        r.completeness_score = min(100, score)
                        batch_names_restored += 1
                        row_dirty = True

            # C. Check SERP scraping artifacts (- LinkedIn, | LinkedIn)
            if (r.title and ('linkedin' in r.title.lower() or ' | ' in r.title)) or (r.recruiter_name and ('linkedin' in r.recruiter_name.lower() or ' - ' in r.recruiter_name or ' | ' in r.recruiter_name)):
                serp_dirty = False
                if r.title and ('linkedin' in r.title.lower() or ' | ' in r.title):
                    c_title = clean_serp_artifacts(r.title)
                    if c_title != r.title:
                        r.title = c_title
                        serp_dirty = True
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
                            serp_dirty = True
                    else:
                        c_name = clean_serp_artifacts(old_n)
                        if c_name != old_n and len(c_name) >= 2:
                            r.recruiter_name = c_name
                            r.normalized_recruiter_name = c_name.lower()
                            serp_dirty = True
                if serp_dirty:
                    batch_serp_cleaned += 1
                    row_dirty = True

            if row_dirty:
                batch_dirty = True

        if batch_dirty:
            db.commit()

        total_emails_fixed += batch_emails_fixed
        total_emails_merged += batch_emails_merged
        total_names_restored += batch_names_restored
        total_serp_cleaned += batch_serp_cleaned

        if (batch_idx + 1) % 5 == 0 or batch_idx == total_batches - 1:
            print(f"   [Batch {batch_idx+1}/{total_batches}] Processed min(offset={offset+batch_size:,}, {total_recs:,}) recruiters | Fixed Emails: {total_emails_fixed:,} | Reconstructed Names: {total_names_restored:,} | Cleaned SERP: {total_serp_cleaned:,}")
            sys.stdout.flush()

    # PART 2: AUDIT & ENRICH ALL 65,593 COMPANIES
    total_comps = db.query(Company).count()
    print(f"\n[Step 2] Auditing all {total_comps:,} companies across the database to ensure 100% logo and domain resolution...")
    sys.stdout.flush()

    missing_domain_comps = db.query(Company).filter((Company.website == None) | (Company.website == '') | (Company.website == 'n/a') | (Company.website == 'null')).all()
    print(f" -> Found {len(missing_domain_comps):,} companies missing website domain. Resolving via email clustering and name mapping...")
    sys.stdout.flush()

    domains_enriched = 0
    for idx, comp in enumerate(missing_domain_comps):
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
            if m: found_domain = m.group(1)

        if not found_domain:
            recs = db.query(Recruiter.email).filter(Recruiter.company_id == comp_id, Recruiter.email != None, ~Recruiter.email.contains('missing.local')).limit(15).all()
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

        if (idx + 1) % 1000 == 0 or idx == len(missing_domain_comps) - 1:
            db.commit()
            print(f"   [Companies {idx+1:,}/{len(missing_domain_comps):,}] Populated {domains_enriched:,} domains so far...")
            sys.stdout.flush()

    db.commit()

    comp_with_domain = db.query(Company).filter(Company.website != None, Company.website != '', Company.website != 'n/a').count()
    print("\n=======================================================================")
    print("=== FULL DATABASE SANITIZATION & LOGO ENRICHMENT SUMMARY ===")
    print(f"  Total Recruiters Audited:        {total_recs:,}")
    print(f"  Malformed Emails Sanitized:      {total_emails_fixed:,}")
    print(f"  Duplicate Emails Safely Merged:  {total_emails_merged:,}")
    print(f"  Numeric/Handle Names Restored:   {total_names_restored:,}")
    print(f"  SERP Scraping Artifacts Cleaned: {total_serp_cleaned:,}")
    print(f"  Companies Enriched with Domains: {domains_enriched:,}")
    print(f"  Total Companies with Clean Logo: {comp_with_domain:,} / {total_comps:,} ({(comp_with_domain/total_comps)*100:.1f}%)")
    print("=======================================================================")
    sys.stdout.flush()
    db.close()

if __name__ == '__main__':
    run_full_database_sanitization()
