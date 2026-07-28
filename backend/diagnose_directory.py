import sqlite3

c = sqlite3.connect('dev.db')

# Check company location stats
total = c.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
null_loc = c.execute("SELECT COUNT(*) FROM companies WHERE location IS NULL OR location = ''").fetchone()[0]
has_loc = total - null_loc

print('=== COMPANY LOCATION STATS ===')
print(f'Total companies: {total}')
print(f'NULL/empty location: {null_loc}')
print(f'Has location: {has_loc}')

# Check the Missing and Unknown companies
missing = c.execute("SELECT company_id, company_name, location, website FROM companies WHERE LOWER(company_name) IN ('missing', 'unknown') LIMIT 5").fetchall()
print('\n=== MISSING/UNKNOWN COMPANIES ===')
for r in missing:
    print(r)
    rid_count = c.execute("SELECT COUNT(*) FROM recruiters WHERE company_id = ?", (r[0],)).fetchone()[0]
    print(f'  -> Recruiter count: {rid_count}')

# Check Vaco
vaco = c.execute("SELECT company_id, company_name, location, state FROM companies WHERE LOWER(company_name) LIKE 'vaco%' LIMIT 3").fetchall()
print('\n=== VACO ===')
for r in vaco:
    print(r)

vaco_ids = [r[0] for r in vaco]
if vaco_ids:
    placeholders = ','.join('?' * len(vaco_ids))
    vaco_states = c.execute(f"SELECT state, COUNT(*) as cnt FROM recruiters WHERE company_id IN ({placeholders}) AND state IS NOT NULL AND state != '' GROUP BY state ORDER BY cnt DESC LIMIT 10", vaco_ids).fetchall()
    print('Vaco recruiter states:', vaco_states)

# Check how many companies could get location from recruiter majority
print('\n=== COMPANIES WITH RECRUITER STATE DATA ===')
result = c.execute("""
    SELECT COUNT(DISTINCT c.company_id) 
    FROM companies c 
    JOIN recruiters r ON r.company_id = c.company_id 
    WHERE (c.location IS NULL OR c.location = '')
    AND r.state IS NOT NULL AND r.state != ''
""").fetchone()[0]
print(f'Companies with NULL location but recruiters HAVE states: {result}')

# Check top companies by recruiter count that are missing location
print('\n=== TOP 15 COMPANIES MISSING LOCATION (by recruiter count) ===')
rows = c.execute("""
    SELECT c.company_name, c.location, COUNT(r.recruiter_id) as cnt 
    FROM companies c
    JOIN recruiters r ON r.company_id = c.company_id
    WHERE c.location IS NULL OR c.location = ''
    GROUP BY c.company_id
    ORDER BY cnt DESC
    LIMIT 15
""").fetchall()
for r in rows:
    print(f'  {r[0]:40s} loc={r[1]!r:20s} recruiters={r[2]}')

c.close()
