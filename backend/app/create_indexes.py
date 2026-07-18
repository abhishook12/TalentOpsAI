import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def resolve_database_url():
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url

    return None

def create_performance_indexes():
    db_url = resolve_database_url()
    if not db_url:
        print("DATABASE_URL not found in environment or backend/.env")
        return

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    print("Connecting to DB to install performance indexes...")
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        # 1. Enable pg_trgm extension for fast string matching
        print("Enabling pg_trgm extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        
        # 2. Standard location and specialization indexes
        print("Creating location and specialization indexes...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_location ON recruiters (location)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_location ON companies (location)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_specialization ON recruiters (specialization)"))
        
        # 3. Trigram GIN indexes for fast fuzzy searching / ILIKE matching
        print("Creating GIN trigram indexes for name and company search...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_trgm_name ON recruiters USING gin (recruiter_name gin_trgm_ops)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_companies_trgm_name ON companies USING gin (company_name gin_trgm_ops)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_trgm_spec ON recruiters USING gin (specialization gin_trgm_ops)"))
        
        # 4. Indexes for filtering and sorting
        print("Creating indexes for filtering and sorting...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_is_active ON recruiters (is_active)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_created_at ON recruiters (created_at DESC NULLS LAST)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_state ON recruiters (state)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_company_id ON recruiters (company_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_completeness_score ON recruiters (completeness_score DESC NULLS LAST)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_recruiters_data_source ON recruiters (data_source)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_page_visits_visited_at ON page_visits (visited_at DESC)"))

        # 5. Campaign engine hot paths: SSE progress GROUP BY, bridge task polling, timeout sweep
        print("Creating campaign engine indexes...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_campaign_recruiters_campaign_status ON campaign_recruiters (campaign_id, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_campaign_log ON email_logs (campaign_id, log_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_logs_bridge_pending ON email_logs (status, sent_via, sending_at)"))

        print("All indexes created successfully!")

if __name__ == "__main__":
    create_performance_indexes()
