from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()

tables = ['recruiters', 'companies', 'upload_jobs']
for t in tables:
    cols = db.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{t}'")).fetchall()
    print(f"Table {t}:")
    for c in cols:
        print(f"  {c[0]}: {c[1]}")
