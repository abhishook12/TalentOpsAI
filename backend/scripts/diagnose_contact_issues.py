import os
import psycopg
from dotenv import load_dotenv

def run_diagnostics():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    c = conn.cursor()

    print("=== DEEP CONTACT REFINEMENT DIAGNOSTICS ===")

    # 1. Names that are all lowercase or ALL CAPS
    c.execute("SELECT COUNT(*) FROM recruiters WHERE recruiter_name = LOWER(recruiter_name) AND recruiter_name ~ '[a-z]'")
    lower_names = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM recruiters WHERE recruiter_name = UPPER(recruiter_name) AND recruiter_name ~ '[A-Z]'")
    upper_names = c.fetchone()[0]
    print(f"Names requiring Title Casing (all lower or ALL CAPS): {lower_names + upper_names:,} (Lower: {lower_names:,}, Upper: {upper_names:,})")
    
    # 2. Names containing commas (often indicates 'Name, Title')
    c.execute("SELECT COUNT(*) FROM recruiters WHERE POSITION(',' IN recruiter_name) > 0")
    comma_names = c.fetchone()[0]
    print(f"Names containing commas (e.g., 'Name, Title'): {comma_names:,}")
    if comma_names > 0:
        c.execute("SELECT recruiter_name FROM recruiters WHERE POSITION(',' IN recruiter_name) > 0 LIMIT 5")
        print("  Examples:", [row[0] for row in c.fetchall()])

    # 3. Names containing '@' (emails in name field)
    c.execute("SELECT COUNT(*) FROM recruiters WHERE POSITION('@' IN recruiter_name) > 0")
    at_names = c.fetchone()[0]
    print(f"Names containing '@' (likely emails): {at_names:,}")
    if at_names > 0:
        c.execute("SELECT recruiter_name FROM recruiters WHERE POSITION('@' IN recruiter_name) > 0 LIMIT 5")
        print("  Examples:", [row[0] for row in c.fetchall()])

    # 4. Names containing numbers
    c.execute("SELECT COUNT(*) FROM recruiters WHERE recruiter_name ~ '[0-9]'")
    num_names = c.fetchone()[0]
    print(f"Names containing numbers: {num_names:,}")
    if num_names > 0:
        c.execute("SELECT recruiter_name FROM recruiters WHERE recruiter_name ~ '[0-9]' LIMIT 5")
        print("  Examples:", [row[0] for row in c.fetchall()])

    # 5. Garbage names/emails ('n/a', 'none', 'null')
    c.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(TRIM(recruiter_name)) IN ('n/a', 'none', 'null', 'nan')")
    garbage_names = c.fetchone()[0]
    print(f"Garbage Names ('n/a', 'none', 'null'): {garbage_names:,}")

    c.execute("SELECT COUNT(*) FROM recruiters WHERE LOWER(TRIM(email)) IN ('n/a', 'none', 'null', 'nan')")
    garbage_emails = c.fetchone()[0]
    print(f"Garbage Emails ('n/a', 'none', 'null'): {garbage_emails:,}")

    # 6. Leading/Trailing spaces
    c.execute("SELECT COUNT(*) FROM recruiters WHERE recruiter_name != TRIM(recruiter_name)")
    space_names = c.fetchone()[0]
    print(f"Names with leading/trailing spaces: {space_names:,}")

    # 7. Unconventional characters in names (excluding letters, spaces, hyphens, periods, apostrophes, commas)
    c.execute("SELECT COUNT(*) FROM recruiters WHERE recruiter_name ~ '[^a-zA-Z\\s\\-\\.\\',]'")
    special_names = c.fetchone()[0]
    print(f"Names with special/unconventional characters: {special_names:,}")
    if special_names > 0:
        c.execute("SELECT recruiter_name FROM recruiters WHERE recruiter_name ~ '[^a-zA-Z\\s\\-\\.\\',]' LIMIT 5")
        print("  Examples:", [row[0] for row in c.fetchall()])
        
    print("=============================================")

if __name__ == '__main__':
    run_diagnostics()
