import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found")
    exit(1)

engine = create_engine(DATABASE_URL)

def add_column_safe(conn, table, column_def):
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
        print(f"Added {column_def} to {table}")
    except Exception as e:
        if "already exists" in str(e) or "Duplicate column name" in str(e):
            print(f"Column already exists: {column_def}")
        else:
            print(f"Error adding {column_def} to {table}: {e}")

with engine.begin() as conn:
    # TrustedDevice columns
    add_column_safe(conn, "trusted_devices", "device_type VARCHAR(100)")
    add_column_safe(conn, "trusted_devices", "browser_version VARCHAR(100)")
    add_column_safe(conn, "trusted_devices", "timezone VARCHAR(100)")
    add_column_safe(conn, "trusted_devices", "language VARCHAR(50)")
    add_column_safe(conn, "trusted_devices", "location VARCHAR(255)")
    add_column_safe(conn, "trusted_devices", "ip_address VARCHAR(60)")
    add_column_safe(conn, "trusted_devices", "login_attempts INTEGER DEFAULT 1")
    add_column_safe(conn, "trusted_devices", "risk_level VARCHAR(50) DEFAULT 'low'")
    add_column_safe(conn, "trusted_devices", "first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # AuditLog columns
    add_column_safe(conn, "audit_logs", "target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
    add_column_safe(conn, "audit_logs", "target_device_id INTEGER REFERENCES trusted_devices(id) ON DELETE SET NULL")
    add_column_safe(conn, "audit_logs", "reason VARCHAR(255)")
    add_column_safe(conn, "audit_logs", "status VARCHAR(50)")

print("Migration completed successfully.")
