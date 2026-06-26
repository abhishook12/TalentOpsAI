import os
import psycopg
from dotenv import load_dotenv

load_dotenv("C:/TalentOpsAI/backend/.env")
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+psycopg://", "postgresql://")

conn = psycopg.connect(DATABASE_URL, prepare_threshold=None)

queries = [
    # Create company_aliases
    """
    CREATE TABLE IF NOT EXISTS company_aliases (
        id SERIAL PRIMARY KEY,
        canonical_company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
        alias_name VARCHAR(255) NOT NULL,
        alias_type VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # Create company_email_patterns
    """
    CREATE TABLE IF NOT EXISTS company_email_patterns (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
        domain VARCHAR(255) NOT NULL,
        pattern VARCHAR(100) NOT NULL,
        verified_example_count INTEGER DEFAULT 0,
        match_percentage NUMERIC(5,2),
        confidence VARCHAR(20),
        source VARCHAR(50),
        last_verified_at TIMESTAMP,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # Create email_candidates
    """
    CREATE TABLE IF NOT EXISTS email_candidates (
        id SERIAL PRIMARY KEY,
        recruiter_id INTEGER REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
        candidate_email VARCHAR(255) NOT NULL,
        domain VARCHAR(255) NOT NULL,
        pattern VARCHAR(100),
        confidence_score INTEGER,
        status VARCHAR(50) DEFAULT 'generated',
        evidence TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verified_at TIMESTAMP,
        rejection_reason TEXT
    );
    """,
    # Add new fields to recruiters
    """
    ALTER TABLE recruiters
    ADD COLUMN IF NOT EXISTS email_status VARCHAR(50) DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS email_confidence INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS email_source VARCHAR(100),
    ADD COLUMN IF NOT EXISTS email_pattern_id INTEGER REFERENCES company_email_patterns(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS email_generated BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS email_last_checked_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS canonical_company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS historical_company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS company_domain_id INTEGER,
    ADD COLUMN IF NOT EXISTS raw_email_value VARCHAR(255),
    ADD COLUMN IF NOT EXISTS repair_reason TEXT;
    """
]

try:
    with conn.cursor() as cur:
        for q in queries:
            print("Executing DDL...")
            cur.execute(q)
    conn.commit()
    print("Schema migration completed successfully.")
except Exception as e:
    conn.rollback()
    print(f"Error executing schema migration: {e}")
finally:
    conn.close()
