import sqlite3
import random

db_path = r'C:\TalentOpsAI\backend\dev.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get recruiters
c.execute("SELECT recruiter_id, email FROM recruiters")
recruiters = c.fetchall()

# Generate 50 companies
companies_data = []
states = ["CA", "NY", "TX", "FL", "WA", "IL", "GA", "PA", "NC", "VA"]
company_names = [f"TechCorp {i}" for i in range(1, 51)]

for i, name in enumerate(company_names):
    companies_data.append((
        1, # user_id
        name,
        name.lower().replace(" ", ""),
        "Technology",
        f"City {i}",
        random.choice(states),
        f"https://www.{name.lower().replace(' ', '')}.com",
        f"https://linkedin.com/company/{name.lower().replace(' ', '')}",
        1,
        1
    ))

c.executemany("""
    INSERT INTO companies (user_id, company_name, normalized_company_name, industry, location, state, website, linkedin_url, is_active, is_tracked)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", companies_data)

# Get inserted company IDs
c.execute("SELECT company_id FROM companies")
company_ids = [row[0] for row in c.fetchall()]

# Assign companies to recruiters
update_data = []
for recruiter in recruiters:
    comp_id = random.choice(company_ids)
    update_data.append((comp_id, recruiter[0]))

c.executemany("UPDATE recruiters SET company_id = ? WHERE recruiter_id = ?", update_data)

conn.commit()
conn.close()
print("Successfully generated companies and linked recruiters.")
