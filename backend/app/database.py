from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = "sqlite:///./dev.db"
raw_database_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
# For production you can set SUPABASE_DATABASE_URL or DATABASE_URL in the environment; SQLite is used for local development.
if raw_database_url:
    DATABASE_URL = raw_database_url
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # detects dead connections before using them
    pool_recycle=300,         # recycle connections every 5 mins
    pool_size=20,             # Max connections = 20
    max_overflow=10,          # limit overflows
    pool_timeout=30,          # fail fast instead of hanging too long on pool wait
    pool_use_lifo=True,       # re-use warm connections first
    connect_args={
        "connect_timeout": 10
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
