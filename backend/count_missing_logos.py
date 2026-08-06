from app.database import SessionLocal
from app.models.models import Company

def count_missing_logos():
    db = SessionLocal()
    # A company might have a logo if it has a website or email_pattern
    # For a stricter check, we can just count those where both are empty/null
    missing_count = db.query(Company).filter(
        (Company.website == None) | (Company.website == ""),
        (Company.email_pattern == None) | (Company.email_pattern == "")
    ).count()
    
    total = db.query(Company).count()
    print(f"Companies missing logo domain: {missing_count} out of {total}")
    db.close()

if __name__ == "__main__":
    count_missing_logos()
