"""
resume_sheet_harvester.py — High-Throughput Sheet Harvester Resumption Worker
=============================================================================
Resumes sequential sheet-by-sheet harvesting:
Picks pending companies from the current active sheet (Ritik -> Anek -> Suhani),
extracts their website, careers/jobs, DNS status, ATS, and recruiter data,
stages entities into discovery_staging, and processes them through DiscoveryProcessor.
"""

import sys
import os
import re
import json
import time
import uuid
import socket
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app.models.staging_models import DiscoveryStaging
from app.services.sheet_target_seeder import sheet_target_seeder
from app.services.discovery_processor import DiscoveryProcessor

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
PHONE_REGEX = re.compile(r'(?:\+?1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b')

def harvest_single_company(target: dict) -> dict:
    sheet_name = target.get("sheet", "Unknown")
    cname = target.get("company_name", "")
    dom = target.get("domain", "")
    
    result = {
        "sheet": sheet_name,
        "company_name": cname,
        "domain": dom,
        "dns_active": False,
        "http_status": None,
        "title": "",
        "contacts_found": [],
        "careers_url": None,
        "ats_type": None,
        "staged_count": 0,
    }
    
    # 1. DNS check
    try:
        socket.gethostbyname(dom)
        result["dns_active"] = True
    except Exception:
        result["dns_active"] = False
        sheet_target_seeder.mark_domain_harvested(dom, sheet=sheet_name, details={"status": "DNS_FAIL"})
        return result
        
    # 2. HTTP Fetch homepage
    home_url = f"https://{dom}"
    html = ""
    try:
        r = requests.get(home_url, headers=headers, verify=False, timeout=5)
        result["http_status"] = r.status_code
        html = r.text
    except Exception:
        try:
            home_url = f"http://{dom}"
            r = requests.get(home_url, headers=headers, verify=False, timeout=5)
            result["http_status"] = r.status_code
            html = r.text
        except Exception:
            result["http_status"] = "TIMEOUT/ERR"
            sheet_target_seeder.mark_domain_harvested(dom, sheet=sheet_name, details={"status": "TIMEOUT/ERR"})
            return result

    if not html:
        sheet_target_seeder.mark_domain_harvested(dom, sheet=sheet_name, details={"status": result["http_status"]})
        return result

    soup = BeautifulSoup(html, 'html.parser')
    result["title"] = soup.title.string.strip() if soup.title and soup.title.string else cname

    # 3. Discover Team / Careers / Jobs pages
    career_links = []
    team_links = []
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(k in href for k in ['career', 'jobs', 'openings', 'work-with-us', 'job-search']):
            full = href if href.startswith('http') else f"https://{dom}/{href.lstrip('/')}"
            career_links.append(full)
        if any(k in href for k in ['team', 'about', 'leadership', 'people']):
            full = href if href.startswith('http') else f"https://{dom}/{href.lstrip('/')}"
            team_links.append(full)

    if career_links:
        result["careers_url"] = career_links[0]
        c_str = str(career_links[:5])
        if 'greenhouse' in c_str:
            result["ats_type"] = "Greenhouse"
        elif 'lever.co' in c_str:
            result["ats_type"] = "Lever"
        elif 'ceipal' in c_str:
            result["ats_type"] = "Ceipal"
        elif 'jobdiva' in c_str:
            result["ats_type"] = "JobDiva"
        elif 'bullhorn' in c_str:
            result["ats_type"] = "Bullhorn"
        elif 'workday' in c_str:
            result["ats_type"] = "Workday"
        else:
            result["ats_type"] = "Custom Portal"

    # 4. Extract emails matching domain
    all_emails = set(EMAIL_REGEX.findall(html))
    corp_emails = [em for em in all_emails if dom.lower() in em.lower()]
    all_phones = list(set(PHONE_REGEX.findall(html)))[:2]
    
    hint_rec = target.get("recruiter_name")
    hint_em = target.get("recruiter_email")
    if hint_rec and len(hint_rec) > 3:
        result["contacts_found"].append({
            "name": hint_rec,
            "title": "Recruiter / Staffing Specialist",
            "email": hint_em or (corp_emails[0] if corp_emails else None),
            "phone": all_phones[0] if all_phones else None
        })

    # Stage entity into DiscoveryStaging
    try:
        with SessionLocal() as db:
            comp_staging = DiscoveryStaging(
                batch_id=f"RESUME-{sheet_name.upper()}-{int(time.time())}",
                discovery_id=f"DS-COMP-{uuid.uuid4().hex[:12]}",
                device_id="harvest_engine_resume_node",
                owner_user_id=1,
                raw_name=cname,
                raw_company=cname,
                raw_title="Staffing & IT Consulting",
                source_url=home_url,
                source_page_title=result["title"][:255],
                extraction_source=f"sheet_harvester:{sheet_name}",
                entity_type="COMPANY",
                processing_status="pending",
                metadata_json=json.dumps({
                    "website": f"https://{dom}",
                    "domain": dom,
                    "sheet_source": sheet_name,
                    "date_flagged": target.get("date_flagged", False),
                    "ats_type": result.get("ats_type"),
                    "careers_url": result.get("careers_url"),
                    "phones": all_phones,
                    "corp_emails": corp_emails[:3]
                })
            )
            db.add(comp_staging)
            result["staged_count"] += 1
            
            for c in result["contacts_found"]:
                person_staging = DiscoveryStaging(
                    batch_id=f"RESUME-{sheet_name.upper()}-{int(time.time())}",
                    discovery_id=f"DS-PERS-{uuid.uuid4().hex[:12]}",
                    device_id="harvest_engine_resume_node",
                    owner_user_id=1,
                    raw_name=c["name"],
                    raw_title=c.get("title", "Technical Recruiter"),
                    raw_company=cname,
                    raw_email=c.get("email"),
                    raw_phone=c.get("phone"),
                    source_url=home_url,
                    source_page_title=result["title"][:255],
                    extraction_source=f"sheet_harvester:{sheet_name}",
                    entity_type="PERSON",
                    processing_status="pending"
                )
                db.add(person_staging)
                result["staged_count"] += 1
                
            db.commit()
    except Exception:
        pass

    sheet_target_seeder.mark_domain_harvested(dom, sheet=sheet_name, details={
        "status": result["http_status"],
        "title": result["title"][:80],
        "ats": result["ats_type"],
        "staged": result["staged_count"]
    })

    return result

