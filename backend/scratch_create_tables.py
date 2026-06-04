from sqlalchemy import create_engine
from app.models.models import Base

db_url = "postgresql+psycopg://neondb_owner:npg_WoluYq6F7NMp@ep-soft-term-aqxur4j2-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(db_url)
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done!")
