import sqlalchemy
from pathlib import Path

env_file = Path('backend/.env')
dsn = [l.split('=')[1].strip().strip('"').strip("'").replace(':6543', ':5432') for l in env_file.read_text().splitlines() if l.startswith('DATABASE_URL')][0]

engine = sqlalchemy.create_engine(dsn)

with engine.connect() as conn:
    discovery = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM recruiters WHERE data_source = 'discovery_worker'")).scalar()
    ingestion = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM companies WHERE data_source = 'file_ingestion'")).scalar()
    enhanced = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM recruiters WHERE phone IS NOT NULL OR email IS NOT NULL")).scalar()

print(f"Discovery Worker Additions: {discovery}")
print(f"File Ingestion Additions: {ingestion}")
print(f"Total Enriched Profiles: {enhanced}")
