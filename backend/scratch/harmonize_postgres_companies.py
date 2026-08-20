import sys
sys.path.append('backend')
from app.database import SessionLocal
from app.models.models import Company

db = SessionLocal()

# Check 163785
c_rht = db.query(Company).filter(Company.company_id == 163785).first()
if c_rht:
    print(f"Postgres 163785: name='{c_rht.company_name}', domain='{c_rht.primary_domain}'")
    c_rht.company_name = "Robert Half Technology (RHT)"
    c_rht.primary_domain = "rht.com"
    c_rht.website = "https://www.rht.com"
else:
    c_rht = Company(
        company_id=163785,
        company_name="Robert Half Technology (RHT)",
        primary_domain="rht.com",
        website="https://www.rht.com"
    )
    db.add(c_rht)

# Check 161735
c_rh = db.query(Company).filter(Company.company_id == 161735).first()
if c_rh:
    print(f"Postgres 161735: name='{c_rh.company_name}', domain='{c_rh.primary_domain}'")
    c_rh.company_name = "Robert Half"
    c_rh.primary_domain = "roberthalf.com"
    c_rh.website = "https://www.roberthalf.com"
else:
    c_rh = Company(
        company_id=161735,
        company_name="Robert Half",
        primary_domain="roberthalf.com",
        website="https://www.roberthalf.com"
    )
    db.add(c_rh)

db.commit()
print("PostgreSQL canonical companies updated successfully!")
db.close()
