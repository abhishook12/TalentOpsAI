from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Hard limits (75% of Supabase Free Tier)
# DB Free Tier = 500 MB -> 75% = 375 MB
DB_SIZE_LIMIT_BYTES = 375 * 1024 * 1024

# File Storage Free Tier = 1 GB -> 75% = 750 MB
FILE_SIZE_LIMIT_BYTES = 750 * 1024 * 1024

def get_database_size(session: Session) -> int:
    """Returns database size in bytes"""
    try:
        # Check if we are using postgres
        bind_url = str(session.get_bind().url)
        if "postgresql" not in bind_url:
            # For SQLite local dev, just return 0 to bypass the check
            return 0
            
        result = session.execute(text("SELECT pg_database_size(current_database())")).scalar()
        return int(result) if result else 0
    except Exception as e:
        logger.error(f"Failed to query pg_database_size: {e}")
        # Fallback for SQLite local dev or if permission denied
        return 0

def get_file_storage_size(db: Session) -> int:
    """Returns the total size of all objects in Supabase storage in bytes."""
    try:
        # Supabase stores file metadata in the storage.objects table
        # We extract the 'size' from the metadata JSONB column
        query = "SELECT COALESCE(SUM((metadata->>'size')::bigint), 0) FROM storage.objects"
        result = db.execute(text(query)).scalar()
        return int(result) if result else 0
    except Exception as e:
        logger.error(f"Failed to query storage.objects: {e}")
        return 0

def check_database_storage_limit(db: Session):
    """Raises a 403 HTTPException if the database is over the 75% limit."""
    db_size = get_database_size(db)
    if db_size >= DB_SIZE_LIMIT_BYTES:
        raise HTTPException(
            status_code=403,
            detail=f"Storage Kill-Switch Activated: Database capacity is over the 75% safety limit ({db_size / 1024 / 1024:.2f} MB / 375.0 MB). Please clear space."
        )

def check_file_storage_limit(db: Session):
    """Raises a 403 HTTPException if the file storage is over the 75% limit."""
    file_size = get_file_storage_size(db)
    if file_size >= FILE_SIZE_LIMIT_BYTES:
        raise HTTPException(
            status_code=403,
            detail=f"Storage Kill-Switch Activated: File Storage is over the 75% safety limit ({file_size / 1024 / 1024:.2f} MB / 750.0 MB). Please delete old files."
        )

def get_storage_health(db: Session) -> dict:
    """Returns a health report of current storage usage vs limits."""
    db_size = get_database_size(db)
    file_size = get_file_storage_size(db)
    
    return {
        "database_storage": {
            "used_bytes": db_size,
            "limit_bytes": DB_SIZE_LIMIT_BYTES,
            "percentage": round((db_size / DB_SIZE_LIMIT_BYTES) * 100, 2) if DB_SIZE_LIMIT_BYTES else 0,
            "is_blocked": db_size >= DB_SIZE_LIMIT_BYTES
        },
        "file_storage": {
            "used_bytes": file_size,
            "limit_bytes": FILE_SIZE_LIMIT_BYTES,
            "percentage": round((file_size / FILE_SIZE_LIMIT_BYTES) * 100, 2) if FILE_SIZE_LIMIT_BYTES else 0,
            "is_blocked": file_size >= FILE_SIZE_LIMIT_BYTES
        }
    }
