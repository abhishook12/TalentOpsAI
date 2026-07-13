import os
import sys
import json
import time
import requests
import argparse
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.database import SessionLocal
from app.models.models import Recruiter, Company
from app.utils.phone_normalizer import format_us_phone

OMNIROUTE_URL = "http://localhost:20128/v1/chat/completions"
# Using OmniRoute's auto model configuration or a specific fast/free tier model
MODEL_NAME = "auto" 

DB_SIZE_LIMIT_MB = 430

def get_db_size_mb(db):
    res = db.execute(text("SELECT pg_database_size(current_database());")).fetchone()
    return res[0] / (1024 * 1024)

def fetch_batch(db, limit=500):
    return db.execute(text("""
        SELECT r.recruiter_id, r.recruiter_name, c.company_name, r.state
        FROM recruiters r
        JOIN companies c ON r.company_id = c.company_id
        WHERE r.is_active = true 
          AND (r.linkedin IS NULL OR r.linkedin = '' OR r.phone IS NULL OR r.phone = '')
          AND (r.last_scan_at IS NULL OR r.last_scan_at < now() - interval '1 day')
        LIMIT :lim
    """), {"lim": limit}).fetchall()

def enrich_profile(recruiter_id, name, company_name, state):
    prompt = f"""
    Find or intelligently infer the professional public LinkedIn URL and a standard US corporate phone number for the following recruiter. 
    If you cannot find or be reasonably certain about the data, leave the field blank. DO NOT hallucinate fake phone numbers.
    
    Target:
    Name: {name}
    Company: {company_name}
    State: {state}

    Return ONLY a raw JSON object, no markdown wrappers, no explanations.
    Format: {{"linkedin": "https://linkedin.com/in/...", "phone": "+1 (xxx) xxx-xxxx"}}
    """

    try:
        response = requests.post(OMNIROUTE_URL, json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "stream": True
        }, headers={"Content-Type": "application/json"}, timeout=30)
        
        if response.status_code == 200:
            full_content = ""
            for line in response.text.split("\n"):
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        if 'content' in delta:
                            full_content += delta['content']
                    except Exception:
                        pass
                        
            content = full_content.strip()
            print(f"[DEBUG] Assembled response for ID {recruiter_id}: {content}")
            
            if not content:
                return recruiter_id, None, None
                
            # Clean possible markdown formatting from LLM response
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
                
            try:
                data = json.loads(content)
                return recruiter_id, data.get('linkedin'), data.get('phone')
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON parse error for ID {recruiter_id}: {e} -> {content}")
                return recruiter_id, None, None
        else:
            print(f"[DEBUG] Status code {response.status_code} for ID {recruiter_id}")
            return recruiter_id, None, None
    except Exception as e:
        print(f"[DEBUG] Unexpected Error for ID {recruiter_id}: {e}")
        return recruiter_id, None, None

def main(dry_run=False):
    print("==================================================")
    print("STARTING OMNIROUTE ENRICHMENT DAEMON")
    print(f"Connecting to OmniRoute at {OMNIROUTE_URL}")
    print("==================================================")
    
    db = SessionLocal()
    
    current_size = get_db_size_mb(db)
    print(f"[PRE-FLIGHT] Current DB Size: {current_size:.2f} MB")
    
    if current_size >= DB_SIZE_LIMIT_MB:
        print("CRITICAL: Database size exceeds 430 MB! Triggering Emergency Halt.")
        sys.exit(1)

    # Loop continuously to process all records in batches
    while True:
        batch = fetch_batch(db, limit=10 if dry_run else 500)
        
        if not batch:
            print("No missing records found or all remaining records have been scanned recently. Enrichment complete!")
            break

        print(f"Loaded batch of {len(batch)} profiles for enrichment.")
        
        success_count = 0
        updates = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(enrich_profile, r.recruiter_id, r.recruiter_name, r.company_name, r.state): r for r in batch}
            
            for future in as_completed(futures):
                r_id, linkedin, phone = future.result()
                
                updates.append({
                    "rid": r_id,
                    "lnk": linkedin if linkedin else None,
                    "ph": format_us_phone(phone) if phone and format_us_phone(phone) != "Invalid" else None
                })
                if linkedin or phone:
                    success_count += 1
                        
                if dry_run:
                    print(f"DRY RUN: [ID:{r_id}] -> LinkedIn: {linkedin}, Phone: {phone}")

        print(f"\n[ENRICHMENT COMPLETE] Generated valid data for {success_count} / {len(batch)} records in this batch.")
        
        if not dry_run and updates:
            print("Committing updates to database (and marking as scanned)...")
            # Only update linkedin or phone if the new value is NOT None. 
            # But we must update last_scan_at so we don't fetch them again.
            db.execute(
                text("""
                    UPDATE recruiters 
                    SET 
                        linkedin = COALESCE(:lnk, linkedin), 
                        phone = COALESCE(:ph, phone),
                        last_scan_at = now()
                    WHERE recruiter_id = :rid
                """),
                updates
            )
            db.commit()
            
            post_size = get_db_size_mb(db)
            print(f"[POST-FLIGHT] DB Size: {post_size:.2f} MB")
            
            if post_size >= DB_SIZE_LIMIT_MB:
                print("WARNING: Database is nearing 430 MB threshold. Halting further execution.")
                sys.exit(1)
                
        if dry_run:
            break
        
        time.sleep(2) # Give the DB a slight breather
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode for testing.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
