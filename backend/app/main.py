import logging
import os
import time
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from .config import CORS_ORIGINS, IS_PRODUCTION, ENV as APP_ENV
from .routes import recruiters, companies, vendors, analytics, admin, auth, actions, updates, ai, campaigns, harvester, users
from .database import get_db, engine
from .models import models, auth_models
from .create_indexes import create_performance_indexes

logging.basicConfig(
    level=logging.INFO if IS_PRODUCTION else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("talentops")

RUN_STARTUP_MIGRATIONS = os.getenv("RUN_STARTUP_MIGRATIONS", "false").lower() in ("1", "true", "yes")

if RUN_STARTUP_MIGRATIONS:
    try:
        models.Base.metadata.create_all(bind=engine)
        try:
            create_performance_indexes()
        except Exception as e:
            logger.warning("Error creating indexes at startup: %s", e)
    except Exception as e:
        logger.warning("Startup migrations skipped due to database error: %s", e)
else:
    logger.info("Skipping startup migrations/index creation (RUN_STARTUP_MIGRATIONS=false)")

if RUN_STARTUP_MIGRATIONS:
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
            
            try:
                from .seed_roles import seed_roles_and_permissions
                seed_roles_and_permissions(_db)
            except Exception as e:
                logger.error("Error seeding roles: %s", e)

            try:
                from .services.backup_service import start_backup_service
                start_backup_service(interval_hours=24)
            except Exception as e:
                logger.error("Error starting backup service: %s", e)

            admin.migrate_page_visits(_db)
            try:
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

                _ensure_columns("recruiters", {
                    "source_job_id": "VARCHAR(36)",
                    "raw_data": "TEXT",
                    "metadata_json": "TEXT",
                    "tags": "TEXT",
                    "title": "VARCHAR(150)",
                    "email2": "VARCHAR(150)",
                    "phone2": "VARCHAR(30)",
                    "email3": "VARCHAR(150)",
                    "phone3": "VARCHAR(30)",
                    "email4": "VARCHAR(150)",
                    "phone4": "VARCHAR(30)",
                    "alternate_emails": "TEXT",
                    "alternate_phones": "TEXT",
                    "review_reason": "TEXT",
                    "linkedin": "VARCHAR(255)",
                    "notes": "TEXT",
                    "location_confidence": "VARCHAR(20) DEFAULT 'high'",
                    "completeness_score": "INTEGER DEFAULT 0",
                    "needs_review": "BOOLEAN DEFAULT FALSE",
                    "is_active": "BOOLEAN DEFAULT TRUE",
                    "data_source": "VARCHAR(100) DEFAULT 'manual'",
                    "trust_score": "INTEGER DEFAULT 100",
                    "state_source": "VARCHAR(100)",
                    "state_confidence": "VARCHAR(20)",
                    "state_reason": "TEXT",
                    "last_scan_at": "TIMESTAMP",
                })

                _ensure_columns("companies", {
                    "source_job_id": "VARCHAR(36)",
                    "raw_data": "TEXT",
                    "metadata_json": "TEXT",
                    "tags": "TEXT",
                    "normalized_company_name": "VARCHAR(255)",
                    "state": "VARCHAR(2)",
                    "trust_score": "INTEGER DEFAULT 100",
                    "data_source": "VARCHAR(100) DEFAULT 'manual'",
                })

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

from .resource_lockdown import is_locked_down, get_lockdown_reason, check_system_limits

@app.middleware("http")
async def lockdown_middleware(request: Request, call_next):
    if request.method != "GET" or request.url.path.startswith("/ai"):
        if is_locked_down():
            return JSONResponse(
                status_code=503,
                content={"detail": f"System is in Emergency Lockdown: {get_lockdown_reason()}", "type": "lockdown"}
            )
    
    # Check limits on every POST/AI request
    if request.method != "GET" or request.url.path.startswith("/ai"):
        check_system_limits()
        
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    if process_time > 1.0:
        logger.warning(f"Slow request detected: {request.method} {request.url.path} took {process_time:.2f}s")
        
    return response

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

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
app.include_router(companies.router, prefix="/companies", tags=["Companies"])
app.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(actions.router, prefix="/actions", tags=["Actions"])
app.include_router(updates.router)
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(harvester.router, prefix="/api", tags=["Autonomous Spider"])
app.include_router(users.router, prefix="/users", tags=["Users"])


@app.get("/")
def root():
    return {"message": "TalentOps AI is running", "docs": "/docs"}


@app.get("/ping")
def ping():
    return {"status": "ok"}


from .routes import health
app.include_router(health.router, prefix="/health", tags=["System Health"])
