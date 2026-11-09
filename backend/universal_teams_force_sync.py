"""
UNIVERSAL TEAMS FORCE SYNC v2
=============================
Synchronizes ALL Teams candidates with valid emails from Excel into PostgreSQL.
- Creates any missing candidates with full Teams fields.
- Updates existing candidates so Name, Title, Company, Location, Phones, Emails, LinkedIn match Teams.
"""
import sys, os, glob, re, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import openpyxl
from app.database import SessionLocal
from app.models.models import Recruiter, Company
from sqlalchemy import func

def clean_val(v):
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in ("none", "null", "nan") else s

def clean_digits(ph):
    if not ph: return ""
    return re.sub(r"\D", "", str(ph))[-10:]

def parse_emails(raw):
    if not raw: return []
    res = []
    for p in re.split(r"[;\n,]+", str(raw)):
        p = p.strip().lower()
        if "@" in p and "." in p:
            res.append(p)
    return res

def parse_phones(raw):
    if not raw: return []
    res = []
    for p in re.split(r"[;\n]+", str(raw)):
        p = p.strip()
        if p and re.search(r"\d{3}", p):
            res.append(p)
    if not res and re.search(r"\d{3}", str(raw)):
        res.append(str(raw).strip())
    return res

print("1. Loading all Teams Excel records with valid emails...", flush=True)
files = sorted(glob.glob(r"C:\TalentOpsAI\teams_extractor\output\vision_*.xlsx"))
teams_candidates = []
seen_emails = set()

for f in files:
    wb = openpyxl.load_workbook(f, read_only=True)
    ws = wb.active
    for row_idx, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        name = clean_val(r[0])
        title = clean_val(r[1]).replace("–", "-").replace("—", "-")
        company = clean_val(r[2])
        location = clean_val(r[3])
        emails = parse_emails(r[4])
        phones = parse_phones(r[5])
        linkedin = clean_val(r[6])
        if linkedin and "linkedin.com" not in linkedin.lower():
            linkedin = ""

        if not emails:
            continue

        primary_em = emails[0]
        if primary_em in seen_emails:
            # Merge richer data into existing entry
            continue
        seen_emails.add(primary_em)

        teams_candidates.append({
            "source": f"{os.path.basename(f)}:{row_idx}",
            "name": name,
            "title": title,
            "company": company,
            "location": location,
            "emails": emails,
            "phones": phones,
            "linkedin": linkedin
        })
    wb.close()

print(f"   Loaded {len(teams_candidates)} unique Teams candidates with emails.", flush=True)

# 2. Connect to DB and load existing recruiters & companies
print("2. Loading DB state...", flush=True)
db = SessionLocal()

all_recs = db.query(Recruiter).all()
print(f"   Loaded {len(all_recs)} recruiters from PostgreSQL.", flush=True)

all_comps = db.query(Company).all()
comp_by_id = {c.company_id: c for c in all_comps}
comp_by_name = {c.company_name.lower().strip(): c for c in all_comps if c.company_name}
print(f"   Loaded {len(all_comps)} companies.", flush=True)

# Index recruiters by all emails
rec_by_email = {}
for r in all_recs:
    for em in [r.email, r.email2, r.email3, r.email4]:
        if em:
            rec_by_email[em.strip().lower()] = r

print(f"   Indexed {len(rec_by_email)} email mappings.", flush=True)

# 3. Synchronize / Ingest
print("3. Synchronizing candidates...", flush=True)
generic_titles = {
    'technical recruitment & staffing professional',
    'talent acquisition specialist', 'recruiter', 'recruiting',
    'staffing', 'contact', 'none', 'null', 'unknown', '',
    'staffing professional', 'technical recruiter',
    'recruitment professional', 'hr professional', 'specialist'
}

updated_count = 0
created_count = 0

def get_or_create_company(c_name):
    if not c_name:
        return None
    c_clean = c_name.strip()
    if not c_clean or c_clean.lower() in ("none", "null", "unknown company", "independent"):
        return None
    key = c_clean.lower()
    if key in comp_by_name:
        return comp_by_name[key]
    new_c = Company(
        company_name=c_clean,
        canonical_name=c_clean,
        is_active=True,
        data_source="teams"
    )
    db.add(new_c)
    db.flush()
    comp_by_name[key] = new_c
    comp_by_id[new_c.company_id] = new_c
    return new_c

