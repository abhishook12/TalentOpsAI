import sys
import os
import io
import csv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.database import SessionLocal

data = """Name	Position	Email	Company
Leonard Bethea	Chief Executive Officer	leonard@tmhsolutions.com	TMH SOLUTIONS LLC
Lucinda Brooks	Project Manager 4	lucinda@tmhsolutions.com	TMH SOLUTIONS LLC
Tammy Meek. PMP, MPM, SCPM, ASEP	Project Manager	tammy@tmhsolutions.com	TMH SOLUTIONS LLC
Kyle Polk	CEO/Owner - Decisive Systems Technologies, LLC	kyle@tmhsolutions.com	TMH SOLUTIONS LLC
Theresa Harris	TMH Strategies	theresa@tmhsolutions.com	TMH SOLUTIONS LLC
Lorna Lowery PMP, MS, MBA	Consultant Project Manager	lorna@tmhsolutions.com	TMH SOLUTIONS LLC
Jo Ellen Campbell	Change Management	joellen@tmhsolutions.com	TMH SOLUTIONS LLC"""

def run():
    db = SessionLocal()
    try:
        # Get an admin user ID using raw SQL
        res = db.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
        user_id = res[0] if res else None

        reader = csv.DictReader(io.StringIO(data), delimiter='\t')
        
        inserted_count = 0
        updated_count = 0
        
        for row in reader:
            name = row['Name'].strip()
            title = row['Position'].strip()
            email = row['Email'].strip().lower()
            company_name = row['Company'].strip()
            
            if not email:
                continue

            # Upsert Company
            comp_res = db.execute(text("SELECT company_id FROM companies WHERE company_name = :cname"), {"cname": company_name}).fetchone()
            if not comp_res:
                db.execute(
                    text("INSERT INTO companies (company_name, normalized_company_name, user_id, data_source) VALUES (:cname, :nname, :uid, 'manual_upload')"),
                    {"cname": company_name, "nname": company_name.lower().replace(" ", ""), "uid": user_id}
                )
                db.commit()
                comp_res = db.execute(text("SELECT company_id FROM companies WHERE company_name = :cname"), {"cname": company_name}).fetchone()
            
            company_id = comp_res[0] if comp_res else None

            # Upsert Recruiter
            rec_res = db.execute(text("SELECT recruiter_id FROM recruiters WHERE email = :email"), {"email": email}).fetchone()
            if not rec_res:
                db.execute(
                    text("INSERT INTO recruiters (recruiter_name, email, title, company_id, user_id, data_source) VALUES (:name, :email, :title, :cid, :uid, 'manual_upload')"),
                    {"name": name, "email": email, "title": title, "cid": company_id, "uid": user_id}
                )
                inserted_count += 1
            else:
                db.execute(
                    text("UPDATE recruiters SET recruiter_name = :name, title = :title, company_id = :cid WHERE email = :email"),
                    {"name": name, "title": title, "cid": company_id, "email": email}
                )
                updated_count += 1
                
        db.commit()
        print(f"Successfully processed {inserted_count + updated_count} records.")
        print(f"- Inserted: {inserted_count}")
        print(f"- Updated: {updated_count}")

    except Exception as e:
        print(f"Error during upload: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run()
