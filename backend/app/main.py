import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS, IS_PRODUCTION
from app.routes import recruiters, companies, vendors, analytics, upload, admin, auth, actions, updates
from app.database import get_db, engine
from app.models import models
from app.create_indexes import create_performance_indexes

logging.basicConfig(
    level=logging.INFO if IS_PRODUCTION else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("talentops")

RUN_STARTUP_MIGRATIONS = os.getenv("RUN_STARTUP_MIGRATIONS", "false").lower() in ("1", "true", "yes")

if RUN_STARTUP_MIGRATIONS:
    models.Base.metadata.create_all(bind=engine)
    try:
        create_performance_indexes()
    except Exception as e:
        logger.warning("Error creating indexes at startup: %s", e)
else:
    logger.info("Skipping startup migrations/index creation (RUN_STARTUP_MIGRATIONS=false)")

try:
    from sqlalchemy.orm import Session as OrmSession
    with OrmSession(engine) as _db:
        try:
            _db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            _db.commit()
        except Exception:
            _db.rollback()
        admin.migrate_page_visits(_db)
except Exception as e:
    logger.warning("Migration warning: %s", e)

app = FastAPI(
    title="TalentOps AI",
    description="Recruitment Operations Intelligence Platform",
    version="1.1.0",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(recruiters.router, prefix="/recruiters", tags=["Recruiters"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(actions.router, prefix="/actions", tags=["Actions"])


@app.get("/")
def root():
    return {"message": "TalentOps AI is running", "docs": "/docs"}


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "degraded", "database": "disconnected", "detail": str(e)}