for cand in teams_candidates:
    rec = None
    
    # Match by email
    for em in cand["emails"]:
        if em in rec_by_email:
            rec = rec_by_email[em]
            break

    if rec:
        # UPDATE MATCHED RECRUITER
        changed = False
        
        # Data source must be teams
        if rec.data_source != "teams":
            rec.data_source = "teams"
            changed = True

        # Name
        if cand["name"] and (not rec.recruiter_name or len(cand["name"]) > len(rec.recruiter_name)):
            rec.recruiter_name = cand["name"]
            changed = True
            
        # Title - Always use Teams title if available and non-empty
        if cand["title"]:
            cur_t = (rec.title or "").strip()
            if cur_t.lower() in generic_titles or len(cand["title"]) >= len(cur_t):
                rec.title = cand["title"]
                changed = True
                
        # Location - Always prioritize Teams location
        if cand["location"]:
            cur_l = (rec.location or "").strip()
            if not cur_l or cur_l.lower() in ("united states", "us", "usa", "none", "null") or len(cand["location"]) >= len(cur_l):
                rec.location = cand["location"]
                changed = True

        # Company - Always map to exact Teams company
        if cand["company"]:
            c_obj = get_or_create_company(cand["company"])
            if c_obj and rec.company_id != c_obj.company_id:
                rec.company_id = c_obj.company_id
                changed = True

        # Phones: merge all
        cur_phone_digits = set()
        for slot in [rec.phone, rec.phone2, rec.phone3, rec.phone4]:
            d = clean_digits(slot)
            if d: cur_phone_digits.add(d)
        if rec.alternate_phones:
            try:
                alt = json.loads(rec.alternate_phones) if rec.alternate_phones.startswith("[") else [rec.alternate_phones]
            except:
                alt = [rec.alternate_phones]
            for a in alt:
                d = clean_digits(a)
                if d: cur_phone_digits.add(d)

        missing_phones = []
        for p in cand["phones"]:
            d = clean_digits(p)
            if d and d not in cur_phone_digits:
                missing_phones.append(p)
                cur_phone_digits.add(d)

        if not rec.phone and cand["phones"]:
            rec.phone = cand["phones"][0]
            changed = True
            missing_phones = [p for p in missing_phones if clean_digits(p) != clean_digits(cand["phones"][0])]

        if missing_phones:
            empty_slots = []
            if not rec.phone: empty_slots.append("phone")
            if not rec.phone2: empty_slots.append("phone2")
            if not rec.phone3: empty_slots.append("phone3")
            if not rec.phone4: empty_slots.append("phone4")
            for mp in missing_phones:
                if empty_slots:
                    slot = empty_slots.pop(0)
                    setattr(rec, slot, mp)
                    changed = True
                else:
                    try:
                        alt = json.loads(rec.alternate_phones) if rec.alternate_phones and rec.alternate_phones.startswith("[") else []
                    except:
                        alt = [rec.alternate_phones] if rec.alternate_phones else []
                    alt.append(mp)
                    rec.alternate_phones = json.dumps(alt)
                    changed = True

        # Emails: merge all
        cur_emails = set()
        for slot in [rec.email, rec.email2, rec.email3, rec.email4]:
            if slot: cur_emails.add(slot.strip().lower())
        missing_emails = [e for e in cand["emails"] if e.lower() not in cur_emails]
        if not rec.email and cand["emails"]:
            rec.email = cand["emails"][0]
            changed = True
            missing_emails = missing_emails[1:]
        if missing_emails:
            empty_slots = []
            if not rec.email: empty_slots.append("email")
            if not rec.email2: empty_slots.append("email2")
            if not rec.email3: empty_slots.append("email3")
            if not rec.email4: empty_slots.append("email4")
            for me in missing_emails:
                if empty_slots:
                    slot = empty_slots.pop(0)
                    setattr(rec, slot, me)
                    changed = True
                else:
                    try:
                        alt = json.loads(rec.alternate_emails) if rec.alternate_emails and rec.alternate_emails.startswith("[") else []
                    except:
                        alt = [rec.alternate_emails] if rec.alternate_emails else []
                    alt.append(me)
                    rec.alternate_emails = json.dumps(alt)
                    changed = True

        # LinkedIn
        if cand["linkedin"] and not rec.linkedin:
            rec.linkedin = cand["linkedin"]
            changed = True

        if changed:
            updated_count += 1

    else:
        # CREATE NEW RECRUITER
        c_obj = get_or_create_company(cand["company"]) if cand["company"] else None
        emails = cand["emails"]
        phones = cand["phones"]
        
        new_rec = Recruiter(
            recruiter_name=cand["name"] or "Teams Candidate",
            title=cand["title"] or "Technical Recruiter",
            location=cand["location"],
            company_id=c_obj.company_id if c_obj else None,
            email=emails[0],
            email2=emails[1] if len(emails) > 1 else None,
            email3=emails[2] if len(emails) > 2 else None,
            email4=emails[3] if len(emails) > 3 else None,
            alternate_emails=json.dumps(emails[4:]) if len(emails) > 4 else None,
            phone=phones[0] if phones else None,
            phone2=phones[1] if len(phones) > 1 else None,
            phone3=phones[2] if len(phones) > 2 else None,
            phone4=phones[3] if len(phones) > 3 else None,
            alternate_phones=json.dumps(phones[4:]) if len(phones) > 4 else None,
            linkedin=cand["linkedin"],
            data_source="teams",
            is_active=True
        )
        db.add(new_rec)
        db.flush()
        
        for em in emails:
            rec_by_email[em] = new_rec
            
        created_count += 1

print(f"4. Committing changes: {updated_count} updated, {created_count} newly created...", flush=True)
db.commit()
db.close()
print("   Committed to PostgreSQL successfully!", flush=True)
