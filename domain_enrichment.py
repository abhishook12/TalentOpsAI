import sqlite3
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DB_PATH = r"C:\TalentOpsAI\backend\dev.db"

FREE_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
    'aol.com', 'icloud.com', 'msn.com', 'live.com', 'ymail.com'
}

def get_or_create_company(cursor, company_name):
    # Check if exists
    cursor.execute("SELECT company_id FROM companies WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
        
    # Insert new company
    cursor.execute("""
        INSERT INTO companies (company_name, normalized_company_name, data_source, is_active, trust_score)
        VALUES (?, ?, 'domain_algorithmic_resolution', 1, 100)
    """, (company_name, company_name.lower().replace(" ", "")))
    
    return cursor.lastrowid

def extract_company_from_domain(email):
    try:
        domain = email.split('@')[1].lower().strip()
        if domain in FREE_DOMAINS:
            return "Independent"
            
        # Strip TLD and format
        raw_name = domain.rsplit('.', 1)[0] # removes .com, .net etc
        
        # Format name nicely (e.g. teksystems -> Teksystems)
        # Handle some edge cases if needed, but Title Case works 95% of time
        formatted_name = raw_name.replace('-', ' ').title()
        return formatted_name
    except:
        return "Unknown"

def run_enrichment():
    logging.info("--- STARTING LOCAL DOMAIN ENRICHMENT ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We only want to process records missing a company
    cursor.execute("SELECT recruiter_id, email FROM recruiters WHERE company_id IS NULL AND email IS NOT NULL")
    records = cursor.fetchall()
    logging.info(f"Found {len(records)} recruiters needing company resolution.")
    
    if not records:
        logging.info("No records to enrich.")
        return
        
    # Build an in-memory cache of companies to avoid millions of SELECTs
    cursor.execute("SELECT company_name, company_id FROM companies")
    company_cache = {row[0]: row[1] for row in cursor.fetchall()}
    
    updates = []
    start_time = time.time()
    
    for r_id, email in records:
        company_name = extract_company_from_domain(email)
        
        if company_name not in company_cache:
            # Need to insert into DB to get real ID
            new_id = get_or_create_company(cursor, company_name)
            company_cache[company_name] = new_id
            
        updates.append((company_cache[company_name], r_id))
        
    logging.info(f"Resolved {len(updates)} records. Writing to database...")
    
    # Bulk update
    cursor.executemany("UPDATE recruiters SET company_id = ? WHERE recruiter_id = ?", updates)
    conn.commit()
    
    logging.info("--- ENRICHMENT COMPLETE ---")
    logging.info(f"Successfully populated Companies for {len(updates)} recruiters.")
    logging.info(f"Created/Verified {len(company_cache)} unique companies.")
    logging.info(f"Time taken: {time.time() - start_time:.2f} seconds")
    
    conn.close()

if __name__ == "__main__":
    run_enrichment()
