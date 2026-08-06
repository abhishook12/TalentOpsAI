import psycopg
import sys

def analyze():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    report = []
    
    with psycopg.connect(remote_url, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 0;")
            report.append("=== TALENTOPS DEEP MASS DATABASE ANALYSIS ===")
            
            # 1. Duplicate Recruiters (same email)
            cur.execute("""
                SELECT email, COUNT(*) 
                FROM recruiters 
                WHERE email IS NOT NULL AND email != '' 
                GROUP BY email 
                HAVING COUNT(*) > 1
            """)
            dupe_emails = cur.fetchall()
            report.append(f"\n1. Duplicate Recruiters by Email: {len(dupe_emails)} emails are shared by multiple recruiters.")
            
            # 2. Invalid Phone Numbers (letters in them, or weird lengths)
            cur.execute("""
                SELECT COUNT(*) 
                FROM recruiters 
                WHERE phone IS NOT NULL AND phone != ''
                  AND (phone ~ '[a-zA-Z]' OR LENGTH(REGEXP_REPLACE(phone, '[^0-9]', '', 'g')) < 7)
            """)
            invalid_phones = cur.fetchone()[0]
            report.append(f"2. Invalid Phone Numbers (letters or too short): {invalid_phones}")
            
            # 3. Bad Names (Numbers in names, extremely short names)
            cur.execute("""
                SELECT COUNT(*)
                FROM recruiters
                WHERE recruiter_name ~ '[0-9]' OR LENGTH(TRIM(recruiter_name)) < 2 OR recruiter_name ILIKE '%test%' OR recruiter_name ILIKE '%unknown%'
            """)
            bad_names = cur.fetchone()[0]
            report.append(f"3. Suspicious Recruiter Names (numbers, 'test', 'unknown', or very short): {bad_names}")
            
            # 4. Companies with 0 Recruiters (Orphaned Companies)
            cur.execute("""
                SELECT COUNT(*)
                FROM companies c
                LEFT JOIN recruiters r ON c.company_id = r.company_id
                WHERE r.recruiter_id IS NULL
            """)
            orphaned_companies = cur.fetchone()[0]
            report.append(f"4. Orphaned Companies (0 recruiters associated): {orphaned_companies}")
            
            # 5. Placeholder / Dummy Values in Location
            cur.execute("""
                SELECT COUNT(*)
                FROM recruiters
                WHERE location ILIKE 'none' OR location ILIKE 'n/a' OR location ILIKE 'null' OR location ILIKE 'test%'
            """)
            dummy_locations = cur.fetchone()[0]
            report.append(f"5. Dummy/Placeholder Locations ('none', 'n/a', 'null', 'test'): {dummy_locations}")
            
            # 6. Bad URLs in Companies
            cur.execute("""
                SELECT COUNT(*)
                FROM companies
                WHERE website IS NOT NULL AND website != ''
                  AND website NOT ILIKE 'http%' AND website NOT LIKE 'www.%' AND website NOT LIKE '%.%'
            """)
            bad_urls = cur.fetchone()[0]
            report.append(f"6. Malformed Company Websites: {bad_urls}")

            # 7. Placeholder Titles
            cur.execute("""
                SELECT COUNT(*)
                FROM recruiters
                WHERE title IS NOT NULL AND title != ''
                  AND (title ILIKE 'none' OR title ILIKE 'n/a' OR title ILIKE 'null' OR title ILIKE 'unknown')
            """)
            dummy_titles = cur.fetchone()[0]
            report.append(f"7. Dummy/Placeholder Job Titles ('none', 'n/a', 'null', 'unknown'): {dummy_titles}")

            # 8. Mismatched Company Names vs Domains (Heuristic: company name doesn't appear in domain at all)
            # This is slow, so we do a quick substring check
            cur.execute("""
                SELECT COUNT(*)
                FROM companies
                WHERE company_name IS NOT NULL AND email_pattern IS NOT NULL
                  AND LENGTH(company_name) > 3
                  AND STRPOS(LOWER(email_pattern), REGEXP_REPLACE(LOWER(SPLIT_PART(company_name, ' ', 1)), '[^a-z]', '', 'g')) = 0
            """)
            mismatched_names_domains = cur.fetchone()[0]
            report.append(f"8. Companies where Name significantly mismatches Email Pattern (Heuristic): {mismatched_names_domains}")

            # 9. Duplicate Companies by EXACT Company Name
            cur.execute("""
                SELECT company_name, COUNT(*)
                FROM companies
                WHERE company_name IS NOT NULL AND company_name != ''
                GROUP BY company_name
                HAVING COUNT(*) > 1
            """)
            dupe_company_names = cur.fetchall()
            report.append(f"9. Duplicate Companies by Exact Name: {len(dupe_company_names)} names are shared by multiple companies.")

            
    for line in report:
        print(line)

if __name__ == "__main__":
    analyze()
