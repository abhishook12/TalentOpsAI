import os
import psycopg
from dotenv import load_dotenv

def run_fast_engine():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== ULTRA-FAST CONTACT REFINEMENT ENGINE (PURE SQL) ===")
    print("=======================================================================")

    # 1. Clean Names that are ALL CAPS or all lower case (Title Casing)
    print("\\n[Phase 1] Normalizing Name Capitalization (Title Case)...")
    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = INITCAP(recruiter_name)
        WHERE (recruiter_name = LOWER(recruiter_name) AND recruiter_name ~ '[a-z]')
           OR (recruiter_name = UPPER(recruiter_name) AND recruiter_name ~ '[A-Z]')
    """)
    print(f" -> Converted {cursor.rowcount:,} names to proper Title Case.")
    conn.commit()

    # 2. Strip trailing digits from obvious internal usernames (e.g., Abrown2 -> Abrown)
    print("\\n[Phase 2] Stripping trailing username digits...")
    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = REGEXP_REPLACE(recruiter_name, '[0-9]+$', '')
        WHERE recruiter_name ~ '^[A-Za-z]+[0-9]+$'
    """)
    print(f" -> Stripped trailing digits from {cursor.rowcount:,} usernames masquerading as names.")
    conn.commit()

    # 3. Detect Job Titles / Company names masquerading as recruiter names
    print("\\n[Phase 3] Moving Job Titles and Company Names from 'Name' to 'Notes'...")
    cursor.execute("""
        UPDATE recruiters 
        SET notes = COALESCE(notes || '\\n', '') || '[Original Name Field]: ' || recruiter_name,
            recruiter_name = 'Unknown'
        WHERE LOWER(recruiter_name) SIMILAR TO '%(specialist|administrator|manager|director|vp|recruiter|talent|acquisition|sourcer|consultant|president|officer|software|technologies|llc|inc|corp|solutions|group)%'
          AND recruiter_name != 'Unknown'
    """)
    print(f" -> Moved {cursor.rowcount:,} titles/companies to 'notes' (and reset Name to 'Unknown').")
    conn.commit()

    # 4. Strip stray commas and multiple spaces
    print("\\n[Phase 4] Stripping stray commas and whitespace...")
    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = REGEXP_REPLACE(REPLACE(recruiter_name, ',', ' '), '\\s+', ' ', 'g')
        WHERE POSITION(',' IN recruiter_name) > 0 OR recruiter_name ~ '\\s{2,}'
    """)
    print(f" -> Cleaned stray commas/spaces from {cursor.rowcount:,} names.")
    
    # 5. Final Trim
    cursor.execute("UPDATE recruiters SET recruiter_name = TRIM(recruiter_name) WHERE recruiter_name != TRIM(recruiter_name)")
    print(f" -> Final whitespace trimmed on {cursor.rowcount:,} names.")
    conn.commit()
    
    print("\n[OK] All Fast Contact Refinement completed successfully!")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    run_fast_engine()
