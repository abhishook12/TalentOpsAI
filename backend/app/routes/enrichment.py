"""
enrichment.py — REST API endpoints for Zero-Resource Multi-Source Enterprise Enrichment.
Provides real-time company tech-stack / ATS fingerprinting, hash identity & avatar resolution,
and waterfall candidate profile enrichment.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import Company, Recruiter
from ..models.auth_models import User
from ..routes.auth import get_current_user_from_request
from ..services.zero_resource_enricher import (
    TechStackFingerprinter,
    HashIdentityResolver,
    zero_resource_enricher,
    CATEGORY_RULES,
)
from ..services.parquet_writer import parquet_writer
from ..services.recruiter_store import recruiter_store

logger = logging.getLogger("talentops.enrichment_api")

router = APIRouter(prefix="/api/enrichment", tags=["Zero-Resource Multi-Source Enrichment"])


# ── Pydantic Request & Response Schemas ───────────────────────────────────────

class EnrichProfileRequest(BaseModel):
    recruiter_id: Optional[int] = Field(None, description="Optional ID of existing recruiter to enrich and persist")
    email: Optional[str] = Field(None, description="Candidate email address")
    name: Optional[str] = Field(None, description="Candidate full name")
    company_name: Optional[str] = Field(None, description="Candidate company name")
    domain: Optional[str] = Field(None, description="Explicit company domain if known (e.g. 'stripe.com')")


class BatchEnrichRequest(BaseModel):
    recruiter_ids: List[int] = Field(..., max_items=50, description="List of recruiter IDs to enrich in batch")


# ── REST API Endpoints ────────────────────────────────────────────────────────

@router.get("/company-tech/{domain}")
def get_company_tech_stack(
    domain: str,
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Passively fingerprints the authoritative DNS TXT/SPF and MX records for a company domain.
    Returns detected Applicant Tracking System (ATS), CRM, Mail Provider, and Infrastructure.
    """
    clean_dom = domain.strip().lower()
    intel = TechStackFingerprinter.fingerprint_domain(clean_dom)
    return {
        "success": True,
        "domain": clean_dom,
        "intelligence": intel,
    }


