"""
MASTER TEAMS EXHAUSTIVE SYNC
============================
Synchronizes the ENTIRE Microsoft Teams chat history (all 6,152 unique candidates:
both email candidates and phone-only candidates) from master_sheet.xlsx, July batches,
and August batches into PostgreSQL and Parquet.
"""
import sys, os, glob, re, json, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\TalentOpsAI\backend")

import openpyxl
from app.database import SessionLocal
from app.models.models import Recruiter, Company

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

def clean_phone_str(p):
    if not p: return ""
    p = str(p).strip()
    p = re.sub(r"(?i)(default|mobile|work|office|direct|primary|cell)$", "", p).strip()
    return p[:80]

def parse_phones(raw):
    if not raw: return []
    res = []
    for p in re.split(r"[;\n]+", str(raw)):
        cp = clean_phone_str(p)
        if cp and re.search(r"\d{3}", cp):
            res.append(cp)
    if not res and re.search(r"\d{3}", str(raw)):
        cp = clean_phone_str(str(raw))
        if cp:
            res.append(cp)
    return res

# 1. Gather all files across both directories
all_files = []
master_path = r"C:\Users\User\Documents\teams extractor files\master_sheet.xlsx"
if os.path.exists(master_path):
    all_files.append(master_path)

all_files.extend(sorted(glob.glob(r"C:\TalentOpsAI\teams_extractor\output\vision_*.xlsx")))
all_files.extend([
    f for f in sorted(glob.glob(r"C:\Users\User\Documents\teams extractor files\*.xlsx"))
    if "master_sheet" not in f and not os.path.basename(f).startswith("~$")
])

print(f"1. Scanning {len(all_files)} Teams extraction files...", flush=True)

candidates_by_email = {}
candidates_by_phone = {}
total_raw_rows = 0

for file_idx, fpath in enumerate(all_files, 1):
    fname = os.path.basename(fpath)
    try:
        wb = openpyxl.load_workbook(fpath, read_only=True)
        ws = wb.active
        for row_idx, r in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            total_raw_rows += 1
            name = clean_val(r[0])
            title = clean_val(r[1]).replace("–", "-").replace("—", "-") if len(r) > 1 else ""
            company = clean_val(r[2]) if len(r) > 2 else ""
            location = clean_val(r[3]) if len(r) > 3 else ""
            emails = parse_emails(r[4]) if len(r) > 4 else []
            phones = parse_phones(r[5]) if len(r) > 5 else []
            linkedin = clean_val(r[6]) if len(r) > 6 else ""
            if linkedin and "linkedin.com" not in linkedin.lower():
                linkedin = ""

            if not emails and not phones:
                continue

            entry = {
                "source": f"{fname}:L{row_idx}",
                "name": name,
                "title": title,
                "company": company,
                "location": location,
                "emails": emails,
                "phones": phones,
                "linkedin": linkedin
            }

            if emails:
                primary_em = emails[0]
                if primary_em not in candidates_by_email:
                    candidates_by_email[primary_em] = entry
                else:
                    # Merge richer info
                    cur = candidates_by_email[primary_em]
                    if not cur["name"] and entry["name"]: cur["name"] = entry["name"]
                    if not cur["title"] and entry["title"]: cur["title"] = entry["title"]
                    if not cur["company"] and entry["company"]: cur["company"] = entry["company"]
                    if not cur["location"] and entry["location"]: cur["location"] = entry["location"]
                    if not cur["linkedin"] and entry["linkedin"]: cur["linkedin"] = entry["linkedin"]
                    for em in emails:
                        if em not in cur["emails"]: cur["emails"].append(em)
                    for ph in phones:
                        if ph not in cur["phones"]: cur["phones"].append(ph)
            else:
                # Phone-only candidate
                d = clean_digits(phones[0])
                if d:
                    if d not in candidates_by_phone:
                        candidates_by_phone[d] = entry
                    else:
                        cur = candidates_by_phone[d]
                        if not cur["name"] and entry["name"]: cur["name"] = entry["name"]
                        if not cur["title"] and entry["title"]: cur["title"] = entry["title"]
                        if not cur["company"] and entry["company"]: cur["company"] = entry["company"]
                        if not cur["location"] and entry["location"]: cur["location"] = entry["location"]
                        for ph in phones:
                            if ph not in cur["phones"]: cur["phones"].append(ph)
        wb.close()
    except Exception as e:
        print(f"   Error reading {fname}: {e}", flush=True)

