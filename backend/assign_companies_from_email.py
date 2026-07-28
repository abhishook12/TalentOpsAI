import sys
import os
import time
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal

def assign_companies():
    start_time = time.time()
    print("STARTING COMPANY ASSIGNMENT VIA EMAIL DOMAINS...")
    db = SessionLocal()
    
    try:
        # First, we need to extract domains from companies that have a valid domain
        print("Mapping company IDs to their dominant email domain...")
        domain_res = db.execute(text("""
            SELECT company_id, 
                   SUBSTR(email, INSTR(email, '@') + 1) as domain,
                   COUNT(*) as cnt
            FROM recruiters
            WHERE email LIKE '%@%'
              AND company_id IS NOT NULL
              AND SUBSTR(email, INSTR(email, '@') + 1) NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com')
            GROUP BY company_id, domain
            HAVING COUNT(*) > 1
        """)).mappings().all()

        domain_to_company = {}
        for row in domain_res:
            d = row['domain'].lower()
            if d not in domain_to_company:
                domain_to_company[d] = row['company_id']
            else:
                domain_to_company[d] = None

        safe_domains = {k: v for k, v in domain_to_company.items() if v is not None}
        print(f"Built safe mapping for {len(safe_domains)} unique company domains.")

        print("Assigning companies to orphaned recruiters...")
        
        orphans = db.execute(text("""
            SELECT recruiter_id, email 
            FROM recruiters 
            WHERE company_id IS NULL AND email LIKE '%@%'
        """)).mappings().all()

        updated = 0
        for orphan in orphans:
            email = orphan['email']
            domain = email.split('@')[-1].lower()
            if domain in safe_domains:
                db.execute(text("UPDATE recruiters SET company_id = :cid WHERE recruiter_id = :rid"),
                           {"cid": safe_domains[domain], "rid": orphan['recruiter_id']})
                updated += 1
                
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Successfully assigned {updated} orphaned recruiters to a company in {elapsed}s.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during assignment: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    assign_companies()