def resume_active_sheet_harvest(batch_size: int = 50):
    active_sheet = sheet_target_seeder.get_current_active_sheet()
    if not active_sheet:
        print("[HARVESTER] All sheets completed! Engine running on global targets.")
        return 0, 0

    print(f"\n=======================================================")
    print(f"RESUMING HARVEST FOR ACTIVE SHEET: '{active_sheet}'")
    print(f"=======================================================")

    targets = sheet_target_seeder.get_sheet_targets_list(active_sheet)
    pending = [t for t in targets if t["domain"] not in sheet_target_seeder._state["harvested_domains"]]
    pending_flagged = [t for t in pending if t.get("date_flagged")]
    pending_other = [t for t in pending if not t.get("date_flagged")]
    to_process = (pending_flagged + pending_other)[:batch_size]

    print(f"[{active_sheet}] Total: {len(targets)} | Pending: {len(pending)} | Harvesting batch: {len(to_process)}")

    staged_total = 0
    success_count = 0
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(harvest_single_company, t): t for t in to_process}
        for future in as_completed(futures):
            res = future.result()
            if res["dns_active"] and res["http_status"] not in [None, "ERR", "TIMEOUT/ERR"]:
                success_count += 1
                staged_total += res["staged_count"]
                ats_label = f"[{res['ats_type']}]" if res['ats_type'] else ""
                print(f"  + [{active_sheet}] {res['company_name'][:25]} ({res['domain']}) -> {res['http_status']} {ats_label}")

    print(f"\n[{active_sheet} Batch Summary] Processed: {len(to_process)} | Reachable: {success_count} | Records Staged: {staged_total}")
    return len(to_process), staged_total

if __name__ == "__main__":
    t0 = time.time()
    print("Resuming High-Throughput Sheet Harvester...")
    
    # Process batch 1
    p1, s1 = resume_active_sheet_harvest(batch_size=50)
    
    # Process batch 2 if active sheet still has pending or moved to next sheet
    p2, s2 = resume_active_sheet_harvest(batch_size=50)
    
    # Process batch via DiscoveryProcessor
    print("\n-------------------------------------------------------")
    print("Running DiscoveryProcessor to commit staged entities...")
    print("-------------------------------------------------------")
    with SessionLocal() as db:
        processor = DiscoveryProcessor(db)
        batch_stats = processor.process_pending_batch(limit=250)
        print(f"DiscoveryProcessor Results: {batch_stats}")

    stats = sheet_target_seeder.get_catalog_stats()
    print("\n=======================================================")
    print("UPDATED SHEET HARVESTER PROGRESS:")
    print(json.dumps(stats, indent=2))
    print(f"Run completed in {round(time.time() - t0, 1)}s")
    print("=======================================================")
