import sys
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.database import SessionLocal
from app.models.models import Company
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("full_throttle")

def clean_domain(url):
    if not url: return None
    url = url.lower().strip()
    if not url.startswith('http'):
        url = 'http://' + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        domain = re.sub(r'^www\.', '', domain)
        return domain
    except:
        return None

def process_company(company_id, company_name):
    attempts = 0
    while attempts < 3:
        try:
            query = f'"{company_name}" official company website'
            results = DDGS().text(query, max_results=3)
            
            website = None
            if results:
                website = next((r.get("href") for r in results if "linkedin" not in r.get("href", "").lower()), None)
                
            email_pattern = clean_domain(website) if website else None
            if website: website = website[:255]
            if email_pattern: email_pattern = email_pattern[:255]
            return (company_id, website, email_pattern, None)

        except Exception as e:
            err_msg = str(e).lower()
            if "rate limit" in err_msg or "429" in err_msg or "too many requests" in err_msg:
                time.sleep(5)
            else:
                time.sleep(2)
        attempts += 1
    return (company_id, None, None, "MAX_ATTEMPTS")

def main():
    db = SessionLocal()
    companies = db.query(Company).filter(
        (Company.website == None) | (Company.website == ''),
        (Company.email_pattern == None) | (Company.email_pattern == '')
    ).all()

    total_to_process = len(companies)
    logger.info(f"Starting free DDGS enrichment for {total_to_process} companies.")

    if total_to_process == 0:
        logger.info("No companies need enrichment.")
        return

    processed = 0
    updated = 0
    batch_size = 20
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_company, c.company_id, c.company_name): c for c in companies}
        
        db.close()
        db = SessionLocal()
        
        for future in as_completed(futures):
            c_id, web, emp, err = future.result()
            processed += 1
            
            if web or emp:
                try:
                    db_comp = db.query(Company).get(c_id)
                    if web: db_comp.website = web
                    if emp: db_comp.email_pattern = emp
                    updated += 1
                except Exception as e:
                    db.rollback()
                    db.close()
                    db = SessionLocal()
                    db_comp = db.query(Company).get(c_id)
                    if web: db_comp.website = web
                    if emp: db_comp.email_pattern = emp
                    updated += 1
                    
            if processed % batch_size == 0:
                try:
                    db.commit()
                    logger.info(f"Processed {processed}/{total_to_process} | Updated {updated} companies so far...")
                except Exception as e:
                    logger.warning(f"Failed to commit batch: {e}")
                    db.rollback()
                    
    try:
        db.commit()
    except:
        pass
        
    logger.info(f"Finished. Total processed: {processed}, Successfully enriched: {updated}")

if __name__ == "__main__":
    main()
