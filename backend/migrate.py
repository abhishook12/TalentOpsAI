from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    cols = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='recruiters'")).scalars().all()
    adds = []
    if "normalized_city" not in cols: adds.append("ADD COLUMN normalized_city VARCHAR(150)")
    if "location_confidence" not in cols: adds.append("ADD COLUMN location_confidence VARCHAR(20) DEFAULT 'high'")
    if "completeness_score" not in cols: adds.append("ADD COLUMN completeness_score INTEGER DEFAULT 0")
    if "needs_review" not in cols: adds.append("ADD COLUMN needs_review BOOLEAN DEFAULT FALSE")

    if adds:
        db.execute(text(f"ALTER TABLE recruiters {', '.join(adds)}"))
        
        # Add indexes
        if "normalized_city" not in cols: db.execute(text("CREATE INDEX ix_rec_norm_city ON recruiters(normalized_city)"))
        if "completeness_score" not in cols: db.execute(text("CREATE INDEX ix_rec_comp_score ON recruiters(completeness_score)"))
        if "needs_review" not in cols: db.execute(text("CREATE INDEX ix_rec_needs_rev ON recruiters(needs_review)"))
        
        db.commit()
        print("Migrated successfully.")
    else:
        print("Already up to date.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
