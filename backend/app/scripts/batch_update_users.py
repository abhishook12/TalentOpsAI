import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres')
SessionLocal = sessionmaker(bind=engine)

def main():
    db = SessionLocal()
    print("Updating companies...")
    db.execute(text("UPDATE companies SET user_id = 56 WHERE user_id IS NULL OR user_id = 20"))
    db.commit()
    print("Updating vendors...")
    db.execute(text("UPDATE vendors SET user_id = 56 WHERE user_id IS NULL OR user_id = 20"))
    db.commit()

    print("Updating recruiters in batches...")
    batch_size = 10000
    updated = 0
    while True:
        # We find recruiters that are NOT user_id 56, and update 10000 of them
        # Wait, since there's no index on user_id, a simple UPDATE with LIMIT might not work in Postgres directly without a CTE
        sql = text("""
            UPDATE recruiters 
            SET user_id = 56 
            WHERE recruiter_id IN (
                SELECT recruiter_id FROM recruiters 
                WHERE user_id IS NULL OR user_id != 56 
                LIMIT :batch_size
            )
        """)
        res = db.execute(sql, {"batch_size": batch_size})
        db.commit()
        if res.rowcount == 0:
            break
        updated += res.rowcount
        print(f"Updated {updated} recruiters...")
    print("Done!")

if __name__ == "__main__":
    main()
