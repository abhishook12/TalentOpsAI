import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS, IS_PRODUCTION, ENV as APP_ENV
from app.routes import recruiters, companies, vendors, analytics, upload, admin, auth, actions, updates, import_engine
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
            
        # Ensure any missing tables (like smart_import_jobs) are created
        models.Base.metadata.create_all(bind=engine)
        
        admin.migrate_page_visits(_db)
        try:
            existing_cols = set(
                row[0]
                for row in _db.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'recruiters'
                """)).all()
            )
            recruit_adds = []
            if "source_job_id" not in existing_cols:
                recruit_adds.append("ADD COLUMN source_job_id VARCHAR(36)")
            if "raw_data" not in existing_cols:
                recruit_adds.append("ADD COLUMN raw_data TEXT")
            if "metadata_json" not in existing_cols:
                recruit_adds.append("ADD COLUMN metadata_json TEXT")
            if "tags" not in existing_cols:
                recruit_adds.append("ADD COLUMN tags TEXT")
            if "title" not in existing_cols:
                recruit_adds.append("ADD COLUMN title VARCHAR(150)")
            if recruit_adds:
                _db.execute(text(f"ALTER TABLE recruiters {', '.join(recruit_adds)}"))
                _db.commit()

            existing_company_cols = set(
                row[0]
                for row in _db.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'companies'
                """)).all()
            )
            company_adds = []
            if "source_job_id" not in existing_company_cols:
                company_adds.append("ADD COLUMN source_job_id VARCHAR(36)")
            if "raw_data" not in existing_company_cols:
                company_adds.append("ADD COLUMN raw_data TEXT")
            if "metadata_json" not in existing_company_cols:
                company_adds.append("ADD COLUMN metadata_json TEXT")
            if "tags" not in existing_company_cols:
                company_adds.append("ADD COLUMN tags TEXT")
            if company_adds:
                _db.execute(text(f"ALTER TABLE companies {', '.join(company_adds)}"))
                _db.commit()

            def _ensure_columns(table_name: str, columns: dict[str, str]) -> None:
                existing = set(
                    row[0]
                    for row in _db.execute(text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                    """), {"table_name": table_name}).all()
                )
                adds = [f"ADD COLUMN {column} {definition}" for column, definition in columns.items() if column not in existing]
                if adds:
                    _db.execute(text(f"ALTER TABLE {table_name} {', '.join(adds)}"))
                    _db.commit()

            _ensure_columns("upload_jobs", {
                "current_step": "VARCHAR(100)",
                "progress_percent": "INTEGER DEFAULT 0",
                "file_size_bytes": "INTEGER DEFAULT 0",
                "valid_rows": "INTEGER DEFAULT 0",
                "warning_rows": "INTEGER DEFAULT 0",
                "duplicate_rows": "INTEGER DEFAULT 0",
                "possible_duplicate_rows": "INTEGER DEFAULT 0",
                "enriched_rows": "INTEGER DEFAULT 0",
                "failed_rows": "INTEGER DEFAULT 0",
                "error_message": "TEXT",
                "last_heartbeat_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT NOW()",
            })
            _ensure_columns("smart_import_jobs", {
                "filename": "VARCHAR(255)",
                "status": "VARCHAR(50) DEFAULT 'mapping'",
                "current_step": "VARCHAR(100)",
                "progress_percent": "INTEGER DEFAULT 0",
                "file_size_bytes": "INTEGER DEFAULT 0",
                "total_rows": "INTEGER DEFAULT 0",
                "processed_rows": "INTEGER DEFAULT 0",
                "valid_rows": "INTEGER DEFAULT 0",
                "warning_rows": "INTEGER DEFAULT 0",
                "error_rows": "INTEGER DEFAULT 0",
                "duplicate_rows": "INTEGER DEFAULT 0",
                "possible_duplicate_rows": "INTEGER DEFAULT 0",
                "enriched_rows": "INTEGER DEFAULT 0",
                "inserted_rows": "INTEGER DEFAULT 0",
                "skipped_rows": "INTEGER DEFAULT 0",
                "failed_rows": "INTEGER DEFAULT 0",
                "started_at": "TIMESTAMP DEFAULT NOW()",
                "completed_at": "TIMESTAMP",
                "error_message": "TEXT",
                "last_heartbeat_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT NOW()",
                "user_email": "VARCHAR(150)",
                "column_mapping": "TEXT",
                "detected_format": "VARCHAR(100)",
                "format_confidence": "INTEGER DEFAULT 100",
            })
            _ensure_columns("smart_import_rows", {
                "job_id": "VARCHAR(36)",
                "original_row_index": "INTEGER",
                "recruiter_name": "VARCHAR(255)",
                "email": "VARCHAR(255)",
                "phone": "VARCHAR(50)",
                "company_name": "VARCHAR(255)",
                "state": "VARCHAR(100)",
                "location": "VARCHAR(255)",
                "linkedin": "VARCHAR(255)",
                "title": "VARCHAR(255)",
                "specialization": "VARCHAR(255)",
                "notes": "TEXT",
                "raw_json": "TEXT",
                "status": "VARCHAR(50) DEFAULT 'Ready'",
                "validation_issues": "TEXT",
            })
        except Exception as e:
            logger.warning("Import batch column migration warning: %s", e)
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

from fastapi.responses import JSONResponse
from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
import traceback

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred.", "type": "database_error"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred.", "type": "internal_error"}
    )

app.include_router(recruiters.router, prefix="/recruiters", tags=["Recruiters"])
app.include_router(import_engine.router, prefix="/api", tags=["Smart Import"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(actions.router, prefix="/actions", tags=["Actions"])
app.include_router(updates.router)


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
        return {"status": "healthy", "database": "connected", "environment": APP_ENV}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "degraded", "database": "disconnected", "environment": APP_ENV, "detail": str(e)}
