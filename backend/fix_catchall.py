import sqlite3
c = sqlite3.connect('dev.db')

# Fix the catch-all companies
c.execute("UPDATE companies SET location = 'Multiple Locations' WHERE LOWER(company_name) = 'unknown'")
c.execute("UPDATE companies SET location = 'Not Available' WHERE LOWER(company_name) = 'missing'")
c.commit()

# Check what Missing recruiters look like
rows = c.execute("""SELECT recruiter_name, email, phone, state FROM recruiters 
    WHERE company_id IN (SELECT company_id FROM companies WHERE LOWER(company_name) = 'missing')
    LIMIT 10""").fetchall()
print('=== SAMPLE MISSING RECRUITERS ===')
for r in rows:
    print(f'  name={r[0]!r:30s} email={r[1]!r:35s} phone={r[2]!r:20s} state={r[3]!r}')

rows2 = c.execute("""SELECT recruiter_name, email, phone, state FROM recruiters 
    WHERE company_id IN (SELECT company_id FROM companies WHERE LOWER(company_name) = 'unknown')
    LIMIT 10""").fetchall()
print('\n=== SAMPLE UNKNOWN RECRUITERS ===')
for r in rows2:
    print(f'  name={r[0]!r:30s} email={r[1]!r:35s} phone={r[2]!r:20s} state={r[3]!r}')

c.close()
