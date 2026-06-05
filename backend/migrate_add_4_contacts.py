import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing")

engine = create_engine(DATABASE_URL)

def run_migration():
    print("Starting migration to add email3, email4, phone3, phone4 to recruiters table...")
    with engine.connect() as conn:
        columns_to_add = [
            ("email3", "VARCHAR(150)"),
            ("email4", "VARCHAR(150)"),
            ("phone3", "VARCHAR(30)"),
            ("phone4", "VARCHAR(30)")
        ]
        
        for col, dtype in columns_to_add:
            print(f"Checking/Adding {col} to recruiters...")
            try:
                # Basic check if column exists
                conn.execute(text(f"SELECT {col} FROM recruiters LIMIT 1"))
                print(f"{col} already exists, skipping.")
            except Exception as e:
                # Column doesn't exist, we add it
                try:
                    # Clear transaction error state in postgres
                    conn.execute(text("ROLLBACK"))
                    conn.execute(text(f"ALTER TABLE recruiters ADD COLUMN {col} {dtype}"))
                    conn.execute(text("COMMIT"))
                    print(f"Added {col} successfully.")
                except Exception as inner_e:
                    print(f"Error adding {col}: {inner_e}")

    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
