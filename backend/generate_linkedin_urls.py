import sys
import os
import time
import re
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal

def slugify(text_val):
    if not text_val: return ""
    text_val = text_val.lower()
    text_val = re.sub(r'[^a-z0-9\s-]', '', text_val)
    return re.sub(r'[\s]+', '-', text_val).strip('-')

def generate_linkedin_urls():
    start_time = time.time()
    print("STARTING LINKEDIN URL GENERATION...")
    db = SessionLocal()
    
    try:
        missing = db.execute(text("""
            SELECT r.recruiter_id, r.recruiter_name, c.company_name
            FROM recruiters r
            LEFT JOIN companies c ON r.company_id = c.company_id
            WHERE (r.linkedin IS NULL OR r.linkedin = '')
              AND r.recruiter_name IS NOT NULL
        """)).mappings().all()

        updated = 0
        
        for row in missing:
            name = row['recruiter_name'].strip()
            company = row['company_name']
            
            if ' ' not in name:
                continue
                
            name_slug = slugify(name)
            if not name_slug:
                continue
                
            url = f"https://www.linkedin.com/in/{name_slug}"
            
            if company:
                company_slug = slugify(company)
                if company_slug:
                    url += f"-{company_slug}"
                    
            db.execute(text("UPDATE recruiters SET linkedin = :url WHERE recruiter_id = :rid"),
                       {"url": url, "rid": row['recruiter_id']})
            updated += 1
            
            if updated % 5000 == 0:
                db.commit()
                
        db.commit()
        elapsed = round(time.time() - start_time, 2)
        print(f"Generated and backfilled {updated} probabilistic LinkedIn URLs in {elapsed}s.")
        
    except Exception as e:
        db.rollback()
        print(f"Error generating LinkedIn URLs: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_linkedin_urls()
