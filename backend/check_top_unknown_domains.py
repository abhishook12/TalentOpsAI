import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from database import SessionLocal
from sqlalchemy import text
from collections import Counter

def main():
    db = SessionLocal()
    
    # Get all emails of unknown states
    emails = db.execute(text("SELECT email FROM recruiters WHERE state = 'Unknown' OR state IS NULL")).fetchall()
    
    domains = []
    for row in emails:
        em = row[0]
        if em and '@' in em:
            domain = em.split('@')[-1].lower().strip()
            domains.append(domain)
            
    counter = Counter(domains)
    print("Top 250 Unknown Domains:")
    for dom, count in counter.most_common(250):
        print(f"{dom.encode('ascii', 'ignore').decode('ascii')}: {count}")
        
    print(f"\nTotal unknown recruiters: {len(emails)}")
    
    # How many would we solve if we resolve the top 100 domains?
    top_100 = sum(count for dom, count in counter.most_common(100))
    top_500 = sum(count for dom, count in counter.most_common(500))
    top_1000 = sum(count for dom, count in counter.most_common(1000))
    print(f"Resolving top 100 domains resolves: {top_100} recruiters")
    print(f"Resolving top 500 domains resolves: {top_500} recruiters")
    print(f"Resolving top 1000 domains resolves: {top_1000} recruiters")
    print(f"Total unique unknown domains: {len(counter)}")
    
    db.close()

if __name__ == '__main__':
    main()
