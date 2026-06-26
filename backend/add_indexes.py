import sys
from sqlalchemy import text
from app.database import engine

def main():
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_is_active ON companies(is_active);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recruiters_company_id ON recruiters(company_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recruiters_is_active ON recruiters(is_active);"))
        print("Indexes created successfully.")

if __name__ == "__main__":
    main()
