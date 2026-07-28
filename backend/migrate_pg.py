import sys
import os

from sqlalchemy import text
from app.database import engine, Base
from app.models.auth_models import TrustedDevice

def migrate():
    print("Running Postgres migrations...")
    
    # Create the trusted_devices table if it doesn't exist
    Base.metadata.create_all(bind=engine, tables=[TrustedDevice.__table__])
    print("Ensured trusted_devices table exists.")
    
    # Add trusted_device_id to sessions table
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='sessions' and column_name='trusted_device_id';
            """)).fetchone()
            
            if not result:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN trusted_device_id INTEGER REFERENCES trusted_devices(id) ON DELETE CASCADE;"))
                print("Added trusted_device_id column to sessions.")
            else:
                print("trusted_device_id column already exists in sessions.")
                
            conn.commit()
        except Exception as e:
            print(f"Error during ALTER TABLE: {e}")
            conn.rollback()
            
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
