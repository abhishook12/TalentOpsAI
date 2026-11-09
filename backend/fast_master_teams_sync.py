"""
FAST MASTER TEAMS-TO-DB FORCE SYNC
==================================
Lightning fast:
1. Loads Teams data from Excel & Staging in memory.
2. Loads all recruiters from PostgreSQL into memory.
3. Performs in-memory exact matching and field synchronization.
4. Commits changes in batches with progress logging.
"""
import sys, os, re, json, glob, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import openpyxl
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from sqlalchemy import func

def parse_phones(raw):
    if not raw: return []
    raw = str(raw).strip()
    if not raw or raw.lower() == 'none': return []
    phones = []
    for part in re.split(r'[;\n]+', raw):
        part = part.strip()
        if part and re.search(r'\d{3}', part):
            phones.append(part)
    if not phones and re.search(r'\d{3}', raw):
        phones.append(raw)
    return phones

def parse_emails(raw):
    if not raw: return []
    raw = str(raw).strip()
    if not raw or raw.lower() == 'none': return []
    emails = []
    for part in re.split(r'[;\n,]+', raw):
        part = part.strip().lower()
        if '@' in part and '.' in part:
            emails.append(part)
    return emails

def clean_str(val):
    v = str(val or '').strip()
    return '' if v.lower() == 'none' else v

def clean_digits(phone):
    if not phone: return ''
    return re.sub(r'\D', '', str(phone))[-10:]

# ── 1. Load Excel ──
print("1. Loading Teams Excel files...", flush=True)
teams_by_email = {}
excel_count = 0
for f in sorted(glob.glob(r'C:\TalentOpsAI\teams_extractor\output\vision_*.xlsx')):
    try:
        wb = openpyxl.load_workbook(f, read_only=True)
    except:
        continue
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        name = clean_str(row[0])
        title = clean_str(row[1])
        company = clean_str(row[2])
        location = clean_str(row[3])
        phones = parse_phones(row[5])
        linkedin = clean_str(row[6])
        emails = parse_emails(row[4])
        
        if not emails:
            continue
        excel_count += 1

        entry = {
            'name': name, 'title': title, 'company': company,
            'location': location, 'phones': phones, 'linkedin': linkedin,
            'extra_emails': emails[1:],
        }
        
        for em in emails:
            if em in teams_by_email:
                ex = teams_by_email[em]
                if len(title) > len(ex.get('title', '')): ex['title'] = title
                if len(location) > len(ex.get('location', '')): ex['location'] = location
                if len(company) > len(ex.get('company', '')): ex['company'] = company
                if linkedin and not ex.get('linkedin'): ex['linkedin'] = linkedin
                ex_digits = set(re.sub(r'\D','',p)[-10:] for p in ex.get('phones',[]))
                for p in phones:
                    d = re.sub(r'\D','',p)[-10:]
                    if d and d not in ex_digits:
                        ex['phones'].append(p)
                        ex_digits.add(d)
            else:
                teams_by_email[em] = entry
    wb.close()

print(f"   Excel entries: {excel_count}, unique emails: {len(teams_by_email)}", flush=True)

# ── 2. Load Staging ──
print("2. Loading Teams staging records...", flush=True)
db = SessionLocal()
from app.models.staging_models import DiscoveryStaging

staging_teams = db.execute(
    db.query(DiscoveryStaging.raw_name, DiscoveryStaging.raw_title, 
             DiscoveryStaging.raw_company, DiscoveryStaging.raw_location,
             DiscoveryStaging.raw_phone, DiscoveryStaging.raw_email,
             DiscoveryStaging.raw_linkedin)
    .filter(DiscoveryStaging.extraction_source.in_([
        'teams_uia_background', 'teams_extractor', 'teams_audit'
    ])).statement
).fetchall()

staging_count = 0
for sr in staging_teams:
    raw_name, raw_title, raw_company, raw_location, raw_phone, raw_email, raw_linkedin = sr
    emails = parse_emails(raw_email)
    if not emails:
        continue
    staging_count += 1
    
    phones = parse_phones(raw_phone)
    entry = {
        'name': clean_str(raw_name),
        'title': clean_str(raw_title),
        'company': clean_str(raw_company),
        'location': clean_str(raw_location),
        'phones': phones,
        'linkedin': clean_str(raw_linkedin),
        'extra_emails': emails[1:],
    }
    
    for em in emails:
        if em in teams_by_email:
            ex = teams_by_email[em]
            if len(clean_str(raw_title)) > len(ex.get('title', '')): ex['title'] = clean_str(raw_title)
            if len(clean_str(raw_location)) > len(ex.get('location', '')): ex['location'] = clean_str(raw_location)
            if len(clean_str(raw_company)) > len(ex.get('company', '')): ex['company'] = clean_str(raw_company)
            if clean_str(raw_linkedin) and not ex.get('linkedin'): ex['linkedin'] = clean_str(raw_linkedin)
            ex_digits = set(re.sub(r'\D','',p)[-10:] for p in ex.get('phones',[]))
            for p in phones:
                d = re.sub(r'\D','',p)[-10:]
                if d and d not in ex_digits:
                    ex['phones'].append(p)
                    ex_digits.add(d)
        else:
            teams_by_email[em] = entry

print(f"   Staging entries: {staging_count}, total unified emails: {len(teams_by_email)}", flush=True)

# ── 3. Load all recruiters into memory at once ──
print("3. Loading all recruiters from database into memory...", flush=True)
all_recruiters = db.query(Recruiter).all()
print(f"   Loaded {len(all_recruiters)} recruiters from database.", flush=True)

