"""
Performance Indexes Migration Script
Adds missing indexes on high-traffic columns to eliminate full table scans on 284k+ rows.
Uses CREATE INDEX CONCURRENTLY to avoid locking the table during creation.
"""
import sqlalchemy
import sys
import time

DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

INDEXES = [
    ("ix_recruiters_created_at", "recruiters", "created_at"),
    ("ix_recruiters_updated_at", "recruiters", "updated_at"),
    ("ix_recruiters_last_scan_at", "recruiters", "last_scan_at"),
    ("ix_companies_company_name", "companies", "company_name"),
    ("ix_companies_created_at", "companies", "created_at"),
    ("ix_companies_updated_at", "companies", "updated_at"),
]

def main():
    engine = sqlalchemy.create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        # Check existing indexes
        existing = conn.execute(sqlalchemy.text(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )).fetchall()
        existing_names = {r[0] for r in existing}
        
        for idx_name, table, column in INDEXES:
            if idx_name in existing_names:
                print(f"  SKIP {idx_name} (already exists)")
                continue
            
            print(f"  CREATE INDEX {idx_name} ON {table}({column})...")
            start = time.time()
            try:
                conn.execute(sqlalchemy.text(
                    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_name} ON {table} ({column})"
                ))
                elapsed = time.time() - start
                print(f"  DONE {idx_name} ({elapsed:.1f}s)")
            except Exception as e:
                print(f"  FALLBACK for {idx_name}: {e}")
                # Fallback to non-concurrent if CONCURRENTLY fails (e.g. inside transaction)
                try:
                    conn.execute(sqlalchemy.text(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
                    ))
                    print(f"  DONE {idx_name} (non-concurrent fallback)")
                except Exception as e2:
                    print(f"  FAILED {idx_name}: {e2}")

        # Verify
        print("\n--- VERIFICATION ---")
        result = conn.execute(sqlalchemy.text(
            "SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'ix_%' ORDER BY tablename, indexname"
        )).fetchall()
        for r in result:
            print(f"  {r[1]}.{r[0]}")
        
        print(f"\nTotal indexes: {len(result)}")

if __name__ == "__main__":
    main()
