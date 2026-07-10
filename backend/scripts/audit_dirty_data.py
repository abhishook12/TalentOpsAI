import sys, os, io, psycopg
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.append('C:/TalentOpsAI/backend')
from dotenv import load_dotenv
load_dotenv('C:/TalentOpsAI/backend/.env')

raw_url = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DATABASE_URL') or ''
db_url = raw_url.replace('postgresql+psycopg://', 'postgresql://')
conn = psycopg.connect(db_url)
cur = conn.cursor()

print('=== DIRTY DATA AUDIT ACROSS ALL 327,319 RECRUITERS ===')
cur.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE email LIKE '%.dup.%') AS email_dup_suffix,
        COUNT(*) FILTER (WHERE email LIKE '%;%') AS email_semicolon,
        COUNT(*) FILTER (WHERE email LIKE '%,%') AS email_comma,
        COUNT(*) FILTER (WHERE email LIKE '%/%') AS email_slash,
        COUNT(*) FILTER (WHERE email LIKE '% %') AS email_space,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%;%') AS name_semicolon,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%,%') AS name_comma,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%/%') AS name_slash,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%[DUPLICATE]%') AS name_duplicate_tag,
        COUNT(*) FILTER (WHERE recruiter_name LIKE '%(%') AS name_paren
    FROM recruiters
""")
row = cur.fetchone()
print(f'Emails with .dup.XXXXX suffix: {row[0]:,}')
print(f'Emails with semicolon (;): {row[1]:,}')
print(f'Emails with comma (,): {row[2]:,}')
print(f'Emails with slash (/): {row[3]:,}')
print(f'Emails with space: {row[4]:,}')
print(f'Names with semicolon (;): {row[5]:,}')
print(f'Names with comma (,): {row[6]:,}')
print(f'Names with slash (/): {row[7]:,}')
print(f'Names with [DUPLICATE] tag: {row[8]:,}')
print(f'Names with parentheses: {row[9]:,}')

print('\n=== SAMPLE DIRTY RECRUITER ROWS ===')
cur.execute("""
    SELECT recruiter_id, recruiter_name, email 
    FROM recruiters 
    WHERE email LIKE '%.dup.%' OR email LIKE '%;%' OR recruiter_name LIKE '%;%' 
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"ID {r[0]}: Name='{r[1]}' | Email='{r[2]}'")

print('\n=== DIRTY DATA AUDIT ACROSS ALL 65,593 COMPANIES ===')
cur.execute("""
    SELECT 
        COUNT(*) FILTER (WHERE company_name LIKE '%[DUPLICATE]%') AS comp_duplicate_tag,
        COUNT(*) FILTER (WHERE logo_url IS NULL OR logo_url = '') AS comp_missing_logo,
        COUNT(*) FILTER (WHERE website IS NULL OR website = '') AS comp_missing_website
    FROM companies
""")
row_c = cur.fetchone()
print(f'Company names with [DUPLICATE] tag: {row_c[0]:,}')
print(f'Companies missing logo_url: {row_c[1]:,}')
print(f'Companies missing website: {row_c[2]:,}')

cur.close()
conn.close()
