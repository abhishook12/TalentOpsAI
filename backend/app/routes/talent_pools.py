"""
TalentOpsAI - Custom Talent Pools & Tagging Engine
==================================================
Allows recruiters and sourcers to bookmark, categorize, and manage candidates
into custom organized talent pools directly from Search and Directory.
"""

import os
import json
import uuid
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from ..services.recruiter_store import recruiter_store
from ..services.auth_service import get_current_user_from_request

router = APIRouter(prefix="/talent-pools", tags=["Talent Pools"], dependencies=[Depends(get_current_user_from_request)])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
POOLS_FILE = os.path.join(DATA_DIR, "talent_pools_store.json")


def _load_pools() -> List[Dict[str, Any]]:
    if not os.path.exists(POOLS_FILE):
        return []
    try:
        with open(POOLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_pools(pools: List[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(pools, f, indent=2)


class CreatePoolPayload(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    target_role: Optional[str] = ""


class AddRecruitersPayload(BaseModel):
    recruiter_ids: List[int]


@router.get("")
def list_talent_pools(current_user = Depends(get_current_user_from_request)):
    """List all custom talent pools with member counts."""
    pools = [p for p in _load_pools() if p.get("user_id") == current_user.id]
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "tags": p.get("tags", []),
            "target_role": p.get("target_role", ""),
            "total_members": len(p.get("recruiter_ids", [])),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at")
        }
        for p in pools
    ]


@router.post("")
def create_talent_pool(payload: CreatePoolPayload, current_user = Depends(get_current_user_from_request)):
    """Create a new named talent pool."""
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Talent pool name is required")

    pools = _load_pools()
    new_pool = {
        "id": str(uuid.uuid4())[:8],
        "user_id": current_user.id,
        "name": payload.name.strip(),
        "description": payload.description or "",
        "tags": payload.tags or [],
        "target_role": payload.target_role or "",
        "recruiter_ids": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    pools.insert(0, new_pool)
    _save_pools(pools)
    return new_pool


@router.get("/{pool_id}")
def get_talent_pool_details(pool_id: str, current_user = Depends(get_current_user_from_request)):
    """Get full talent pool metadata and resolved recruiter records."""
    pools = _load_pools()
    pool = next((p for p in pools if p["id"] == pool_id and p.get("user_id") == current_user.id), None)
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    recruiter_ids = pool.get("recruiter_ids", [])
    resolved_recruiters = []
    if recruiter_ids:
        conn = recruiter_store._ensure_loaded()
        if conn:
            id_list_str = ",".join(str(i) for i in recruiter_ids)
            try:
                query = f"SELECT * FROM recruiters WHERE id IN ({id_list_str})"
                resolved_recruiters = conn.execute(query).df().to_dict(orient="records")
            except Exception:
                pass

    return {
        "pool": pool,
        "total_members": len(recruiter_ids),
        "recruiters": resolved_recruiters
    }


@router.post("/{pool_id}/add-recruiters")
def add_recruiters_to_pool(pool_id: str, payload: AddRecruitersPayload, current_user = Depends(get_current_user_from_request)):
    """Add a list of recruiter IDs to a talent pool."""
    pools = _load_pools()
    pool = next((p for p in pools if p["id"] == pool_id and p.get("user_id") == current_user.id), None)
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    existing_ids = set(pool.get("recruiter_ids", []))
    new_count = 0
    for rid in payload.recruiter_ids:
        if rid not in existing_ids:
            existing_ids.add(rid)
            new_count += 1

    pool["recruiter_ids"] = list(existing_ids)
    pool["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_pools(pools)

    return {
        "pool_id": pool_id,
        "added_count": new_count,
        "total_members": len(pool["recruiter_ids"])
    }


@router.delete("/{pool_id}/recruiters/{recruiter_id}")
def remove_recruiter_from_pool(pool_id: str, recruiter_id: int, current_user = Depends(get_current_user_from_request)):
    """Remove a single recruiter from a talent pool."""
    pools = _load_pools()
    pool = next((p for p in pools if p["id"] == pool_id and p.get("user_id") == current_user.id), None)
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")

    recruiter_ids = pool.get("recruiter_ids", [])
    if recruiter_id in recruiter_ids:
        recruiter_ids.remove(recruiter_id)
        pool["recruiter_ids"] = recruiter_ids
        pool["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save_pools(pools)

    return {"pool_id": pool_id, "removed_id": recruiter_id, "total_members": len(recruiter_ids)}


@router.delete("/{pool_id}")
def delete_talent_pool(pool_id: str, current_user = Depends(get_current_user_from_request)):
    """Delete a talent pool."""
    pools = _load_pools()
    pool = next((p for p in pools if p["id"] == pool_id and p.get("user_id") == current_user.id), None)
    if not pool:
        raise HTTPException(status_code=404, detail="Talent pool not found")
    pools = [p for p in pools if p["id"] != pool_id]
    _save_pools(pools)
    return {"message": "Talent pool deleted", "deleted_id": pool_id}
