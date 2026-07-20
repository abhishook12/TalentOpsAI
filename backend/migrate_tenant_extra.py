import os
from sqlalchemy import create_engine, text
from app.database import Base, engine

def run_migration():
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        res = conn.execute(text("SELECT id FROM users WHERE email = 'admin@talentops.com'"))
        admin_row = res.first()
        admin_id = admin_row[0]

        tables_to_isolate = ["candidates", "submissions"]

        for table in tables_to_isolate:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                print(f"Added user_id column to {table}")
                conn.execute(text(f"UPDATE {table} SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_id})
            except Exception as e:
                print(f"Error for {table}: {e}")

if __name__ == "__main__":
    run_migration()
