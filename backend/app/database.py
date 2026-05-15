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
    pool_size=5,              # max 5 persistent connections
    max_overflow=2,           # allow 2 extra under load
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
