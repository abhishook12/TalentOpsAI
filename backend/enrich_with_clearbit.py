import time
import requests
from app.database import SessionLocal
from app.models.models import Company

def fix_missing_logos_clearbit():
    db = SessionLocal()
    
    missing_companies = db.query(Company).filter(
        (Company.website == None) | (Company.website == ""),
        (Company.email_pattern == None) | (Company.email_pattern == "")
    ).all()
    
    print(f"Found {len(missing_companies)} companies missing logos. Enriching with Clearbit Autocomplete...")
    
    updated_count = 0
    for company in missing_companies:
        query = company.company_name.replace(".com", "")
        print(f"Searching Clearbit for: {query}")
        try:
            res = requests.get(f"https://autocomplete.clearbit.com/v1/companies/suggest?query={query}", timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    domain = data[0]['domain']
                    print(f"  -> Found domain: {domain}")
                    company.website = domain
                    updated_count += 1
                else:
                    print(f"  -> No results found")
            else:
                print(f"  -> API Error: {res.status_code}")
                
            time.sleep(1)
        except Exception as e:
            print(f"  -> Request Error: {e}")
            
    db.commit()
    print(f"Successfully enriched {updated_count} companies with a website domain!")
    db.close()

if __name__ == "__main__":
    fix_missing_logos_clearbit()
