import sqlite3

db_path = r'C:\TalentOpsAI\backend\dev.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Reset recruiters company_id to NULL
c.execute("UPDATE recruiters SET company_id = NULL")

# 2. Delete the mock companies
c.execute("DELETE FROM companies")

# 3. Get all recruiters with emails
c.execute("SELECT recruiter_id, email FROM recruiters WHERE email IS NOT NULL AND email != ''")
recruiters = c.fetchall()

# 4. Extract domains and map recruiters to domains
domain_to_recruiters = {}
for r_id, email in recruiters:
    try:
        domain = email.split('@')[1].strip().lower()
        if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com', 'outlook.com']:
            if domain not in domain_to_recruiters:
                domain_to_recruiters[domain] = []
            domain_to_recruiters[domain].append(r_id)
    except:
        pass

# 5. Insert real companies based on domains
companies_data = []
company_names = list(domain_to_recruiters.keys())
for i, domain in enumerate(company_names):
    company_name = domain.split('.')[0].capitalize()
    companies_data.append((
        1, # user_id
        company_name, # company_name
        company_name.lower().replace(" ", ""), # normalized_company_name
        "Staffing/Recruiting", # industry
        None, # location
        None, # state
        f"https://www.{domain}", # website
        None, # linkedin_url
        1, # is_active
        1 # is_tracked
    ))

c.executemany("""
    INSERT INTO companies (user_id, company_name, normalized_company_name, industry, location, state, website, linkedin_url, is_active, is_tracked)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", companies_data)

# 6. Map the inserted companies back to recruiters
c.execute("SELECT company_id, website FROM companies")
inserted_companies = c.fetchall()
domain_to_company_id = {website.split('www.')[1]: comp_id for comp_id, website in inserted_companies}

update_data = []
for domain, r_ids in domain_to_recruiters.items():
    comp_id = domain_to_company_id.get(domain)
    if comp_id:
        for r_id in r_ids:
            update_data.append((comp_id, r_id))

c.executemany("UPDATE recruiters SET company_id = ? WHERE recruiter_id = ?", update_data)

conn.commit()
conn.close()

print(f"Successfully extracted {len(domain_to_recruiters)} real companies from recruiter emails and linked them to their respective recruiters.")
