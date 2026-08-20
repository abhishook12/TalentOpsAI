import sys
sys.path.append('backend')
from app.database import SessionLocal
from app.models.models import Company, Recruiter
import duckdb

db = SessionLocal()
comp_count = db.query(Company).count()
print(f"Postgres total companies: {comp_count}")

top_comps = db.query(Company).filter(Company.company_name.ilike('%rht%')).all()
print(f"Postgres 'rht' companies: {len(top_comps)}")
for c in top_comps[:10]:
    print(c.company_id, c.company_name, c.primary_domain, c.location)

# Check Parquet schema
con = duckdb.connect()
print("\nParquet columns:")
print(con.execute("DESCRIBE SELECT * FROM 'backend/data/recruiters_full.parquet'").fetchall())

# Check how company_id and company_name look in parquet for rht.com
print("\nParquet sample rht.com rows:")
sample = con.execute("""
    SELECT company_id, recruiter_name, email, location, state
    FROM 'backend/data/recruiters_full.parquet'
    WHERE email LIKE '%@rht.com'
    LIMIT 10
""").fetchall()
for s in sample:
    print(s)

db.close()
