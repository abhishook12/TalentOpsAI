from app.database import SessionLocal
from app.models.models import Company

def fix_remaining():
    db = SessionLocal()
    
    missing_companies = db.query(Company).filter(
        (Company.website == None) | (Company.website == ""),
        (Company.email_pattern == None) | (Company.email_pattern == "")
    ).all()
    
    fixes = {
        67942: "ecomsolutions.net",
        65406: "lucid.co",
        64960: "honestsearch.co",
        64586: "expresspros.com",
        67996: "eternalstaffing.com"
    }
    
    for c in missing_companies:
        if c.company_id in fixes:
            c.website = fixes[c.company_id]
            print(f"Fixed {c.company_name} -> {c.website}")
            
    db.commit()
    print("All fixed!")
        
if __name__ == "__main__":
    fix_remaining()
