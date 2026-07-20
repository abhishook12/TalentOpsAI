import os
import time
from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.models import auth_models, models, campaigns, system_settings

def run_migration():
    # Use autocommit to avoid long transactions blocking
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("Starting tenant isolation batch migration...")
        
        # Get admin user ID
        res = conn.execute(text("SELECT id FROM users WHERE email = 'admin@talentops.com'"))
        admin_row = res.first()
        if not admin_row:
            print("No admin user found! Aborting.")
            return
            
        admin_id = admin_row[0]
        print(f"Assigning existing global data to Admin User ID: {admin_id}")

        tables_to_isolate = [
            "campaigns", "companies", "vendors", 
            "email_signatures", "email_templates", "upload_jobs", 
            "smart_import_jobs", "campaign_drafts", "recruiters"
        ]

        for table in tables_to_isolate:
            print(f"\n--- Processing table: {table} ---")
            
            # Add user_id column
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"))
                print(f"Added user_id column to {table}")
            except Exception as e:
                print(f"Error adding user_id to {table} (might already exist): {e}")
                
            # Assign existing records to admin_id IN BATCHES
            batch_size = 10000
            total_updated = 0
            while True:
                try:
                    # postgresql UPDATE with LIMIT requires a subquery
                    if table == 'recruiters':
                        pk = 'recruiter_id'
                    elif table == 'companies':
                        pk = 'company_id'
                    elif table == 'vendors':
                        pk = 'vendor_id'
                    elif table == 'campaigns':
                        pk = 'campaign_id'
                    elif table == 'email_signatures':
                        pk = 'signature_id'
                    elif table == 'email_templates':
                        pk = 'template_id'
                    elif table == 'upload_jobs':
                        pk = 'job_id'
                    elif table == 'smart_import_jobs':
                        pk = 'job_id'
                    elif table == 'campaign_drafts':
                        pk = 'draft_id'
                    else:
                        pk = 'id'
                        
                    query = f"""
                    UPDATE {table} SET user_id = :admin_id 
                    WHERE {pk} IN (
                        SELECT {pk} FROM {table} WHERE user_id IS NULL LIMIT {batch_size}
                    )
                    """
                    result = conn.execute(text(query), {"admin_id": admin_id})
                    updated_in_batch = result.rowcount
                    
                    if updated_in_batch == 0:
                        print(f"Finished updating {table}. Total updated: {total_updated}")
                        break
                        
                    total_updated += updated_in_batch
                    print(f"Updated {updated_in_batch} rows in {table}... (Total: {total_updated})")
                    time.sleep(0.1) # Small pause to let pooler breathe
                except Exception as e:
                    print(f"Error updating user_id in {table}: {e}")
                    break

        print("\nMigration complete!")

if __name__ == "__main__":
    run_migration()
