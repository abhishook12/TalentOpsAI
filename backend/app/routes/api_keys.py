"""
API Key Management Routes
Allows users to create, list, and revoke API keys for external/headless API access.
"""
import hashlib
import secrets
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.auth_service import get_current_user_from_request, require_admin
from ..models.auth_models import APIKey, User

logger = logging.getLogger("api_keys")

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str = "Default API Key"

class APIKeyResponse(BaseModel):
    id: int
    name: Optional[str]
    key_prefix: str
    created_at: str
    is_active: bool

class CreateAPIKeyResponse(BaseModel):
    id: int
    name: Optional[str]
    api_key: str  # Only returned on creation
    key_prefix: str
    created_at: str
    message: str


@router.post("", response_model=CreateAPIKeyResponse)
def create_api_key(
    payload: CreateAPIKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Create a new API key. The full key is only shown once."""
    # Limit: max 5 active keys per user
    active_count = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()
    if active_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 active API keys allowed. Revoke an existing key first."
        )
    
    # Generate a secure random key with prefix
    raw_key = f"top_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=payload.name,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"API key created: {api_key.id} for user {current_user.id}")
    
    return CreateAPIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        api_key=raw_key,
        key_prefix=raw_key[:12] + "...",
        created_at=api_key.created_at.isoformat() if api_key.created_at else datetime.now(timezone.utc).isoformat(),
        message="Save this key securely. It will not be shown again."
    )


@router.get("", response_model=List[APIKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """List all API keys for the current user (key values are not shown)."""
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(APIKey.created_at.desc()).all()
    
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_hash[:8] + "...",
            created_at=k.created_at.isoformat() if k.created_at else "",
            is_active=k.is_active
        )
        for k in keys
    ]


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Revoke (deactivate) an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    
    # Clear from auth cache
    from ..services.auth_service import _AUTH_CACHE
    keys_to_remove = [k for k in _AUTH_CACHE if k.startswith("apikey:")]
    for k in keys_to_remove:
        del _AUTH_CACHE[k]
    
    logger.info(f"API key {key_id} revoked by user {current_user.id}")
    return {"message": "API key revoked successfully", "id": key_id}


@router.get("/usage")
def api_key_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get API usage information."""
    active_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()
    
    return {
        "active_keys": active_keys,
        "max_keys": 5,
        "auth_methods": [
            {"method": "X-API-Key header", "example": "X-API-Key: top_xxxxx"},
            {"method": "Bearer token", "example": "Authorization: Bearer top_xxxxx"}
        ],
        "available_endpoints": [
            {"path": "/api/enrichment/enrich-profile", "method": "POST", "description": "Enrich a single profile"},
            {"path": "/api/enrichment/batch-enrich", "method": "POST", "description": "Batch enrich up to 50 profiles"},
            {"path": "/api/enrichment/company-tech/{domain}", "method": "GET", "description": "Company tech stack detection"},
            {"path": "/recruiters/search", "method": "GET", "description": "Search recruiter database"}
        ]
    }
