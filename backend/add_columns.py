import sys
sys.path.append("C:/TalentOpsAI/backend")
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE companies ADD COLUMN state VARCHAR(2);"))
        conn.execute(text("CREATE INDEX ix_companies_state ON companies (state);"))
        print("Added state to companies")
    except Exception as e:
        print(f"Error companies: {e}")
        
    try:
        conn.execute(text("ALTER TABLE recruiters ADD COLUMN state VARCHAR(2);"))
        conn.execute(text("CREATE INDEX ix_recruiters_state ON recruiters (state);"))
        print("Added state to recruiters")
    except Exception as e:
        print(f"Error recruiters: {e}")
    
    conn.commit()
