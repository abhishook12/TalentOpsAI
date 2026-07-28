"""Deep analysis of Missing and Unknown company data to plan cleanup"""
import sqlite3
from collections import Counter

c = sqlite3.connect('dev.db')

# ─── MISSING COMPANY ANALYSIS ───
print("=" * 60)
print("MISSING COMPANY (15,335 recruiters)")
print("=" * 60)

missing_id = c.execute("SELECT company_id FROM companies WHERE LOWER(company_name) = 'missing'").fetchone()[0]

# How many have real names vs placeholder names?
total = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ?", (missing_id,)).fetchone()[0]
real_names = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND recruiter_name IS NOT NULL AND recruiter_name != '' AND LOWER(recruiter_name) NOT IN ('name', 'unknown', 'not provided', 'n/a', 'nil', '-', '--', '---')", (missing_id,)).fetchone()[0]
has_phone = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND phone IS NOT NULL AND phone != ''", (missing_id,)).fetchone()[0]
has_linkedin = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND linkedin IS NOT NULL AND linkedin != '' AND linkedin NOT LIKE '%missing%'", (missing_id,)).fetchone()[0]
has_notes = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND notes IS NOT NULL AND notes != ''", (missing_id,)).fetchone()[0]
has_location = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND location IS NOT NULL AND location != ''", (missing_id,)).fetchone()[0]
has_specialization = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND specialization IS NOT NULL AND specialization != ''", (missing_id,)).fetchone()[0]

print(f"Total: {total}")
print(f"Real names: {real_names}")
print(f"Has phone: {has_phone}")
print(f"Has LinkedIn (non-missing): {has_linkedin}")
print(f"Has notes: {has_notes}")
print(f"Has location: {has_location}")
print(f"Has specialization: {has_specialization}")

# Sample the ones with the MOST data
print("\nSample recruiters WITH some data:")
samples = c.execute("""
    SELECT recruiter_name, email, phone, linkedin, location, specialization, notes
    FROM recruiters WHERE company_id = ? 
    AND (phone IS NOT NULL AND phone != '' OR location IS NOT NULL AND location != '')
    LIMIT 10
""", (missing_id,)).fetchall()
for s in samples:
    print(f"  name={s[0]!r:25s} phone={s[2]!r:18s} loc={s[4]!r:15s} spec={s[5]!r:20s}")

# Placeholder name count
placeholder_names = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND (recruiter_name IS NULL OR recruiter_name = '' OR LOWER(recruiter_name) IN ('name', 'unknown', 'not provided', 'n/a', 'nil', '-', '--', '---'))", (missing_id,)).fetchone()[0]
print(f"\nPlaceholder/empty names: {placeholder_names}")

# ─── UNKNOWN COMPANY ANALYSIS ───
print("\n" + "=" * 60)
print("UNKNOWN COMPANY (6,977 recruiters)")
print("=" * 60)

unknown_id = c.execute("SELECT company_id FROM companies WHERE LOWER(company_name) = 'unknown'").fetchone()[0]

total_u = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ?", (unknown_id,)).fetchone()[0]
real_names_u = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND recruiter_name IS NOT NULL AND recruiter_name != '' AND LOWER(recruiter_name) NOT IN ('name', 'unknown', 'not provided', 'n/a', 'nil', '-', '--', '---', 'point of contacts', 'not specified')", (unknown_id,)).fetchone()[0]
junk_names_u = total_u - real_names_u
has_phone_u = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND phone IS NOT NULL AND phone != ''", (unknown_id,)).fetchone()[0]
has_real_email_u = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND email LIKE '%@%' AND email NOT LIKE 'no-email%'", (unknown_id,)).fetchone()[0]
has_location_u = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ? AND location IS NOT NULL AND location != ''", (unknown_id,)).fetchone()[0]

print(f"Total: {total_u}")
print(f"Real names: {real_names_u}")
print(f"Junk/placeholder names: {junk_names_u}")
print(f"Has phone: {has_phone_u}")
print(f"Has real email (@): {has_real_email_u}")
print(f"Has location: {has_location_u}")

# Sample the corrupt emails
print("\nSample corrupt emails:")
corrupt = c.execute("""
    SELECT recruiter_name, email, phone, location
    FROM recruiters WHERE company_id = ?
    AND (email NOT LIKE '%@%' OR email IS NULL OR email = '')
    LIMIT 15
""", (unknown_id,)).fetchall()
for s in corrupt:
    print(f"  name={s[0]!r:30s} email={s[1]!r:25s} phone={s[2]!r:18s} loc={s[3]!r}")

# Count truly unsalvageable (no name AND no email AND no phone)
unsalvageable = c.execute("""
    SELECT COUNT(*) FROM recruiters WHERE company_id = ?
    AND (recruiter_name IS NULL OR recruiter_name = '' OR LOWER(recruiter_name) IN ('name', 'unknown', 'not provided', 'n/a', 'nil', '-', '--', '---', 'point of contacts', 'not specified'))
    AND (email NOT LIKE '%@%' OR email IS NULL OR email = '')
    AND (phone IS NULL OR phone = '')
""", (unknown_id,)).fetchone()[0]
print(f"\nTruly unsalvageable (no name, no email, no phone): {unsalvageable}")

c.close()
