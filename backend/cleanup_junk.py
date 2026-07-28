import sqlite3
import re

c = sqlite3.connect('dev.db')
cur = c.cursor()

print("Starting cleanup...")

# 1. DELETE MISSING COMPANY RECRUITERS
# They only have names, no contact info, no location, no company.
missing_row = cur.execute("SELECT company_id FROM companies WHERE LOWER(company_name) = 'missing'").fetchone()
if missing_row:
    missing_id = missing_row[0]
    cur.execute("DELETE FROM recruiters WHERE company_id = ?", (missing_id,))
    print(f"Deleted {cur.rowcount} dead recruiters from 'Missing' company.")

    # Delete the Missing company itself
    cur.execute("DELETE FROM companies WHERE company_id = ?", (missing_id,))
    print("Deleted 'Missing' company record.")
else:
    print("The 'Missing' company has already been deleted.")

# 2. CLEAN UP UNKNOWN COMPANY RECRUITERS
unknown_id = cur.execute("SELECT company_id FROM companies WHERE LOWER(company_name) = 'unknown'").fetchone()[0]

# 2a. Move phone numbers stored in email column to phone column
phone_regex = r'^[\d\-\(\)\s\+\.]{7,20}$'
unknown_recruiters = cur.execute("SELECT recruiter_id, email, phone FROM recruiters WHERE company_id = ?", (unknown_id,)).fetchall()

moved_phones = 0
for r in unknown_recruiters:
    rid, email, phone = r
    if email and not '@' in email and re.match(phone_regex, email.strip()):
        # It's a phone number
        new_phone = email.strip()
        cur.execute("UPDATE recruiters SET phone = ?, email = ? WHERE recruiter_id = ?", (new_phone, f'unknown-{rid}@missing.local', rid))
        moved_phones += 1

print(f"Moved {moved_phones} phone numbers from email column to phone column.")

# 2b. Nullify bad emails (no @)
cur.execute("UPDATE recruiters SET email = 'corrupt-' || recruiter_id || '@missing.local' WHERE company_id = ? AND email NOT LIKE '%@%'", (unknown_id,))
print(f"Fixed {cur.rowcount} corrupt emails by assigning placeholder.")

# 2c. Nullify bad locations (literally 'location')
cur.execute("UPDATE recruiters SET location = NULL WHERE company_id = ? AND LOWER(location) = 'location'", (unknown_id,))
print(f"Nullified {cur.rowcount} corrupt locations.")

# 2d. Delete truly unsalvageable recruiters (no real name AND had a corrupt email)
cur.execute("""
    DELETE FROM recruiters 
    WHERE company_id = ?
    AND (recruiter_name IS NULL OR recruiter_name = '' OR LOWER(recruiter_name) IN ('name', 'unknown', 'not provided', 'n/a', 'nil', '-', '--', '---', 'point of contacts', 'not specified'))
    AND email LIKE '%@missing.local'
""", (unknown_id,))
print(f"Deleted {cur.rowcount} unsalvageable recruiters from 'Unknown' company.")

c.commit()
c.close()
print("Cleanup complete!")
