"""
enrichment.py — REST API endpoints for Zero-Resource Multi-Source Enterprise Enrichment.
Provides real-time company tech-stack / ATS fingerprinting, hash identity & avatar resolution,
and waterfall candidate profile enrichment.
"""

import json
import logging
from datetime import datetime, timezone
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
            meta_dict["nsr_profile"] = enriched_data.get("nsr_profile")
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
            meta_dict["nsr_profile"] = enriched_data.get("nsr_profile")
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


@router.get("/autonomous-engine-stats")
def get_autonomous_engine_stats(
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Returns live real-time operational telemetry of the continuous 24/7 autonomous enrichment
    and profile sweeper engine.
    """
    from ..services.autonomous_profile_sweeper import autonomous_sweeper
    telemetry = autonomous_sweeper.get_telemetry()
    return {
        "success": True,
        "autonomous_engine": telemetry,
    }


@router.get("/web-harvest-stats")
def get_web_harvest_stats(
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Returns live real-time operational telemetry of the WebHarvest Autonomous
    Web Discovery Engine — proactive web crawling for new profile discovery.
    """
    from ..services.web_harvest_engine import web_harvest_engine
    telemetry = web_harvest_engine.get_telemetry()
    return {
        "success": True,
        "web_harvest_engine": telemetry,
    }


@router.get("/web-harvest-reports")
def get_web_harvest_reports(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Returns granular forensic reports of all profiles and companies discovered
    by the 24/7 autonomous WebHarvest background crawler.
    Includes exact source URLs, extraction confidence, and database commit status.
    """
    from ..models.staging_models import DiscoveryStaging
    valid_sources = [
        "web_harvest", "search_xray", "ats_job_board",
        "git_commit_mine", "email_signature_flywheel"
    ]
    records = (
        db.query(DiscoveryStaging)
        .filter(DiscoveryStaging.extraction_source.in_(valid_sources))
        .order_by(DiscoveryStaging.id.desc())
        .limit(limit)
        .all()
    )
    
    reports = []
    for r in records:
        meta = {}
        if r.metadata_json:
            try:
                meta = json.loads(r.metadata_json)
            except Exception:
                meta = {}
                
        reports.append({
            "id": r.id,
            "discovery_id": r.discovery_id,
            "name": r.raw_name,
            "title": r.raw_title,
            "company": r.raw_company,
            "email": r.raw_email,
            "phone": r.raw_phone,
            "linkedin": r.raw_linkedin,
            "location": r.raw_location,
            "source_url": r.source_url,
            "source_domain": meta.get("source_domain") or (r.source_url.split('/')[2] if r.source_url and '/' in r.source_url else "—"),
            "quality_score": r.quality_score,
            "dom_confidence": r.dom_confidence,
            "processing_status": r.processing_status,
            "decision": r.decision,
            "decision_reason": r.decision_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "harvest_cycle": meta.get("harvest_cycle", 1),
            "discovery_method": meta.get("discovery_method", "autonomous_web_crawl"),
            "smtp_verification": meta.get("smtp_verification"),
        })

    return {
        "success": True,
        "total_reports": len(reports),
        "reports": reports
    }


@router.post("/web-harvest-trigger")
async def trigger_web_harvest_cycle(
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Manually triggers an immediate autonomous web harvest & crawl cycle in the background.
    """
    import asyncio
    from ..services.web_harvest_engine import web_harvest_engine
    
    # Run cycle asynchronously in background thread
    asyncio.create_task(asyncio.to_thread(web_harvest_engine._run_harvest_cycle))
    
    return {
        "success": True,
        "message": "Autonomous WebHarvest crawl cycle triggered successfully in the background.",
        "triggered_at": datetime.now(timezone.utc).isoformat()
    }


# ── Multi-Source Web Intelligence & Staging Reconciliation Endpoints ─────────

class CompanyTargetRequest(BaseModel):
    company_name: str = Field(..., description="Target company name (e.g. 'Insight Global')")
    domain: str = Field(..., description="Target company domain (e.g. 'insightglobal.com')")
    max_profiles: Optional[int] = Field(5, ge=1, le=20)


@router.post("/xray/harvest-company")
def harvest_xray_company(
    req: CompanyTargetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Executes an autonomous Search Engine X-Ray Dorking pass to mine active recruiters
    and talent acquisition leaders for a company, verifying deliverability via Port 25 SMTP.
    """
    from ..services.search_xray_harvester import search_xray_harvester
    staged = search_xray_harvester.harvest_company(
        company_name=req.company_name,
        domain=req.domain,
        db=db,
        max_profiles=req.max_profiles,
        owner_user_id=current_user.id
    )
    return {
        "success": True,
        "source": "search_xray",
        "company": req.company_name,
        "domain": req.domain,
        "profiles_staged": len(staged),
        "results": staged,
        "stats": search_xray_harvester.stats,
    }


@router.post("/ats/scan-company")
def scan_ats_company(
    req: CompanyTargetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Scans public corporate ATS boards (Greenhouse, Lever) for the target company
    to extract active hiring managers, recruiters, and contact points.
    """
    from ..services.ats_board_harvester import ats_board_harvester
    staged = ats_board_harvester.harvest_company(
        company_name=req.company_name,
        domain=req.domain,
        db=db,
        max_profiles=req.max_profiles,
        owner_user_id=current_user.id
    )
    return {
        "success": True,
        "source": "ats_job_board",
        "company": req.company_name,
        "domain": req.domain,
        "profiles_staged": len(staged),
        "results": staged,
        "stats": ats_board_harvester.stats,
    }


@router.post("/git/mine-commits")
def mine_git_commits(
    domain: str = Query(..., description="Target corporate domain (e.g. 'gitlab.com')"),
    company_name: Optional[str] = Query(None, description="Optional company name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Mines public git commit logs and author headers to discover 100% ground-truth
    verified corporate emails, establishing locked CompanyEmailPatterns.
    """
    from ..services.git_commit_miner import git_commit_miner
    comp_name = company_name or domain.split(".")[0].capitalize()
    staged = git_commit_miner.mine_company_domain(
        company_name=comp_name,
        domain=domain,
        db=db,
        max_contacts=5,
        owner_user_id=current_user.id
    )
    return {
        "success": True,
        "source": "git_commit_mine",
        "domain": domain,
        "contacts_staged": len(staged),
        "results": staged,
        "stats": git_commit_miner.stats,
    }


@router.post("/reconcile-staging")
def reconcile_staging_pipeline(
    batch_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Executes a safe, non-destructive reconciliation pass of discovery_staging:
    - Enriches existing recruiters with missing fields (phone, title, LinkedIn, location)
    - Runs Port 25 live SMTP verification on emails
    - Safely promotes verified fresh talent into the master catalog
    """
    from ..services.db_auto_enricher import db_auto_enricher
    result = db_auto_enricher.reconcile_staging_batch(db=db, limit=batch_size)
    return {
        "success": True,
        "reconciliation": result,
        "lifetime_stats": db_auto_enricher.stats,
    }


@router.get("/multi-source-stats")
def get_multi_source_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Aggregated operational intelligence telemetry across all external data sources:
    Search X-Ray, ATS Job Boards, Git Commit Mining, WebHarvest, and Email Signatures.
    """
    from ..models.staging_models import DiscoveryStaging
    from ..services.search_xray_harvester import search_xray_harvester
    from ..services.ats_board_harvester import ats_board_harvester
    from ..services.git_commit_miner import git_commit_miner
    from ..services.db_auto_enricher import db_auto_enricher

    from sqlalchemy import func
    counts_by_source = (
        db.query(DiscoveryStaging.extraction_source, func.count(DiscoveryStaging.id))
        .group_by(DiscoveryStaging.extraction_source)
        .all()
    )

    breakdown = {src: cnt for src, cnt in counts_by_source}
    total_staged = sum(breakdown.values())

    return {
        "success": True,
        "total_staged_observations": total_staged,
        "source_breakdown": breakdown,
        "engine_telemetry": {
            "search_xray": search_xray_harvester.stats,
            "ats_harvester": ats_board_harvester.stats,
            "git_commit_miner": git_commit_miner.stats,
            "db_auto_enricher": db_auto_enricher.stats,
        }
    }


class PriorityTargetRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None


@router.post("/priority-queue-target")
def queue_priority_company_target(
    payload: PriorityTargetRequest,
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Enqueues a high-priority company target into the WebHarvest & X-Ray engine
    to be scraped and mined in the very next cycle.
    """
    from ..services.web_harvest_engine import web_harvest_engine
    enqueued = web_harvest_engine.enqueue_priority_target(
        company_name=payload.company_name,
        domain=payload.domain,
        source=f"admin_manual:{current_user.id}"
    )
    return {
        "success": True,
        "enqueued": enqueued,
        "company_name": payload.company_name,
        "queue_length": len(web_harvest_engine.priority_queue),
        "priority_targets": web_harvest_engine.get_priority_targets(),
    }


@router.get("/priority-targets")
def get_priority_targets(
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """Returns the list of currently queued priority targets."""
    from ..services.web_harvest_engine import web_harvest_engine
    return {
        "success": True,
        "count": len(web_harvest_engine.priority_queue),
        "targets": web_harvest_engine.get_priority_targets(),
    }


@router.post("/sync-parquet")
def sync_promoted_to_parquet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Dual-Syncs newly promoted PostgreSQL recruiters into the DuckDB Parquet dataset.
    """
    from ..models.models import Recruiter
    from ..services.parquet_writer import parquet_writer
    from ..services.recruiter_store import PARQUET_FILE, recruiter_store
    import duckdb

    promoted_recs = db.query(Recruiter).filter(
        Recruiter.data_source.like("web_intelligence:%")
    ).all()

    con = duckdb.connect()
    p_path = PARQUET_FILE.replace("\\", "/")
    existing_emails = set()
    existing_ids = set()
    try:
        promoted_emails = [r.email.lower() for r in promoted_recs if r.email]
        if promoted_emails:
            escaped = [e.replace("'", "''") for e in promoted_emails]
            in_clause = ", ".join(f"'{e}'" for e in escaped)
            rows = con.execute(f"SELECT recruiter_id, lower(email) FROM read_parquet('{p_path}') WHERE lower(email) IN ({in_clause})").fetchall()
            for r in rows:
                if r[0] is not None:
                    existing_ids.add(r[0])
                if r[1]:
                    existing_emails.add(r[1])
    except Exception as e:
        logger.warning("Error reading parquet in sync-parquet: %s", e)
    finally:
        con.close()

    to_append = []
    seen = set()
    for r in promoted_recs:
        r_email = (r.email or "").strip().lower()
        if r.recruiter_id in existing_ids or (r_email and r_email in existing_emails) or (r_email and r_email in seen):
            continue
        if r_email:
            seen.add(r_email)
        to_append.append({
            "recruiter_id": r.recruiter_id,
            "recruiter_name": r.recruiter_name,
            "title": r.title,
            "company_id": r.company_id,
            "email": r.email,
            "phone": r.phone,
            "linkedin": r.linkedin,
            "location": r.location,
            "state": getattr(r, "state", None),
            "email_status": r.email_status,
            "email_confidence": r.email_confidence,
            "data_source": r.data_source,
            "notes": r.notes,
            "quality_score": r.email_confidence or 85,
            "completeness_score": 85,
            "is_active": True,
            "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat(),
            "updated_at": r.updated_at.isoformat() if r.updated_at else datetime.utcnow().isoformat(),
        })

    appended_count = 0
    if to_append:
        appended_count = parquet_writer.append_records(to_append)

    return {
        "success": True,
        "appended_to_parquet": appended_count,
        "total_promoted_in_db": len(promoted_recs),
        "already_in_parquet": len(existing_emails) or len(existing_ids),
        "total_parquet_records": recruiter_store.get_stats().get("total_recruiters", 0),
    }


class PushToCampaignRequest(BaseModel):
    campaign_id: int
    recruiter_id: Optional[int] = None
    staged_id: Optional[int] = None
    email: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None


@router.post("/push-to-campaign")
def push_recruiter_to_campaign(
    payload: PushToCampaignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_request),
) -> Dict[str, Any]:
    """
    Direct 1-Click Outreach Bridge: Enrolls a discovered recruiter directly
    into an active campaign sequence step.
    """
    from ..models.campaigns import Campaign, CampaignRecruiter, SequenceStep
    from ..models.models import Recruiter
    from sqlalchemy import func

    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == payload.campaign_id,
        Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    first_step = db.query(SequenceStep).filter(
        SequenceStep.campaign_id == payload.campaign_id,
        SequenceStep.is_active == True
    ).order_by(SequenceStep.step_order.asc()).first()

    recruiter = None
    if payload.recruiter_id:
        recruiter = db.query(Recruiter).filter(Recruiter.recruiter_id == payload.recruiter_id).first()
    elif payload.email:
        recruiter = db.query(Recruiter).filter(func.lower(Recruiter.email) == payload.email.lower()).first()

    if not recruiter and payload.email:
        recruiter = Recruiter(
            user_id=current_user.id,
            recruiter_name=payload.name or payload.email.split("@")[0],
            email=payload.email.lower(),
            title=payload.title or "Recruiter",
            data_source="web_harvest_campaign_bridge",
        )
        db.add(recruiter)
        db.flush()

    if not recruiter:
        raise HTTPException(status_code=400, detail="Could not resolve recruiter identity or email")

    existing = db.query(CampaignRecruiter).filter(
        CampaignRecruiter.campaign_id == campaign.campaign_id,
        CampaignRecruiter.recruiter_id == recruiter.recruiter_id
    ).first()

    if existing:
        return {
            "success": True,
            "already_enrolled": True,
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.name,
            "recruiter_id": recruiter.recruiter_id,
            "message": f"{recruiter.recruiter_name} is already enrolled in '{campaign.name}'",
        }

    cr = CampaignRecruiter(
        campaign_id=campaign.campaign_id,
        recruiter_id=recruiter.recruiter_id,
        current_step_id=first_step.step_id if first_step else None,
        status="pending",
        enrolled_at=datetime.now(timezone.utc),
        next_send_at=campaign.start_at or datetime.now(timezone.utc),
    )
    db.add(cr)
    db.commit()

    return {
        "success": True,
        "already_enrolled": False,
        "campaign_id": campaign.campaign_id,
        "campaign_name": campaign.name,
        "recruiter_id": recruiter.recruiter_id,
        "recruiter_name": recruiter.recruiter_name,
        "email": recruiter.email,
        "message": f"Successfully enrolled {recruiter.recruiter_name} into '{campaign.name}'!",
    }