# Also load companies map
companies = db.query(Company).all()
company_by_id = {c.company_id: c for c in companies}
print(f"   Loaded {len(companies)} companies into memory.", flush=True)

# Index recruiters by all their emails
recruiter_by_email = {}
for r in all_recruiters:
    for em in [r.email, r.email2, r.email3, r.email4]:
        if em:
            recruiter_by_email[em.strip().lower()] = r

print(f"   Indexed {len(recruiter_by_email)} email mappings.", flush=True)

# ── 4. Apply Updates in Memory ──
print("4. Applying field synchronizations...", flush=True)
generic_titles = {
    'technical recruitment & staffing professional',
    'talent acquisition specialist', 'recruiter', 'recruiting',
    'staffing', 'contact', 'none', 'null', 'unknown', '',
    'staffing professional', 'technical recruiter',
    'recruitment professional', 'hr professional',
}

updated_recruiters = set()
updates_log = []

for email, data in teams_by_email.items():
    rec = recruiter_by_email.get(email)
    if not rec:
        continue
    
    changes = []
    
    # Title
    teams_title = data.get('title', '').strip()
    db_title = (rec.title or '').strip()
    if teams_title and teams_title != db_title:
        if (len(teams_title) > len(db_title)) or (db_title.lower() in generic_titles):
            # Clean hyphens
            cleaned_title = teams_title.replace('–', '-').replace('—', '-')
            changes.append(f"TITLE: [{db_title[:40]}] -> [{cleaned_title[:40]}]")
            rec.title = cleaned_title

    # Location
    teams_loc = data.get('location', '').strip()
    db_loc = (rec.location or '').strip()
    if teams_loc and teams_loc != db_loc:
        teams_parts = len(teams_loc.split(','))
        db_parts = len(db_loc.split(',')) if db_loc else 0
        if teams_parts >= db_parts or not db_loc:
            changes.append(f"LOCATION: [{db_loc[:30]}] -> [{teams_loc[:30]}]")
            rec.location = teams_loc

    # Phones
    teams_phones = data.get('phones', [])
    if teams_phones:
        existing_digits = set()
        for slot in [rec.phone, rec.phone2, rec.phone3, rec.phone4]:
            d = clean_digits(slot)
            if d: existing_digits.add(d)
        if rec.alternate_phones:
            try:
                alt = json.loads(rec.alternate_phones) if rec.alternate_phones.startswith('[') else [rec.alternate_phones]
            except:
                alt = [rec.alternate_phones]
            for a in alt:
                d = clean_digits(a)
                if d: existing_digits.add(d)

        missing = []
        for p in teams_phones:
            d = clean_digits(p)
            if d and d not in existing_digits:
                missing.append(p)
                existing_digits.add(d)

        if not rec.phone and teams_phones:
            if teams_phones[0] not in missing:
                missing.insert(0, teams_phones[0])

        if missing:
            slots = []
            if not rec.phone: slots.append('phone')
            if not rec.phone2: slots.append('phone2')
            if not rec.phone3: slots.append('phone3')
            if not rec.phone4: slots.append('phone4')

            for mp in missing:
                if slots:
                    slot = slots.pop(0)
                    setattr(rec, slot, mp)
                    changes.append(f"{slot.upper()}: -> [{mp}]")
                else:
                    try:
                        alt = json.loads(rec.alternate_phones) if rec.alternate_phones and rec.alternate_phones.startswith('[') else []
                    except:
                        alt = [rec.alternate_phones] if rec.alternate_phones else []
                    alt.append(mp)
                    rec.alternate_phones = json.dumps(alt)
                    changes.append(f"ALT_PHONES: +[{mp}]")

    # Company
    teams_comp = data.get('company', '').strip()
    if teams_comp and rec.company_id and rec.company_id in company_by_id:
        comp = company_by_id[rec.company_id]
        db_comp = (comp.company_name or '').strip()
        if teams_comp.lower() != db_comp.lower() and len(teams_comp) > len(db_comp):
            changes.append(f"COMPANY: [{db_comp}] -> [{teams_comp}]")
            comp.company_name = teams_comp

    # LinkedIn
    teams_li = data.get('linkedin', '').strip()
    if teams_li and not rec.linkedin and 'linkedin.com' in teams_li.lower():
        changes.append(f"LINKEDIN: -> [{teams_li[:50]}]")
        rec.linkedin = teams_li

    if changes:
        updated_recruiters.add(rec.recruiter_id)
        updates_log.append({
            'email': email,
            'name': rec.recruiter_name,
            'rec_id': rec.recruiter_id,
            'changes': changes
        })

print(f"   Total recruiters with field updates: {len(updated_recruiters)}", flush=True)
print(f"   Total field updates: {sum(len(u['changes']) for u in updates_log)}", flush=True)

# ── 5. Commit to Database ──
print("5. Committing changes to PostgreSQL...", flush=True)
db.commit()
db.close()
print("   Committed successfully!", flush=True)

# Save sample log
with open(r"C:\TalentOpsAI\backend\scratch_fast_sync_log.json", "w", encoding="utf-8") as f:
    json.dump(updates_log[:100], f, indent=2, ensure_ascii=False)

print("\n=== SAMPLE UPDATES (first 10) ===")
for u in updates_log[:10]:
    print(f"[{u['rec_id']}] {u['name']} ({u['email']}):")
    for c in u['changes']:
        print(f"   {c}")

print("\n=== FAST SYNC COMPLETE ===")