print(f"   Total raw rows scanned: {total_raw_rows}", flush=True)
print(f"   Unique candidates with email: {len(candidates_by_email)}", flush=True)
print(f"   Unique candidates phone-only: {len(candidates_by_phone)}", flush=True)

# 2. Connect to DB and load existing recruiters & companies
print("2. Connecting to PostgreSQL and loading state...", flush=True)
db = SessionLocal()

all_recs = db.query(Recruiter).all()
print(f"   Loaded {len(all_recs)} recruiters from PostgreSQL.", flush=True)

all_comps = db.query(Company).all()
comp_by_name = {c.company_name.lower().strip(): c for c in all_comps if c.company_name}
print(f"   Loaded {len(all_comps)} companies.", flush=True)

def get_or_create_company(c_name):
    if not c_name: return None
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
    return new_c

# Index recruiters
rec_by_email = {}
rec_by_phone_digits = {}

for r in all_recs:
    for em in [r.email, r.email2, r.email3, r.email4]:
        if em:
            rec_by_email[em.strip().lower()] = r
    if r.alternate_emails:
        try:
            alt = json.loads(r.alternate_emails) if r.alternate_emails.startswith("[") else [r.alternate_emails]
            for a in alt:
                if a and isinstance(a, str):
                    rec_by_email[a.strip().lower()] = r
        except:
            pass

    for slot in [r.phone, r.phone2, r.phone3, r.phone4]:
        d = clean_digits(slot)
        if d:
            rec_by_phone_digits[d] = r
    if r.alternate_phones:
        try:
            alt = json.loads(r.alternate_phones) if r.alternate_phones.startswith("[") else [r.alternate_phones]
            for a in alt:
                d = clean_digits(a)
                if d:
                    rec_by_phone_digits[d] = r
        except:
            pass

print(f"   Indexed {len(rec_by_email)} email mappings, {len(rec_by_phone_digits)} phone mappings.", flush=True)

# 3. Synchronize All Candidates
print("3. Synchronizing all Teams candidates...", flush=True)
updated_count = 0
created_count = 0

all_candidates_list = list(candidates_by_email.values()) + list(candidates_by_phone.values())

for cand_idx, cand in enumerate(all_candidates_list):
    rec = None
    
    # Match by email first
    for em in cand["emails"]:
        if em in rec_by_email:
            rec = rec_by_email[em]
            break
            
    # Match by phone digits if no email match
    if not rec:
        for ph in cand["phones"]:
            d = clean_digits(ph)
            if d in rec_by_phone_digits:
                rec = rec_by_phone_digits[d]
                break

    if rec:
        # UPDATE
        changed = False
        if rec.data_source != "teams":
            rec.data_source = "teams"
            changed = True
            
        if cand["name"] and (not rec.recruiter_name or len(cand["name"]) > len(rec.recruiter_name)):
            rec.recruiter_name = cand["name"]
            changed = True
            
        if cand["title"]:
            cur_t = (rec.title or "").strip()
            if not cur_t or len(cand["title"]) >= len(cur_t):
                rec.title = cand["title"]
                changed = True
                
        if cand["location"]:
            cur_l = (rec.location or "").strip()
            if not cur_l or cur_l.lower() in ("united states", "us", "usa", "none", "null") or len(cand["location"]) >= len(cur_l):
                rec.location = cand["location"]
                changed = True
                
        if cand["company"]:
            c_obj = get_or_create_company(cand["company"])
            if c_obj and rec.company_id != c_obj.company_id:
                rec.company_id = c_obj.company_id
                changed = True

        # Merge Phones
        cur_phone_digits = set()
        for slot in [rec.phone, rec.phone2, rec.phone3, rec.phone4]:
            d = clean_digits(slot)
            if d: cur_phone_digits.add(d)
        if rec.alternate_phones:
            try:
                alt = json.loads(rec.alternate_phones) if rec.alternate_phones.startswith("[") else [rec.alternate_phones]
                for a in alt:
                    d = clean_digits(a)
                    if d: cur_phone_digits.add(d)
            except:
                pass

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

        # Merge Emails
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
            email=emails[0] if emails else None,
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
        for ph in phones:
            d = clean_digits(ph)
            if d:
                rec_by_phone_digits[d] = new_rec

        created_count += 1

    if (cand_idx + 1) % 500 == 0:
        db.commit()
        print(f"   Processed {cand_idx + 1}/{len(all_candidates_list)}... ({updated_count} updated, {created_count} created)", flush=True)

db.commit()
print(f"4. Finished Database Committal: {updated_count} updated, {created_count} newly created!", flush=True)
db.close()
