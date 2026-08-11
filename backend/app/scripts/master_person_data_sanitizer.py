import os
import sys
import time
from sqlalchemy import text
import logging

sys.path.append(r'C:\TalentOpsAI\backend')
from app.database import engine

logger = logging.getLogger("talentops")
logging.basicConfig(level=logging.INFO)

def run_sanitization():
    print("=== STARTING MASTER PERSON DATA SANITIZER ===")
    start_time = time.time()
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Clean Names
            print("1. Cleaning Names (Trimming & Title Casing)...")
            res_names = conn.execute(text("""
                UPDATE recruiters 
                SET recruiter_name = INITCAP(BTRIM(recruiter_name))
                WHERE recruiter_name != INITCAP(BTRIM(recruiter_name))
            """))
            print(f" -> Updated {res_names.rowcount} names.")
            
            # 2. Clean Job Titles
            print("2. Cleaning Job Titles (Trimming & Title Casing)...")
            res_titles = conn.execute(text("""
                UPDATE recruiters 
                SET title = INITCAP(BTRIM(title))
                WHERE title != INITCAP(BTRIM(title)) AND title IS NOT NULL
            """))
            print(f" -> Updated {res_titles.rowcount} titles.")
            
            # 3. Clean Emails (Lowercase & Trim)
            print("3. Cleaning Emails (Lowercase & Trim)...")
            res_emails = conn.execute(text("""
                UPDATE recruiters 
                SET email = LOWER(BTRIM(email))
                WHERE email != LOWER(BTRIM(email)) AND email IS NOT NULL
            """))
            print(f" -> Updated {res_emails.rowcount} emails.")
            
            # 4. Phone Standardization (Simple non-digit stripping, keeping +)
            print("4. Standardizing Phone Numbers (Removing whitespace, dashes, parens)...")
            res_phones = conn.execute(text("""
                UPDATE recruiters 
                SET phone = REGEXP_REPLACE(phone, '[^\d+]', '', 'g')
                WHERE phone != REGEXP_REPLACE(phone, '[^\d+]', '', 'g') AND phone IS NOT NULL
            """))
            print(f" -> Updated {res_phones.rowcount} phones.")

            res_phones2 = conn.execute(text("""
                UPDATE recruiters 
                SET phone2 = REGEXP_REPLACE(phone2, '[^\d+]', '', 'g')
                WHERE phone2 != REGEXP_REPLACE(phone2, '[^\d+]', '', 'g') AND phone2 IS NOT NULL
            """))
            print(f" -> Updated {res_phones2.rowcount} phone2s.")

    print(f"=== MASTER PERSON DATA SANITIZER COMPLETED IN {time.time() - start_time:.2f}s ===")

if __name__ == "__main__":
    run_sanitization()
