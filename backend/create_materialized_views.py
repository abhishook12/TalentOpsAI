from sqlalchemy import text
from app.database import engine

def create_views():
    with engine.begin() as conn:
        print("Creating materialized view for state company counts...")
        conn.execute(text("""
            DROP MATERIALIZED VIEW IF EXISTS mv_state_company_counts;
            CREATE MATERIALIZED VIEW mv_state_company_counts AS
            SELECT COALESCE(c.state, r.state) as state, COUNT(DISTINCT c.company_id) as count 
            FROM companies c
            LEFT JOIN recruiters r ON r.company_id = c.company_id
            WHERE COALESCE(c.state, r.state) IS NOT NULL 
            GROUP BY COALESCE(c.state, r.state);
        """))
        
        # Create a unique index to allow CONCURRENTLY refreshing
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_state ON mv_state_company_counts (state);"))

        print("Creating materialized view for recruiters by state...")
        conn.execute(text("""
            DROP MATERIALIZED VIEW IF EXISTS mv_recruiters_by_state;
            CREATE MATERIALIZED VIEW mv_recruiters_by_state AS
            SELECT state, COUNT(recruiter_id) as count
            FROM recruiters
            WHERE state IS NOT NULL AND state != ''
            GROUP BY state;
        """))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_rec_state ON mv_recruiters_by_state (state);"))

        print("Materialized views created successfully.")

if __name__ == "__main__":
    create_views()
