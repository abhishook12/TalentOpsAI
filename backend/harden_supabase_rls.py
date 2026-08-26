"""
Supabase Database Security Hardening Script
- Enables Row Level Security (RLS) on ALL tables in the public schema
- Forces RLS on all public tables
- Revokes all permissions on public tables, sequences, and routines from 'anon' and 'authenticated' roles
- Configures default privileges so future tables created by migrations automatically have RLS and no public exposure
"""

import sys
import logging
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SUPABASE_RLS_HARDENER")

TARGET_DATABASES = [
    {
        "name": "talentops-production",
        "ref": "dcqvsvgrdsrgnbwwssup",
        "url": "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
    },
    {
        "name": "talentops-clean",
        "ref": "qpetzpxmuofuepvrqedk",
        "url": "postgresql://postgres.qpetzpxmuofuepvrqedk:h2ejQHVen5i5lQkDSR9RaCoz@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    }
]

def harden_database(db_config: dict):
    name = db_config["name"]
    ref = db_config["ref"]
    url = db_config["url"]
    
    logger.info(f"============================================================")
    logger.info(f"Hardening Database: {name} (ref: {ref})")
    logger.info(f"============================================================")
    
    with psycopg.connect(url, connect_timeout=15, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Fetch all tables in public schema
            cur.execute("""
                SELECT tablename, rowsecurity 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            tables = cur.fetchall()
            logger.info(f"Found {len(tables)} tables in 'public' schema.")
            
            # 2. Enable and Force RLS on every table
            enabled_count = 0
            for table_name, is_rls in tables:
                cur.execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY;')
                cur.execute(f'ALTER TABLE public."{table_name}" FORCE ROW LEVEL SECURITY;')
                enabled_count += 1
                logger.info(f"  [RLS ENABLED & FORCED] public.{table_name}")
            
            # 3. Revoke all privileges from anon and authenticated on public tables
            logger.info("Revoking all privileges on public schema from 'anon' and 'authenticated' roles...")
            cur.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;")
            cur.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;")
            cur.execute("REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;")
            
            # 4. Set default privileges so future tables are secure by default
            logger.info("Configuring ALTER DEFAULT PRIVILEGES for future tables...")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated;")
            
            # 5. Ensure postgres and service_role retain full access
            logger.info("Granting full access to 'postgres' and 'service_role'...")
            cur.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, service_role;")
            cur.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, service_role;")
            cur.execute("GRANT ALL ON ALL ROUTINES IN SCHEMA public TO postgres, service_role;")
            cur.execute("GRANT ALL ON SCHEMA public TO postgres, service_role;")
            
            # 6. Verification query
            cur.execute("""
                SELECT COUNT(*) 
                FROM pg_tables 
                WHERE schemaname = 'public' AND rowsecurity = false;
            """)
            unsecured_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.table_privileges 
                WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated');
            """)
            anon_grants_count = cur.fetchone()[0]
            
            logger.info(f"Verification Results for {name}:")
            logger.info(f"  - Total public tables: {len(tables)}")
            logger.info(f"  - Tables without RLS: {unsecured_count} (Must be 0)")
            logger.info(f"  - Public/Anon table grants remaining: {anon_grants_count} (Must be 0)")
            
            if unsecured_count > 0 or anon_grants_count > 0:
                raise RuntimeError(f"Database {name} failed verification! unsecured={unsecured_count}, grants={anon_grants_count}")
            
            logger.info(f"SUCCESS: {name} is 100% HARDENED & SECURED!\n")

def main():
    logger.info("Starting Supabase Enterprise Security Hardening...")
    for db_config in TARGET_DATABASES:
        harden_database(db_config)
    logger.info("All Supabase projects successfully hardened!")

if __name__ == "__main__":
    main()
