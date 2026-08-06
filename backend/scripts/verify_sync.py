import sys
import time
import os
sys.path.append('C:/TalentOpsAI/backend')

from app.database import engine
from sqlalchemy import text
from app.services.sync_layer import sync_manager
from app.services.recruiter_store import recruiter_store

print("--- Verification 1: Insert ---")
with engine.begin() as conn:
    conn.execute(text("""
        INSERT INTO recruiters (recruiter_id, recruiter_name, email, is_active)
        VALUES (9999999, 'Test Sync Recruiter', 'sync@test.com', true)
        ON CONFLICT (recruiter_id) DO UPDATE SET recruiter_name = 'Test Sync Recruiter'
    """))
print("Inserted live record into Postgres.")

# Sync synchronously for testing
sync_manager._perform_sync()

# Verify
res = recruiter_store.get_by_id(9999999)
if res and res.get('recruiter_name') == 'Test Sync Recruiter':
    print("SUCCESS: Insert sync verified!")
else:
    print(f"FAILED: Recruiter not found or wrong data: {res}")

print("\n--- Verification 2: Update ---")
with engine.begin() as conn:
    conn.execute(text("""
        UPDATE recruiters SET recruiter_name = 'Test Sync Updated' WHERE recruiter_id = 9999999
    """))
print("Updated live record in Postgres.")

sync_manager._perform_sync()

res = recruiter_store.get_by_id(9999999)
if res and res.get('recruiter_name') == 'Test Sync Updated':
    print("SUCCESS: Update sync verified!")
else:
    print(f"FAILED: Recruiter not found or wrong data: {res}")

print("\n--- Verification 3: Delete ---")
with engine.begin() as conn:
    conn.execute(text("""
        DELETE FROM recruiters WHERE recruiter_id = 9999999
    """))
print("Deleted live record from Postgres.")

sync_manager._perform_sync()

res = recruiter_store.get_by_id(9999999)
if res is None:
    print("SUCCESS: Delete sync verified!")
else:
    print(f"FAILED: Recruiter still exists in Parquet: {res}")
