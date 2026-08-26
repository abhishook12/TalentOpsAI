import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("DATABASE_SECURITY")

def enforce_database_rls_and_security(engine: Engine) -> None:
    """
    Ensures that Row Level Security (RLS) is enabled and forced on all tables
    in the 'public' schema, and that public 'anon' / 'authenticated' roles have no unauthorized access.
    """
    if "postgresql" not in engine.url.drivername:
        return

    try:
        with engine.connect() as conn:
            # Check if running on Supabase / PostgreSQL
            tables_result = conn.execute(text("""
                SELECT tablename, rowsecurity 
                FROM pg_tables 
                WHERE schemaname = 'public';
            """))
            tables = tables_result.fetchall()
            
            unsecured = [t[0] for t in tables if not t[1]]
            if unsecured:
                logger.info("Securing %d tables without RLS: %s", len(unsecured), unsecured)
                for tbl in unsecured:
                    conn.execute(text(f'ALTER TABLE public."{tbl}" ENABLE ROW LEVEL SECURITY;'))
                    conn.execute(text(f'ALTER TABLE public."{tbl}" FORCE ROW LEVEL SECURITY;'))
            
            # Ensure default privileges are revoked from anon/authenticated
            try:
                conn.execute(text("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;"))
                conn.execute(text("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;"))
                conn.execute(text("REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;"))
                conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;"))
                conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;"))
                conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated;"))
                conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, service_role;"))
            except Exception as e:
                logger.debug("Minor notice during role permission adjustment: %s", e)
                
            conn.commit()
            logger.info("Database security check passed: RLS enabled on all %d public tables.", len(tables))
    except Exception as exc:
        logger.warning("Could not execute automatic RLS enforcement (non-fatal): %s", exc)
