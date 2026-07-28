import sqlite3
import re
import time

def extract_name_from_email(email):
    if not email or "@" not in email:
        return None
    local_part = email.split('@')[0].lower()
    local_part = re.sub(r'[^a-z0-9\.]', '', local_part)
    
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) >= 2 and len(parts[0]) >= 1 and len(parts[1]) >= 2:
            first = parts[0].capitalize()
            last = parts[1].capitalize()
            return f"{first} {last}"
            
    if len(local_part) > 3 and sum(c.isdigit() for c in local_part) < 3:
        first = local_part[0].upper() + "."
        last = local_part[1:].capitalize()
        return f"{first} {last}"
        
    return None

def build_linkedin_url(name, company_name):
    if not name or not company_name:
        return None
        
    parts = name.split(' ', 1)
    if len(parts) != 2:
        return None
        
    slug_first = re.sub(r'[^a-z0-9\-]', '', parts[0].lower().replace('.', '').replace(' ', '-'))
    slug_last = re.sub(r'[^a-z0-9\-]', '', parts[1].lower().replace('.', '').replace(' ', '-'))
    slug_company = re.sub(r'[^a-z0-9\-]', '', company_name.lower().replace(' ', '-'))
    
    if slug_first and slug_last and slug_company:
        return f"linkedin.com/in/{slug_first}-{slug_last}-{slug_company}"
    return None

def main():
    print("Connecting to dev.db...")
    conn = sqlite3.connect('dev.db')
    c = conn.cursor()

    # Find recruiters with missing LinkedIn URLs, but valid emails.
    # Exclude obvious generic emails.
    print("Fetching recruiters for name and LinkedIn extraction...")
    c.execute('''
        SELECT r.recruiter_id, r.email, c.company_name
        FROM recruiters r
        LEFT JOIN companies c ON r.company_id = c.company_id
        WHERE (r.linkedin IS NULL OR r.linkedin = '')
          AND r.email IS NOT NULL 
          AND r.email LIKE '%@%'
          AND r.email NOT LIKE 'info@%'
          AND r.email NOT LIKE 'contact@%'
          AND r.email NOT LIKE 'sales@%'
          AND r.email NOT LIKE 'support@%'
          AND r.email NOT LIKE 'admin@%'
    ''')
    rows = c.fetchall()
    
    print(f"Found {len(rows)} recruiters to process.")
    
    updates = []
    names_extracted = 0
    linkedins_generated = 0
    
    for r_id, email, company_name in rows:
        name = extract_name_from_email(email)
        if name:
            names_extracted += 1
            linkedin = build_linkedin_url(name, company_name) if company_name else None
            if linkedin:
                linkedins_generated += 1
                
            updates.append((name, linkedin, r_id))
            
    print(f"Extracted {names_extracted} names and generated {linkedins_generated} LinkedIn URLs.")
    
    batch_size = 10000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        c.executemany('''
            UPDATE recruiters 
            SET recruiter_name = ?, linkedin = ?, updated_at = CURRENT_TIMESTAMP
            WHERE recruiter_id = ?
        ''', batch)
        conn.commit()
        print(f"Updated {i + len(batch)} / {len(updates)} records...")
        
    conn.close()
    print("Successfully completed Name & LinkedIn Enrichment!")

if __name__ == "__main__":
    start = time.time()
    main()
    print(f"Done in {time.time() - start:.2f} seconds.")
