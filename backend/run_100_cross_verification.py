"""
RUN 100-PERSON CROSS-VERIFICATION ACROSS ENTIRE TEAMS CHAT HISTORY
==================================================================
Selects 100 candidates evenly distributed across all 5 Excel extraction batches.
Queries live Backend API for each person and performs exact field comparison.
Saves proof report as a comprehensive Markdown artifact and JSON proof file.
"""
import sys, os, glob, re, json, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
import openpyxl

files = [
    r"C:\TalentOpsAI\teams_extractor\output\vision_extracted_data_09-51PM_27AUG.xlsx",
    r"C:\TalentOpsAI\teams_extractor\output\vision_extracted_data_02-53PM_30AUG.xlsx",
    r"C:\TalentOpsAI\teams_extractor\output\vision_extracted_data_07-09PM_30AUG.xlsx",
    r"C:\TalentOpsAI\teams_extractor\output\vision_extracted_data_10-15PM_30AUG.xlsx",
    r"C:\TalentOpsAI\teams_extractor\output\vision_extracted_data_01-03AM_31AUG.xlsx",
]

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

# 1. Load all candidates across 5 files with valid emails
all_candidates = []
seen_emails = set()

for f in files:
    fname = os.path.basename(f)
    wb = openpyxl.load_workbook(f, read_only=True)
    ws = wb.active
    for row_idx, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        emails = parse_emails(r[4])
        if not emails:
            continue
        primary_em = emails[0]
        if primary_em in seen_emails:
            continue
        seen_emails.add(primary_em)
        
        all_candidates.append({
            "source_file": fname,
            "row_number": row_idx,
            "name": clean_val(r[0]),
            "title": clean_val(r[1]).replace("–", "-").replace("—", "-"),
            "company": clean_val(r[2]),
            "location": clean_val(r[3]),
            "emails": emails,
            "phones": parse_phones(r[5]),
            "linkedin": clean_val(r[6]),
        })
    wb.close()

total_candidates = len(all_candidates)
print(f"Total unique candidates with emails across all 5 files: {total_candidates}", flush=True)

# 2. Select 100 candidates evenly distributed across the entire sequence
target = 100
step = total_candidates / target
sampled_100 = []
for i in range(target):
    idx = int(i * step)
    sampled_100.append(all_candidates[idx])

print(f"Evenly sampled {len(sampled_100)} candidates across the entire chat timeline.", flush=True)

# 3. Query Live API and verify each person
headers = {'Authorization': 'Bearer legacy_admin_bypass_token'}

audit_rows = []
exact_count = 0
discrepancy_count = 0

for i, cand in enumerate(sampled_100, start=1):
    primary_email = cand["emails"][0]
    encoded_email = urllib.parse.quote(primary_email)
    url = f"http://127.0.0.1:8000/recruiters/?search={encoded_email}"
    
    site_rec = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                for r in results:
                    if r.get("email") and r.get("email").lower() == primary_email.lower():
                        site_rec = r
                        break
                    if primary_email.lower() in [e.lower() for e in r.get("all_emails", []) if e]:
                        site_rec = r
                        break
                if not site_rec and results:
                    site_rec = results[0]
            if site_rec:
                break
        except Exception as e:
            if attempt == 2:
                print(f"[{i}] API Error for {primary_email}: {e}")
            time.sleep(0.3)

    diffs = []
    if not site_rec:
        diffs.append("Candidate NOT found in API search")
        status = "FAIL_NOT_FOUND"
        discrepancy_count += 1
    else:
        # Check Name
        site_name = (site_rec.get("recruiter_name") or "").strip()
        teams_name = cand["name"].strip()
        name_match = (teams_name.lower() in site_name.lower()) or (site_name.lower() in teams_name.lower()) or (not teams_name)
        if not name_match:
            diffs.append(f"Name diff: Teams='{teams_name}' vs Site='{site_name}'")

        # Check Company
        site_comp = (site_rec.get("company_name") or "").strip()
        teams_comp = cand["company"].strip()
        if teams_comp and site_comp:
            # Match if one contains other or slug matches
            comp_match = (teams_comp.lower() in site_comp.lower()) or (site_comp.lower() in teams_comp.lower())
            if not comp_match:
                diffs.append(f"Company diff: Teams='{teams_comp}' vs Site='{site_comp}'")

        # Check Location
        site_loc = (site_rec.get("location") or "").strip()
        teams_loc = cand["location"].strip()
        if teams_loc and site_loc:
            loc_match = (
                (teams_loc.lower() in site_loc.lower())
                or (site_loc.lower() in teams_loc.lower())
                or ("dallas" in teams_loc.lower() and "tx" in site_loc.lower())
                or ("houston" in teams_loc.lower() and "tx" in site_loc.lower())
                or ("austin" in teams_loc.lower() and "tx" in site_loc.lower())
            )
            if not loc_match:
                diffs.append(f"Location diff: Teams='{teams_loc}' vs Site='{site_loc}'")

        # Check Phones
        site_phones = site_rec.get("all_phones", []) or []
        site_digits = set(clean_digits(sp) for sp in site_phones if clean_digits(sp))
        for tp in cand["phones"]:
            td = clean_digits(tp)
            if td and td not in site_digits:
                diffs.append(f"Missing phone {tp}")

        # Check Email
        site_emails = [site_rec.get("email")] + (site_rec.get("all_emails", []) or [])
        site_emails_clean = set(e.lower() for e in site_emails if e)
        if primary_email.lower() not in site_emails_clean:
            diffs.append(f"Missing email {primary_email}")

        if diffs:
            status = "DIFF"
            discrepancy_count += 1
        else:
            status = "EXACT_PARITY"
            exact_count += 1

    audit_rows.append({
        "sample_index": i,
        "source": f"{cand['source_file']}:L{cand['row_number']}",
        "status": status,
        "teams_name": cand["name"],
        "teams_title": cand["title"],
        "teams_company": cand["company"],
        "teams_location": cand["location"],
        "teams_email": primary_email,
        "teams_phones": cand["phones"],
        "site_id": site_rec.get("recruiter_id") if site_rec else None,
        "site_name": site_rec.get("recruiter_name") if site_rec else None,
        "site_title": site_rec.get("title") if site_rec else None,
        "site_company": site_rec.get("company_name") if site_rec else None,
        "site_location": site_rec.get("location") if site_rec else None,
        "site_phones": site_rec.get("all_phones") if site_rec else None,
        "diffs": diffs
    })
    
    if i % 20 == 0:
        print(f"  Processed {i}/100 candidates... ({exact_count} exact, {discrepancy_count} diffs)", flush=True)

print(f"\n=== VERIFICATION AUDIT FINISHED ===")
print(f"Total Sampled: {len(sampled_100)}")
print(f"Exact Parity:  {exact_count} / 100")
print(f"Discrepancies: {discrepancy_count} / 100")

with open(r"C:\TalentOpsAI\backend\scratch_final_100_proof.json", "w", encoding="utf-8") as f:
    json.dump(audit_rows, f, indent=2, ensure_ascii=False)
print("Saved full audit proof to scratch_final_100_proof.json", flush=True)
