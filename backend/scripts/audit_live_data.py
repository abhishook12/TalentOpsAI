import psycopg, os
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')

conn = psycopg.connect(os.getenv('DATABASE_URL').replace('postgresql+psycopg://','postgresql://'), autocommit=True)
cur = conn.cursor()

print("=" * 70)
print("WHAT'S ACTUALLY IN THE DATABASE RIGHT NOW")
print("=" * 70)

# Total counts
cur.execute("SELECT COUNT(*) FROM recruiters")
total = cur.fetchone()[0]
print(f"\nTotal Recruiters: {total:,}")

cur.execute("SELECT COUNT(*) FROM companies WHERE is_active = true")
print(f"Active Companies: {cur.fetchone()[0]:,}")

# Email status breakdown
print("\n--- RECRUITER EMAIL STATUS BREAKDOWN ---")
cur.execute("SELECT email_status, COUNT(*) as cnt FROM recruiters GROUP BY email_status ORDER BY cnt DESC")
for row in cur.fetchall():
    pct = (row[1] / total * 100) if total else 0
    print(f"  {row[0]}: {row[1]:,} ({pct:.1f}%)")

# Company mapping
print("\n--- COMPANY MAPPING ---")
cur.execute("SELECT COUNT(*) FROM recruiters WHERE company_id IS NOT NULL")
with_company = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM recruiters WHERE company_id IS NULL")
no_company = cur.fetchone()[0]
print(f"  With company: {with_company:,} ({with_company/total*100:.1f}%)")
print(f"  No company:   {no_company:,} ({no_company/total*100:.1f}%)")

# Title/specialization coverage
print("\n--- FIELD COVERAGE ---")
for field in ['title', 'specialization', 'location', 'recruiter_name', 'phone']:
    cur.execute(f"SELECT COUNT(*) FROM recruiters WHERE {field} IS NOT NULL AND {field} != '' AND {field} != 'Unknown'")
    filled = cur.fetchone()[0]
    print(f"  {field}: {filled:,} filled ({filled/total*100:.1f}%)")

# Top 20 companies by recruiter count
print("\n--- TOP 20 COMPANIES (by recruiter count) ---")
cur.execute("""
    SELECT c.company_name, COUNT(r.recruiter_id) as cnt, c.website
    FROM recruiters r
    JOIN companies c ON r.company_id = c.company_id
    WHERE c.is_active = true
    GROUP BY c.company_name, c.website
    ORDER BY cnt DESC
    LIMIT 20
""")
for i, row in enumerate(cur.fetchall(), 1):
    print(f"  {i:2}. {row[0][:40]:<40} {row[1]:>6,} recruiters  [{row[2] or 'no website'}]")

# What email statuses mean in terms of usability
print("\n--- USABILITY ASSESSMENT ---")
cur.execute("SELECT COUNT(*) FROM recruiters WHERE email_status IN ('verified', 'verified_pattern', 'syntax_valid', 'likely')")
high_quality = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM recruiters WHERE email_status IN ('generic_provider', 'inferred')")
medium_quality = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM recruiters WHERE email_status IN ('unknown', 'missing_placeholder', 'scrubbed_placeholder')")
low_quality = cur.fetchone()[0]

print(f"  HIGH quality (verified/pattern/syntax_valid/likely): {high_quality:,} ({high_quality/total*100:.1f}%)")
print(f"  MEDIUM quality (generic_provider/inferred):          {medium_quality:,} ({medium_quality/total*100:.1f}%)")
print(f"  LOW quality (unknown/placeholder):                   {low_quality:,} ({low_quality/total*100:.1f}%)")

# Sample of unknown recruiters to show what they look like
print("\n--- SAMPLE OF REMAINING 'unknown' RECRUITERS ---")
cur.execute("""
    SELECT r.recruiter_name, r.email, r.title, c.company_name, r.location
    FROM recruiters r
    LEFT JOIN companies c ON r.company_id = c.company_id
    WHERE r.email_status = 'unknown'
    LIMIT 15
""")
for row in cur.fetchall():
    name = (row[0] or 'None')[:25]
    email = (row[1] or 'None')[:35]
    title = (row[2] or 'None')[:25]
    company = (row[3] or 'None')[:25]
    loc = (row[4] or 'None')[:10]
    print(f"  {name:<25} | {email:<35} | {title:<25} | {company:<25} | {loc}")

print("\n" + "=" * 70)
conn.close()
