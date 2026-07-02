import sys
import os
import time
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.database import SessionLocal

def run_aliasing_engine():
    print("=== STARTING UNIVERSAL DOMAIN ALIASING ENGINE ===")
    t0 = time.time()
    db = SessionLocal()

    # Manual overrides for critical missing links
    MANUAL_LINKS = [
        {"domain": "sisinc.com", "canonical": "Systems Integration Solutions"}
    ]

    for link in MANUAL_LINKS:
        domain = link["domain"]
        canonical_name = link["canonical"]
        print(f"Processing manual link: {domain} -> {canonical_name}")

        # Find canonical company
        canonical = db.execute(text("SELECT company_id, company_name FROM companies WHERE company_name ILIKE :c_name LIMIT 1"), {"c_name": canonical_name}).mappings().first()
        if not canonical:
            print(f" Canonical company '{canonical_name}' not found. Creating it.")
            db.execute(text("""
                INSERT INTO companies (company_name, normalized_company_name, email_pattern, is_active, data_source)
                VALUES (:c, :nc, :ep, true, 'alias_engine')
            """), {"c": canonical_name, "nc": canonical_name.lower().replace(" ", ""), "ep": domain})
            db.commit()
            canonical = db.execute(text("SELECT company_id, company_name FROM companies WHERE company_name ILIKE :c_name LIMIT 1"), {"c_name": canonical_name}).mappings().first()
        
        canon_id = canonical['company_id']

        # Find all other companies that have this domain, or are literally named the domain prefix
        prefix = domain.split('.')[0]
        aliases = db.execute(text("""
            SELECT company_id, company_name FROM companies 
            WHERE (email_pattern ILIKE :domain OR website ILIKE :w_domain OR company_name ILIKE :prefix)
            AND company_id != :canon_id
        """), {"domain": f"%{domain}%", "w_domain": f"%{domain}%", "prefix": prefix, "canon_id": canon_id}).mappings().all()

        for alias in aliases:
            a_id = alias['company_id']
            a_name = alias['company_name']
            print(f" -> Found alias: {a_name} (ID: {a_id}). Merging to Canonical ID: {canon_id}")

            # Insert into company_aliases
            db.execute(text("""
                INSERT INTO company_aliases (canonical_company_id, alias_name, alias_type)
                VALUES (:cid, :an, 'domain_alias')
            """), {"cid": canon_id, "an": a_name})

            # Re-parent recruiters
            db.execute(text("""
                UPDATE recruiters SET company_id = :canon_id WHERE company_id = :a_id
            """), {"canon_id": canon_id, "a_id": a_id})

            # Deactivate the alias company
            db.execute(text("""
                UPDATE companies SET is_active = false WHERE company_id = :a_id
            """), {"a_id": a_id})

        # Ensure canonical has the email pattern
        db.execute(text("UPDATE companies SET email_pattern = :domain, is_active = true WHERE company_id = :canon_id"), {"domain": domain, "canon_id": canon_id})
        
        # Also blindly reparent any recruiters with this email domain directly, just in case they have no company
        res = db.execute(text("UPDATE recruiters SET company_id = :canon_id WHERE email ILIKE :em AND (company_id != :canon_id OR company_id IS NULL)"), {"canon_id": canon_id, "em": f"%@{domain}"})
        print(f" -> Directly reparented {res.rowcount} orphaned recruiters matching @{domain}")

        db.commit()

    print(f"Done in {round(time.time() - t0, 2)}s.")

if __name__ == "__main__":
    run_aliasing_engine()
