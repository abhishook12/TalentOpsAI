import re
from app.database import SessionLocal
from app.models.models import Company

blockedLogoDomains = {
    'apollo.io', 'crunchbase.com', 'facebook.com', 'glassdoor.com',
    'hasdic.org', 'indeed.com', 'linkedin.com', 'rocketreach.co',
    'signalhire.com', 'twitter.com', 'wikipedia.org', 'x.com', 'zoominfo.com'
}

knownStaffingDomains = {
    'airswift': 'airswift.com', 'air swift': 'airswift.com', 'tekpartners': 'tekpartners.com',
    'tek partners': 'tekpartners.com', 'robert half': 'roberthalf.com', 'insight global': 'insightglobal.com',
    '3ci': '3ci.tech', 'teksystems': 'teksystems.com', 'kforce': 'kforce.com',
    'beacon hill': 'beaconhillstaffing.com', 'beacon hill staffing group': 'beaconhillstaffing.com',
    'apex systems': 'apexsystems.com', 'randstad': 'randstadusa.com', 'adecco': 'adeccousa.com',
    'kelly services': 'kellyservices.com', 'kelly': 'kellyservices.com', 'manpower': 'manpowergroup.com',
    'manpowergroup': 'manpowergroup.com', 'actalent': 'actalenttalent.com', 'cybercoders': 'cybercoders.com',
    'bairesdev': 'bairesdev.com', 'toptal': 'toptal.com', 'oxford global resources': 'oxfordcorp.com',
    'modis': 'modis.com', 'akkodis': 'akkodis.com', 'judge group': 'judge.com',
    'the judge group': 'judge.com', 'collabera': 'collabera.com', 'matrix resources': 'matrixres.com',
    'eliassen group': 'eliassen.com', 'addison group': 'addisongroup.com', 'hays': 'hays.com',
    'lucas group': 'lucasgroup.com', 'korn ferry': 'kornferry.com', 'heidrick & struggles': 'heidrick.com',
    'spencer stuart': 'spencerstuart.com', 'russell reynolds': 'russellreynolds.com',
    'egon zehnder': 'egonzehnder.com', 'michael page': 'michaelpage.com', 'pagegroup': 'page.com',
    'robert walters': 'robertwalters.com', 'allegis group': 'allegisgroup.com', 'aston carter': 'astoncarter.com',
    'aerotek': 'aerotek.com', 'guidant global': 'guidantglobal.com', 'impellam': 'impellam.com',
    'amn healthcare': 'amnhealthcare.com', 'cross country healthcare': 'crosscountryhealthcare.com',
    'chg healthcare': 'chghealthcare.com', 'jackson healthcare': 'jacksonhealthcare.com',
    'aya healthcare': 'ayahealthcare.com', 'favorite healthcare staffing': 'favoritestaffing.com',
    'medical solutions': 'medicalsolutions.com', 'maxim healthcare': 'maximhealthcare.com',
    'hiregenics': 'hiregenics.com', 'pontoon': 'pontoonsolutions.com', 'us navy': 'navy.mil',
    'u.s. navy': 'navy.mil', 'us army': 'army.mil', 'u.s. army': 'army.mil',
    'us air force': 'af.mil', 'u.s. air force': 'af.mil', 'accenture': 'accenture.com',
    'deloitte': 'deloitte.com', 'pwc': 'pwc.com', 'kpmg': 'kpmg.com', 'ey': 'ey.com',
    'capgemini': 'capgemini.com', 'cognizant': 'cognizant.com', 'tcs': 'tcs.com',
    'infosys': 'infosys.com', 'wipro': 'wipro.com', 'hcltech': 'hcltech.com',
    'tech mahindra': 'techmahindra.com', 'ibm': 'ibm.com', 'microsoft': 'microsoft.com',
    'google': 'google.com', 'amazon': 'amazon.com', 'meta': 'meta.com', 'apple': 'apple.com',
    'netflix': 'netflix.com', 'stand 8': 'stand8.io', 'stand8': 'stand8.io',
    'talonpro': 'talonpro.com', 'anagh technologies': 'anaghtech.com',
    'anagh technologies inc': 'anaghtech.com', 'anaghtech': 'anaghtech.com',
    'amanda cucinotti': 'medasource.com', 'medasource': 'medasource.com', 'russelltobin': 'russelltobin.com',
    'russell tobin': 'russelltobin.com', 'kellymitchell': 'kellymitchell.com',
    'kelly mitchell': 'kellymitchell.com', 'brooksource': 'brooksource.com',
    'kellyscientific': 'kellyscientific.com', 'kelly scientific': 'kellyscientific.com',
    'cisco': 'cisco.com', 'oracle': 'oracle.com', 'salesforce': 'salesforce.com',
    'workday': 'workday.com', 'servicenow': 'servicenow.com'
}

def inferDomainFromName(name):
    if not name: return None
    clean = re.sub(r'\[duplicate\]\s*', '', str(name).strip().lower(), flags=re.IGNORECASE).strip()
    if clean in knownStaffingDomains:
        return knownStaffingDomains[clean]
    for k, v in knownStaffingDomains.items():
        if k in clean and len(k) > 3: return v
    stripped = re.sub(r'\b(llc|inc|corp|corporation|company|group|limited|ltd|solutions|technologies|services|staffing|global)\b', '', clean, flags=re.IGNORECASE)
    stripped = re.sub(r'[^a-z0-9]', '', stripped)
    if stripped and len(stripped) >= 3 and not stripped.isdigit():
        return f"{stripped}.com"
    return None

def normalizeLogoDomain(domain, name):
    target = domain
    if not target or str(target).lower() in ['null', 'n/a']:
        target = inferDomainFromName(name)
    if not target: return None
    
    cleaned = str(target).strip().lower()
    cleaned = re.sub(r'\.dup\.\d+$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.\.dup\.\d+$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[duplicate\]\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.split(r'[\s;|]+', cleaned)[0]
    cleaned = re.sub(r'^https?://', '', cleaned)
    cleaned = re.sub(r'^www\.', '', cleaned)
    cleaned = cleaned.split('/')[0]

    if not cleaned or cleaned in blockedLogoDomains or '.dup.' in cleaned:
        return inferDomainFromName(name)

    return cleaned

def check_frontend():
    db = SessionLocal()
    companies = db.query(Company).all()
    
    missing = []
    for c in companies:
        domain = c.metadata_json.get("logo_domain") if isinstance(c.metadata_json, dict) else None
        if not domain:
            domain = c.website or c.email_pattern
            
        final_domain = normalizeLogoDomain(domain, c.company_name)
        if not final_domain:
            missing.append(c)
            
    print(f"Total companies failing frontend logo check: {len(missing)}")
    if missing:
        print("Sample missing:")
        for c in missing[:10]:
            print(f" - {c.company_name} (website: {c.website}, email: {c.email_pattern})")
            
if __name__ == "__main__":
    check_frontend()
