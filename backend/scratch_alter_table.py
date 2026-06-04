from sqlalchemy import create_engine, text
db_url = "postgresql+psycopg://neondb_owner:npg_WoluYq6F7NMp@ep-soft-term-aqxur4j2-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(db_url)
with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE recruiters ADD COLUMN title VARCHAR(150)"))
        print("recruiters updated.")
    except Exception as e:
        print(f"recruiters: {e}")
    try:
        conn.execute(text("ALTER TABLE staging_recruiters ADD COLUMN title VARCHAR(150)"))
        print("staging_recruiters updated.")
    except Exception as e:
        print(f"staging_recruiters: {e}")
print("Done!")
