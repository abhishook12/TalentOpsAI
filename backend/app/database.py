from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/talentops")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # detects dead connections before using them
    pool_recycle=300,         # recycle connections every 5 mins
    pool_size=2,              # keep small pool for free-tier instances
    max_overflow=3,           # allow small burst under load
    pool_timeout=15,          # fail fast instead of hanging too long on pool wait
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
