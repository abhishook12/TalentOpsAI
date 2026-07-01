from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = "sqlite:///./dev.db"
raw_database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
# For production you can set DATABASE_URL or SUPABASE_DATABASE_URL in the environment; SQLite is used for local development.
if raw_database_url:
    DATABASE_URL = raw_database_url
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")


connect_args = {}
if DATABASE_URL.startswith("postgresql"):
    connect_args = {
        "connect_timeout": 10,
        "prepare_threshold": None
    }
else:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_use_lifo=True,
    connect_args=connect_args
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
