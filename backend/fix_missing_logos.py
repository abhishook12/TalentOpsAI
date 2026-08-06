import time
from app.database import SessionLocal
from app.models.models import Company
from urllib.parse import urlparse

try:
    from googlesearch import search
except ImportError:
    import os
    os.system("pip install googlesearch-python")
    from googlesearch import search

def fix_missing_logos():
    db = SessionLocal()
    
    missing_companies = db.query(Company).filter(
        (Company.website == None) | (Company.website == ""),
        (Company.email_pattern == None) | (Company.email_pattern == "")
    ).all()
    
    print(f"Found {len(missing_companies)} companies missing logos. Enriching...")
    
    updated_count = 0
    for company in missing_companies:
        query = f'"{company.company_name}" official website URL'
        print(f"Searching for: {query}")
        try:
            results = list(search(query, num_results=3))
            
            if results:
                url = results[0]
                domain = urlparse(url).netloc.replace("www.", "")
                
                # Exclude common aggregator sites just in case
                if domain not in ["linkedin.com", "glassdoor.com", "crunchbase.com", "indeed.com", "facebook.com", "x.com", "twitter.com", "bloomberg.com", "wikipedia.org"]:
                    print(f"  -> Found domain: {domain}")
                    company.website = domain
                    updated_count += 1
                else:
                    if len(results) > 1:
                        url2 = results[1]
                        domain2 = urlparse(url2).netloc.replace("www.", "")
                        if domain2 not in ["linkedin.com", "glassdoor.com", "crunchbase.com", "indeed.com", "facebook.com", "x.com", "twitter.com", "bloomberg.com", "wikipedia.org"]:
                            print(f"  -> Found domain (2nd result): {domain2}")
                            company.website = domain2
                            updated_count += 1
                        else:
                            print(f"  -> Only found aggregators")
            else:
                print(f"  -> No results found")
                
            time.sleep(2)
        except Exception as e:
            print(f"  -> Error: {e}")
            time.sleep(5)
            
    db.commit()
    print(f"Successfully enriched {updated_count} companies with a website domain!")
    db.close()

if __name__ == "__main__":
    fix_missing_logos()
