import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from app.database import engine
from sqlalchemy import text

def vacuum_db():
    print("Connecting to DB for VACUUM FULL...")
    with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
        print("Running VACUUM FULL on recruiters...")
        conn.execute(text("VACUUM FULL recruiters"))
        print("VACUUM FULL complete.")
    
    # Check new size
    with engine.connect() as conn2:
        size = conn2.execute(text("SELECT pg_database_size(current_database()) / (1024 * 1024)")).fetchone()[0]
        print(f"New DB Size: {size} MB")

if __name__ == "__main__":
    vacuum_db()
