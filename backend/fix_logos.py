from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Check 1: No Clearbit URLs left
r1 = db.execute(text("SELECT COUNT(*) FROM companies WHERE logo_url LIKE 'https://logo.clearbit.com/%'")).scalar()
print(f"CHECK 1 - Clearbit URLs remaining: {r1}")
assert r1 == 0, f"FAIL: {r1} Clearbit URLs still in DB"
print("CHECK 1 PASSED: Zero Clearbit URLs in database")

# Check 2: Hunter.io URLs present
r2 = db.execute(text("SELECT COUNT(*) FROM companies WHERE logo_url LIKE 'https://logos.hunter.io/%'")).scalar()
print(f"CHECK 2 - Hunter.io logo URLs: {r2}")
assert r2 > 0, "FAIL: No Hunter.io URLs found"
print(f"CHECK 2 PASSED: {r2} companies have Hunter.io logo URLs")

# Check 3: Sample logo URLs look correct
rows = db.execute(text("SELECT company_name, logo_url, primary_domain FROM companies WHERE logo_url IS NOT NULL AND primary_domain IS NOT NULL LIMIT 5")).fetchall()
print("CHECK 3 - Sample logo URLs:")
for row in rows:
    print(f"  {row[0]}: {row[1]} (domain: {row[2]})")
    assert 'hunter.io' in row[1] or row[1].startswith('http'), f"FAIL: Unexpected URL format: {row[1]}"
print("CHECK 3 PASSED: All sample URLs are valid")
