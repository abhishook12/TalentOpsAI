import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)

def add_columns():
    with engine.connect() as conn:
        print("Checking/Adding alternate_emails to recruiters...")
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN alternate_emails TEXT"))
            print("Added alternate_emails")
        except Exception as e:
            print("alternate_emails already exists or error:", str(e))
            
        print("Checking/Adding alternate_phones to recruiters...")
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN alternate_phones TEXT"))
            print("Added alternate_phones")
        except Exception as e:
            print("alternate_phones already exists or error:", str(e))
            
        print("Checking/Adding review_reason to recruiters...")
        try:
            conn.execute(text("ALTER TABLE recruiters ADD COLUMN review_reason TEXT"))
            print("Added review_reason")
        except Exception as e:
            print("review_reason already exists or error:", str(e))
            
        conn.commit()
        print("Done!")

if __name__ == "__main__":
    add_columns()
