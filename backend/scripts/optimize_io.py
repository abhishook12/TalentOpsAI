import psycopg

def optimize_db():
    remote_url = 'postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    
    # autocommit=True is required for VACUUM and CREATE INDEX CONCURRENTLY
    with psycopg.connect(remote_url, autocommit=True, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            # Disable statement timeout so these long operations don't get killed
            cur.execute("SET statement_timeout = 0;")
            
            print("=== STARTING DATABASE IO OPTIMIZATION ===")
            
            print("1. Creating indexes (if not exists)...")
            cur.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recruiters_company_id ON recruiters(company_id);
            """)
            print("   -> idx_recruiters_company_id created.")
            
            cur.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recruiters_email ON recruiters(email);
            """)
            print("   -> idx_recruiters_email created.")
            
            cur.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companies_company_name ON companies(company_name);
            """)
            print("   -> idx_companies_company_name created.")
            
            print("2. Running deep VACUUM ANALYZE on recruiters table...")
            cur.execute("VACUUM ANALYZE recruiters;")
            print("   -> recruiters vacuumed successfully.")
            
            print("3. Running deep VACUUM ANALYZE on companies table...")
            cur.execute("VACUUM ANALYZE companies;")
            print("   -> companies vacuumed successfully.")
            
            print("=== OPTIMIZATION COMPLETE ===")

if __name__ == "__main__":
    optimize_db()
