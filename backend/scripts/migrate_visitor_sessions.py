import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
db = Session()

alter_statements = [
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS total_searches INTEGER DEFAULT 0;",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS total_clicks INTEGER DEFAULT 0;",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS anonymous_id VARCHAR(64);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS screen_size VARCHAR(50);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS timezone VARCHAR(100);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS referrer VARCHAR(500);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS user_agent VARCHAR(300);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS current_page VARCHAR(255);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS previous_page VARCHAR(255);",
    "ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Active';",
    "CREATE INDEX IF NOT EXISTS ix_visitor_sessions_anonymous_id ON visitor_sessions(anonymous_id);"
]

try:
    for stmt in alter_statements:
        print(f"Executing: {stmt}")
        db.execute(text(stmt))
    db.commit()
    print("Migration successful.")
except Exception as e:
    db.rollback()
    print(f"Migration failed: {e}")
