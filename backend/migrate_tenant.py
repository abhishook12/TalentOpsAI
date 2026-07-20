import os
from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.models import auth_models, models, campaigns, system_settings

# Create new tables (UserOutlookAccount, UserPreference)
Base.metadata.create_all(bind=engine)

def run_migration():
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("Starting tenant isolation migration...")
        
        # Get admin user ID
        res = conn.execute(text("SELECT id FROM users WHERE email = 'admin@talentops.com'"))
        admin_row = res.first()
        if not admin_row:
            print("No admin user found! Aborting.")
            return
            
        admin_id = admin_row[0]
        print(f"Assigning existing global data to Admin User ID: {admin_id}")

        # 1. Expand User Profile Fields
        user_cols = [
            "job_title VARCHAR(150)", "department VARCHAR(150)", "phone VARCHAR(50)", 
            "mobile VARCHAR(50)", "work_email VARCHAR(150)", "alt_email VARCHAR(150)", 
            "timezone VARCHAR(100) DEFAULT 'UTC'", "address VARCHAR(255)", 
            "linkedin_url VARCHAR(255)", "website VARCHAR(255)", "resume_url VARCHAR(500)",
            "default_sender_id INTEGER", "default_reply_to VARCHAR(150)", "signature_html TEXT"
        ]
        for col in user_cols:
            try:
                col_name = col.split()[0]
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col.replace(col_name, '', 1)}"))
                print(f"Added {col_name} to users")
            except Exception as e:
                print(f"Error adding {col}: {e}")

        # 2. Add user_id to Tables
        tables_to_isolate = [
            "campaigns", "recruiters", "companies", "vendors", 
            "email_signatures", "email_templates", "upload_jobs", 
            "smart_import_jobs", "campaign_drafts"
        ]

        for table in tables_to_isolate:
            print(f"Isolating table: {table}")
            
            # Add user_id column
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
            except Exception as e:
                print(f"Error adding user_id to {table}: {e}")
                
            # Assign existing records to admin_id
            try:
                conn.execute(text(f"UPDATE {table} SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_id})
            except Exception as e:
                print(f"Error updating user_id in {table}: {e}")

        # Fix CampaignDrafts user_email -> user_id
        try:
            conn.execute(text("ALTER TABLE campaign_drafts DROP COLUMN IF EXISTS user_email"))
        except Exception:
            pass
            
        # Fix EmailSignatures user_email -> user_id
        try:
            conn.execute(text("ALTER TABLE email_signatures DROP COLUMN IF EXISTS user_email"))
        except Exception:
            pass

        print("Migration complete!")

if __name__ == "__main__":
    run_migration()