@router.post("/enrich-profile")
def enrich_single_profile(
    req: EnrichProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Executes zero-resource waterfall enrichment across:
    1. Authoritative DNS SPF/MX Firmographic Fingerprint (Greenhouse, Lever, Workday, Salesforce, etc.)
    2. Cryptographic Hash Identity & Avatar Resolution (Gravatar, Unavatar, High-Res Headshots)
    3. Persists enriched fields to PostgreSQL and DuckDB Parquet if recruiter_id is provided.
    """
    rec_obj: Optional[Recruiter] = None
    target_email = req.email
    target_name = req.name
    target_company = req.company_name
    target_domain = req.domain

    parquet_rec: Optional[Dict[str, Any]] = None

    # If recruiter_id is provided, pull missing fields from DB or Parquet
    if req.recruiter_id:
        rec_obj = db.query(Recruiter).filter(Recruiter.recruiter_id == req.recruiter_id).first()
        if rec_obj:
            target_email = target_email or rec_obj.email
            target_name = target_name or rec_obj.recruiter_name
            if not target_company and rec_obj.company:
                target_company = rec_obj.company.company_name
                target_domain = target_domain or rec_obj.company.primary_domain or rec_obj.company.website
        else:
            # Query DuckDB Parquet dataset (437k canonical profiles)
            try:
                parquet_rec = recruiter_store.get_by_id(req.recruiter_id)
            except Exception:
                parquet_rec = None
            if parquet_rec:
                target_email = target_email or parquet_rec.get("email")
                target_name = target_name or parquet_rec.get("recruiter_name")
                target_company = target_company or parquet_rec.get("company_id")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recruiter with ID {req.recruiter_id} not found in database or Parquet dataset."
                )

    if not target_email and not target_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide at least an email address or company domain to enrich."
        )

    # Execute Waterfall Enrichment
    enriched_data = zero_resource_enricher.enrich_profile(
        email=target_email,
        name=target_name,
        company_name=target_company,
        domain=target_domain,
    )

    persisted = False
    if rec_obj:
        try:
            # Parse or initialize metadata_json
            meta_dict = {}
            if rec_obj.metadata_json:
                try:
                    meta_dict = json.loads(rec_obj.metadata_json)
                except Exception:
                    meta_dict = {}

            # Update metadata attributes
            meta_dict["avatar_url"] = enriched_data.get("avatar_url")
            meta_dict["ats_system"] = enriched_data.get("ats_system")
            meta_dict["crm_system"] = enriched_data.get("crm_system")
            meta_dict["tech_stack"] = enriched_data.get("tech_stack", [])
            meta_dict["detected_tools"] = enriched_data.get("detected_tools", [])
            meta_dict["enriched_at"] = enriched_data.get("enriched_at")

            rec_obj.metadata_json = json.dumps(meta_dict)
            
            # Boost completeness score
            boost = enriched_data.get("score_boost", 0)
            if boost > 0:
                rec_obj.completeness_score = min(100, (rec_obj.completeness_score or 50) + boost)

            db.commit()

            # Update DuckDB Parquet dataset
            parquet_update = {
                "recruiter_id": rec_obj.recruiter_id,
                "metadata_json": json.dumps(meta_dict),
                "completeness_score": rec_obj.completeness_score,
            }
            if enriched_data.get("avatar_url"):
                parquet_update["logo_url"] = enriched_data.get("avatar_url")

            parquet_writer.update_records([parquet_update])
            recruiter_store.reload()
            persisted = True
        except Exception as e:
            logger.error("Error persisting enriched profile for #%s: %s", req.recruiter_id, e)
            db.rollback()
    elif parquet_rec:
        try:
            meta_dict = {}
            if parquet_rec.get("metadata_json"):
                try:
                    meta_dict = json.loads(parquet_rec["metadata_json"])
                except Exception:
                    meta_dict = {}
            meta_dict["avatar_url"] = enriched_data.get("avatar_url")
            meta_dict["ats_system"] = enriched_data.get("ats_system")
            meta_dict["crm_system"] = enriched_data.get("crm_system")
            meta_dict["tech_stack"] = enriched_data.get("tech_stack", [])
            meta_dict["detected_tools"] = enriched_data.get("detected_tools", [])
            meta_dict["enriched_at"] = enriched_data.get("enriched_at")

            old_score = parquet_rec.get("completeness_score") or 50
            boost = enriched_data.get("score_boost", 0)
            new_score = min(100, old_score + boost)

            parquet_update = {
                "recruiter_id": req.recruiter_id,
                "metadata_json": json.dumps(meta_dict),
                "completeness_score": new_score,
            }
            if enriched_data.get("avatar_url"):
                parquet_update["logo_url"] = enriched_data.get("avatar_url")

            parquet_writer.update_records([parquet_update])
            recruiter_store.reload()
            persisted = True
        except Exception as e:
            logger.error("Error persisting enriched Parquet profile for #%s: %s", req.recruiter_id, e)

    return {
        "success": True,
        "recruiter_id": req.recruiter_id,
        "enriched": enriched_data,
        "persisted": persisted,
    }


@router.post("/batch-enrich")
def batch_enrich_profiles(
    req: BatchEnrichRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Enriches a batch of recruiter IDs in a single transaction.
    """
    recruiters = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(req.recruiter_ids)).all()
    if not recruiters:
        return {"success": True, "enriched_count": 0, "results": []}

    results = []
    parquet_updates = []

    for r in recruiters:
        domain = None
        if r.company:
            domain = r.company.primary_domain or r.company.website

        data = zero_resource_enricher.enrich_profile(
            email=r.email,
            name=r.recruiter_name,
            company_name=r.company.company_name if r.company else None,
            domain=domain,
        )

        meta = {}
        if r.metadata_json:
            try:
                meta = json.loads(r.metadata_json)
            except Exception:
                meta = {}

        meta["avatar_url"] = data.get("avatar_url")
        meta["ats_system"] = data.get("ats_system")
        meta["crm_system"] = data.get("crm_system")
        meta["tech_stack"] = data.get("tech_stack", [])
        meta["detected_tools"] = data.get("detected_tools", [])

        r.metadata_json = json.dumps(meta)
        boost = data.get("score_boost", 0)
        if boost > 0:
            r.completeness_score = min(100, (r.completeness_score or 50) + boost)

        p_up = {
            "recruiter_id": r.recruiter_id,
            "metadata_json": json.dumps(meta),
            "completeness_score": r.completeness_score,
        }
        if data.get("avatar_url"):
            p_up["logo_url"] = data.get("avatar_url")
        parquet_updates.append(p_up)

        results.append({
            "recruiter_id": r.recruiter_id,
            "name": r.recruiter_name,
            "ats_system": data.get("ats_system"),
            "crm_system": data.get("crm_system"),
            "tech_stack": data.get("tech_stack", []),
            "avatar_url": data.get("avatar_url"),
        })

    try:
        db.commit()
        if parquet_updates:
            parquet_writer.update_records(parquet_updates)
            recruiter_store.reload()
    except Exception as e:
        logger.error("Error persisting batch enrichment: %s", e)
        db.rollback()

    return {
        "success": True,
        "enriched_count": len(results),
        "results": results,
    }


@router.get("/supported-taxonomies")
def get_supported_taxonomies(
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Returns the supported ATS, CRM, Mail, and Cloud taxonomies available for passive zero-cost detection.
    """
    ats_list = [r["name"] for r in CATEGORY_RULES if r["category"] == "ATS"]
    crm_list = [r["name"] for r in CATEGORY_RULES if r["category"] == "CRM"]
    email_list = [r["name"] for r in CATEGORY_RULES if r["category"] == "Email"]
    cloud_list = [r["name"] for r in CATEGORY_RULES if r["category"] in ("Cloud Infrastructure", "Email API", "Marketing Automation")]

    return {
        "success": True,
        "ats_systems": sorted(list(set(ats_list))),
        "crm_systems": sorted(list(set(crm_list))),
        "email_providers": sorted(list(set(email_list))),
        "cloud_and_marketing": sorted(list(set(cloud_list))),
        "cached_domains": len(TechStackFingerprinter._cache),
        "cached_identities": len(HashIdentityResolver._cache),
    }
