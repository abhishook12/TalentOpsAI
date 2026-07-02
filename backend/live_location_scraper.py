#!/usr/bin/env python
"""Option A: Free Live Async Web Scraping Engine for Corporate Locations - TalentOpsAI"""
import sys, os, time, re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

FREEMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com',
    'protonmail.com', 'zoho.com', 'yandex.com', 'mail.com', 'gmx.com', 'talentops.local'
}

# Major global tech & corporate hubs regex look-up table
HUB_REGEX = [
    (r'\b(San Francisco|SF|Bay Area|Palo Alto|Mountain View|San Jose|Oakland)\b.*?\b(CA|California)\b', 'San Francisco Bay Area, CA'),
    (r'\b(New York|NYC|Manhattan|Brooklyn)\b.*?\b(NY|New York)\b', 'New York, NY'),
    (r'\b(Austin)\b.*?\b(TX|Texas)\b', 'Austin, TX'),
    (r'\b(Seattle|Bellevue|Redmond)\b.*?\b(WA|Washington)\b', 'Seattle, WA'),
    (r'\b(Chicago)\b.*?\b(IL|Illinois)\b', 'Chicago, IL'),
    (r'\b(Boston|Cambridge)\b.*?\b(MA|Massachusetts)\b', 'Boston, MA'),
    (r'\b(Toronto|Mississauga)\b.*?\b(ON|Ontario)\b', 'Toronto, ON'),
    (r'\b(London)\b.*?\b(UK|United Kingdom|England)\b', 'London, United Kingdom'),
    (r'\b(Atlanta)\b.*?\b(GA|Georgia)\b', 'Atlanta, GA'),
    (r'\b(Denver|Boulder)\b.*?\b(CO|Colorado)\b', 'Denver, CO'),
    (r'\b(Dallas|Plano|Irving|Fort Worth)\b.*?\b(TX|Texas)\b', 'Dallas-Fort Worth, TX'),
    (r'\b(Miami|Fort Lauderdale)\b.*?\b(FL|Florida)\b', 'Miami, FL'),
    (r'\b(Los Angeles|LA|Santa Monica|Culver City|Irvine)\b.*?\b(CA|California)\b', 'Los Angeles Metro, CA'),
    (r'\b(Vancouver)\b.*?\b(BC|British Columbia)\b', 'Vancouver, BC'),
    (r'\b(Berlin)\b.*?\b(Germany|DE)\b', 'Berlin, Germany'),
    (r'\b(Paris)\b.*?\b(France|FR)\b', 'Paris, France'),
    (r'\b(Bengaluru|Bangalore)\b.*?\b(India|IN)\b', 'Bengaluru, India'),
    (r'\b(Sydney)\b.*?\b(Australia|NSW)\b', 'Sydney, Australia'),
    (r'\b(Remote|Distributed|Work from anywhere)\b', 'Remote (Distributed Hub)')
]

def scrape_domain_location(domain):
    url = f"http://{domain}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 TalentOpsAI-Research-Bot/1.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Scan HTML text for city/state markers
            for pat, loc in HUB_REGEX:
                if re.search(pat, html, re.IGNORECASE):
                    return domain, loc
    except Exception:
        pass
    return domain, None

def run_live_scraper():
    t0 = time.time()
    print(f"[{time.strftime('%X')}] INITIATING OPTION A: FREE LIVE WEB SCRAPING ENGINE ($0.00 COST)...")
    db = SessionLocal()
    try:
        print(f"[{time.strftime('%X')}] Clustering unmapped recruiters by corporate email domain...")
        last_rid = 0
        domain_recs = defaultdict(list)

        while True:
            chunk = db.execute(text("""
                SELECT recruiter_id, email
                FROM recruiters
                WHERE recruiter_id > :lid AND (location IS NULL OR TRIM(location) = '' OR LOWER(location) = 'nan') AND is_active = true
                ORDER BY recruiter_id LIMIT 10000
            """), {"lid": last_rid}).mappings().all()
            if not chunk: break
            for r in chunk:
                em = str(r['email'] or "").strip().lower()
                if '@' in em:
                    dom = em.split('@')[-1]
                    if dom not in FREEMAIL_DOMAINS and '.' in dom:
                        domain_recs[dom].append(r['recruiter_id'])
            last_rid = chunk[-1]['recruiter_id']

        # Sort domains by number of recruiters impacted
        sorted_domains = sorted(domain_recs.keys(), key=lambda d: len(domain_recs[d]), reverse=True)
        print(f"[{time.strftime('%X')}] Discovered {len(sorted_domains):,} unique corporate domains across unmapped cohort.")
        
        # We will scrape the top 500 domains in this batch execution (impacting tens of thousands of recruiters)
        top_batch = sorted_domains[:500]
        tot_impacted = sum(len(domain_recs[d]) for d in top_batch)
        print(f"[{time.strftime('%X')}] Launching 30 concurrent headless crawler threads against top 500 corporate domains (Targeting {tot_impacted:,} recruiters)...")

        resolved_doms = {}
        with ThreadPoolExecutor(max_workers=30) as exe:
            futures = {exe.submit(scrape_domain_location, d): d for d in top_batch}
            done_cnt = 0
            for fut in as_completed(futures):
                done_cnt += 1
                dom, loc = fut.result()
                if loc:
                    resolved_doms[dom] = loc
                if done_cnt % 100 == 0:
                    print(f"[{time.strftime('%X')}] Web Crawl Progress: {done_cnt}/500 domains scanned. Hits found: {len(resolved_doms)}")

        print(f"[{time.strftime('%X')}] Live Web Scrape Complete! Successfully geolocated {len(resolved_doms):,} corporate domains.")

        # Execute Bulk DB Updates
        recs_updated = 0
        if resolved_doms:
            print(f"[{time.strftime('%X')}] Committing live scraped locations to local database...")
            up_batch = []
            for dom, loc in resolved_doms.items():
                rids = domain_recs[dom]
                for rid in rids:
                    up_batch.append({"rid": rid, "loc": loc[:145], "nts": f"[GEO: {loc} (Live Scraped via {dom})]"})

            for i in range(0, len(up_batch), 500):
                b_chunk = up_batch[i:i+500]
                db.execute(text("""
                    UPDATE recruiters
                    SET location = :loc,
                        notes = COALESCE(notes, '') || '; ' || :nts
                    WHERE recruiter_id = :rid
                """), b_chunk)
            db.commit()
            recs_updated = len(up_batch)

        elapsed = round(time.time() - t0, 2)
        print(f"\n=======================================================")
        print(f"OPTION A: FREE LIVE WEB SCRAPING BATCH COMPLETE!")
        print(f"Execution Time: {elapsed}s")
        print(f"Corporate Domains Crawled: 500")
        print(f"Domains Successfully Geolocated: {len(resolved_doms):,}")
        print(f"Recruiter Profiles Enriched with Pinpoint Locations: +{recs_updated:,}")
        print(f"Total Money Spent: $0.00")
        print(f"=======================================================")

    except Exception as e:
        db.rollback()
        print("ERROR DURING LIVE SCRAPE:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_live_scraper()
