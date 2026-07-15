import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

conn = engine.connect()

# Get all columns
cols = conn.execute(text(
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'recruiters' ORDER BY ordinal_position"
)).fetchall()
print("=== RECRUITER TABLE SCHEMA ===")
for c in cols:
    print(f"  {c[0]:30s} {c[1]}")

# Check nulls for all text columns
print("\n=== FIELD COMPLETENESS (active recruiters) ===")
text_cols = [c[0] for c in cols if c[1] in ('character varying', 'text')]
for col in text_cols:
    r = conn.execute(text(f"SELECT COUNT(*) FILTER (WHERE {col} IS NULL OR {col} = '') FROM recruiters WHERE is_active = true")).fetchone()
    missing = r[0]
    if missing > 0:
        print(f"  {col:30s} missing: {missing}")

conn.close()
