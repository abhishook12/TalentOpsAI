"""
Direct bulk import of TalentOps_Recruiters_Formatted.xlsx into Neon PostgreSQL.
Data starts at row 17 (row 16 = headers).
Columns: company, recruiter_name, email, email2, phone, phone2, linkedin, specialization, notes
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

import openpyxl
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# ── DB connection ──────────────────────────────────────────────────────────────
RAW_URL = os.getenv("DATABASE_URL", "")
if not RAW_URL or "localhost" in RAW_URL:
    # Prompt for Neon URL if .env has localhost
    RAW_URL = input("Paste your Neon DATABASE_URL: ").strip()

DB_URL = RAW_URL.replace("postgresql://", "postgresql+psycopg://")
engine = create_engine(DB_URL, pool_pre_ping=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(v):
    if v is None: return None
    s = str(v).strip()
    return s if s and s.lower() not in ('none', 'n/a', 'null', '-', '') else None

def clean_phone(v):
    if not v: return None
    digits = re.sub(r'[^\d+]', '', str(v))
    # strip leading country code 1 if 11 digits
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits if len(digits) >= 7 else None

def clean_email(v):
    if not v: return None
    e = str(v).lower().strip()
    return e if '@' in e and '.' in e.split('@')[-1] else None

def clean_name(v):
    if not v: return None
    s = str(v).strip().title()
    return s if s else None

# ── Read Excel ────────────────────────────────────────────────────────────────
FILE = r"C:\Users\User\Desktop\TalentOps_Recruiters_Formatted.xlsx"
print(f"Reading: {FILE}")
wb = openpyxl.load_workbook(FILE, read_only=True)
ws = wb.active

# Row 16 = headers, Row 17+ = data
all_rows = list(ws.iter_rows(min_row=16, values_only=True))
headers = [str(h).strip().lower() if h else '' for h in all_rows[0]]
data_rows = all_rows[1:]
print(f"Headers: {headers}")
print(f"Total data rows: {len(data_rows)}")

# ── Bulk Insert ───────────────────────────────────────────────────────────────
inserted = 0
skipped_dup = 0
skipped_no_email = 0
errors = 0

INSERT_SQL = text("""
    INSERT INTO recruiters (recruiter_name, email, phone, email2, phone2, linkedin, specialization, notes, is_active)
    VALUES (:recruiter_name, :email, :phone, :email2, :phone2, :linkedin, :specialization, :notes, true)
    ON CONFLICT (email) DO NOTHING
""")

BATCH_SIZE = 500
batch = []

def flush(conn, batch):
    if not batch: return 0
    result = conn.execute(INSERT_SQL, batch)
    return result.rowcount

with engine.connect() as conn:
    for i, row in enumerate(data_rows):
        d = dict(zip(headers, row))

        email = clean_email(d.get('email'))
        if not email:
            skipped_no_email += 1
            continue

        record = {
            'recruiter_name': clean_name(d.get('recruiter_name')) or email.split('@')[0].title(),
            'email':          email,
            'phone':          clean_phone(d.get('phone')),
            'email2':         clean_email(d.get('email2')),
            'phone2':         clean_phone(d.get('phone2')),
            'linkedin':       clean(d.get('linkedin')),
            'specialization': clean(d.get('specialization')),
            'notes':          clean(d.get('notes')),
        }
        batch.append(record)

        if len(batch) >= BATCH_SIZE:
            n = flush(conn, batch)
            inserted += n
            skipped_dup += len(batch) - n
            conn.commit()
            print(f"  ...processed {i+1} rows, inserted so far: {inserted}")
            batch = []

    # Final batch
    if batch:
        n = flush(conn, batch)
        inserted += n
        skipped_dup += len(batch) - n
        conn.commit()

print(f"\nDone!")
print(f"  Inserted      : {inserted}")
print(f"  Skipped (dup) : {skipped_dup}")
print(f"  Skipped (no email): {skipped_no_email}")
print(f"  Total rows processed: {len(data_rows)}")
