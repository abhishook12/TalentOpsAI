import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import engine
from sqlalchemy import text

create_sql = text("""
CREATE TABLE IF NOT EXISTS upload_jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    inserted_rows INTEGER DEFAULT 0,
    skipped_rows INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    errors TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_job_id ON upload_jobs(job_id);
""")

with engine.begin() as conn:
    conn.execute(create_sql)
print("Table created successfully using raw SQL.")
