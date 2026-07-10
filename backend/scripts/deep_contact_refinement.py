import os
import re
import psycopg
from dotenv import load_dotenv

def run_deep_refinement():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    conn = psycopg.connect(db_url)
    cursor = conn.cursor()

    print("=======================================================================")
    print("=== DEEP CONTACT REFINEMENT ENGINE (NAMES & STRUCTURAL ANOMALIES) ===")
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

    # 2. Strip trailing digits from obvious internal usernames (e.g., Abrown2 -> Abrown)
    print("\\n[Phase 2] Stripping trailing username digits...")
    cursor.execute("""
        UPDATE recruiters
        SET recruiter_name = REGEXP_REPLACE(recruiter_name, '[0-9]+$', '')
        WHERE recruiter_name ~ '^[A-Za-z]+[0-9]+$'
    """)
    print(f" -> Stripped trailing digits from {cursor.rowcount:,} usernames masquerading as names.")

    # 3. Detect Job Titles / Company names masquerading as recruiter names
    print("\\n[Phase 3] Moving Job Titles and Company Names from 'Name' to 'Notes'...")
    # Words that indicate a title or company
    invalid_keywords = [
        'specialist', 'administrator', 'manager', 'director', 'vp', 'recruiter', 
        'talent', 'acquisition', 'sourcer', 'consultant', 'president', 'officer',
        'software', 'technologies', 'llc', 'inc', 'corp', 'solutions', 'group'
    ]
    
    # We will find rows that match these keywords and move them to notes
    cursor.execute("SELECT recruiter_id, recruiter_name, notes FROM recruiters WHERE recruiter_name IS NOT NULL")
    all_names = cursor.fetchall()
    
    title_moves = 0
    comma_cleans = 0
    space_cleans = 0

    for r_id, r_name, r_notes in all_names:
        original_name = r_name
        name_lower = r_name.lower()
        
        is_title = any(kw in name_lower for kw in invalid_keywords)
        
        # If it's a title, move it to notes
        if is_title:
            new_notes = r_notes or ''
            if r_name not in new_notes:
                new_notes = (new_notes + f"\\n[Original Name Field]: {r_name}").strip()
            
            cursor.execute("""
                UPDATE recruiters 
                SET recruiter_name = 'Unknown', notes = %s
                WHERE recruiter_id = %s
            """, (new_notes, r_id))
            title_moves += 1
            continue # Move on to the next one
            
        # Strip trailing commas
        if r_name.endswith(','):
            r_name = r_name[:-1].strip()
            
        # Strip internal commas if it looks like Lastname, Firstname without spaces
        if ',' in r_name:
            # Simple clean: replace comma with space and trim
            r_name = r_name.replace(',', ' ')
            
        # Reduce multiple spaces to single space and trim
        r_name = re.sub(r'\\s+', ' ', r_name).strip()
        
        if r_name != original_name:
            cursor.execute("""
                UPDATE recruiters 
                SET recruiter_name = %s
                WHERE recruiter_id = %s
            """, (r_name, r_id))
            
            if ',' in original_name:
                comma_cleans += 1
            else:
                space_cleans += 1

    print(f" -> Moved {title_moves:,} titles/companies to 'notes' (and reset Name to 'Unknown').")
    print(f" -> Stripped commas/symbols from {comma_cleans:,} names.")
    print(f" -> Scrubbed multiple whitespaces from {space_cleans:,} names.")
    
    conn.commit()
    print("\\n✅ All Deep Contact Refinement completed successfully!")

if __name__ == '__main__':
    run_deep_refinement()
