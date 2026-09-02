from app.services.recruiter_store import recruiter_store

recruiter_store._ensure_loaded()
conn = recruiter_store._conn

cols = conn.execute("DESCRIBE recruiters").fetchall()
print("=== RECRUITERS TABLE COLUMNS IN DUCKDB ===")
for c in cols:
    print(f"  {c[0]}: {c[1]}")

total = conn.execute("SELECT COUNT(*) FROM recruiters").fetchone()[0]
print(f"\nTotal records in DuckDB: {total}")

missing_comp = conn.execute("SELECT COUNT(*) FROM recruiters WHERE company_name IS NULL OR company_name = '' OR LOWER(company_name) = 'unknown'").fetchone()[0]
missing_dom = conn.execute("SELECT COUNT(*) FROM recruiters WHERE company_domain IS NULL OR company_domain = ''").fetchone()[0]
missing_logo = conn.execute("SELECT COUNT(*) FROM recruiters WHERE logo_url IS NULL OR logo_url = ''").fetchone()[0]
clearbit_logos = conn.execute("SELECT COUNT(*) FROM recruiters WHERE logo_url LIKE '%logo.clearbit.com%'").fetchone()[0]
hunter_logos = conn.execute("SELECT COUNT(*) FROM recruiters WHERE logo_url LIKE '%logos.hunter.io%'").fetchone()[0]

print(f"Missing company_name: {missing_comp}")
print(f"Missing company_domain: {missing_dom}")
print(f"Missing logo_url: {missing_logo}")
print(f"Clearbit logo_url in DuckDB: {clearbit_logos}")
print(f"Hunter.io logo_url in DuckDB: {hunter_logos}")

# Sample missing records
print("\nSample records with missing/empty company or domain:")
sample = conn.execute("""
    SELECT recruiter_id, recruiter_name, email, company_name, company_domain, logo_url 
    FROM recruiters 
    WHERE (company_domain IS NULL OR company_domain = '' OR logo_url IS NULL OR logo_url = '' OR logo_url LIKE '%logo.clearbit.com%')
    LIMIT 10
""").fetchall()

for row in sample:
    print(f"ID={row[0]} | Name={row[1]} | Email={row[2]} | Company={row[3]} | Domain={row[4]} | Logo={row[5]}")
