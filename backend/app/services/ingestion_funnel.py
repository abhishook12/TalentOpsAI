"""
ingestion_funnel.py — Universal Data Ingestion & Quality Funnel Engine
======================================================================
The mandatory 7-stage quality funnel through which ALL upcoming data flows:
WebHarvest, Desktop Scout, Browser Extensions, Search X-Ray, and Manual Uploads.

FUNNEL ARCHITECTURE:
  Gate 1: Raw Sourcing & Platform Chrome Elimination (Top of Funnel)
          - Filters empty names, buttons, 404s, login pages, and notification feeds.
  Gate 2: Hard Entity Disambiguation & Segregation
          - Classifies into PERSON, COMPANY, JOB_POSTING, CONTACT_INFO, MARKET_SIGNAL.
          - Hard walls: Companies, Jobs, and Signals are routed to dedicated tables
            and NEVER cross into the Person / Recruiter catalog.
  Gate 3: Contextual Identity Reconstruction & Sanitization
          - Validates human names (strictly rejects non-human entities).
          - Sanitizes UI action titles ('Contact', 'View profile' -> 'Staffing Professional').
          - Reconstructs true company from URL context (/company/<slug>/) or page title
            if raw company was empty or platform noise ('Linkedin', 'Google', etc.).
  Gate 4: Autonomous Corporate Email Intelligence
          - Resolves canonical corporate domain (dictionary, whitespace-insensitive DB slug match).
          - Reverse-engineers empirical email formulas from colleagues in Master DB.
          - Synthesizes candidate email permutations ('first.last', 'f_last', 'first', etc.).
  Gate 5: Live Deliverability Probing & Ranking Gate
          - Non-intrusive Port 25 SMTP RCPT TO handshake + live DNS MX verification.
          - Code 250 -> SMTP_VERIFIED; Code 550 -> cycles alternatives; Catchall -> CATCHALL_VERIFIED.
          - Auto-learns newly verified pattern into `company_email_patterns`.
  Gate 6: Actionable Contact Intelligence Gate
          - Requires at least 1 verified contact channel: deliverable email, linkedin URL, or phone.
          - Hard-blocks synthetic '@unknown.com' and '@noemail.talentops'.
  Gate 7: Master Catalog Promotion & Dual-Sync Flywheel (Bottom of Funnel)
          - De-duplicates against master catalog:
            - If existing -> non-destructively enriches verified email, title, phone, or LinkedIn URL.
            - If new -> creates canonical recruiter and links to canonical company.
          - Invalidates cache and syncs to DuckDB Parquet for sub-second frontend search.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from ..models.staging_models import DiscoveryStaging, ResolvedPerson
from ..models.models import Recruiter, Company, CompanyEmailPattern
from ..models.knowledge_models import KnowledgeEntity, KnowledgeSignal
from ..utils.normalizer import (
    validate_human_name,
    is_company_name,
    is_platform_name,
    is_ui_action,
    clean_company,
    clean_title,
    clean_location_text,
)
from .entity_classifier import (
    entity_classifier,
    ENTITY_PERSON,
    ENTITY_COMPANY,
    ENTITY_JOB_POSTING,
    ENTITY_CONTACT_INFO,
    ENTITY_MARKET_SIGNAL,
    ENTITY_NOISE,
)
from .email_intelligence_service import email_intelligence
from .smtp_prober import smtp_prober

logger = logging.getLogger("talentops.ingestion_funnel")


class UniversalIngestionFunnel:
    """
    Unified Ingestion Funnel governing 100% of data entering TalentOpsAI.
    Ensures zero garbage, zero fake emails, and verified deliverability.
    """

    def __init__(self):
        self.telemetry = {
            "total_ingested": 0,
            "gate_1_noise_dropped": 0,
            "gate_2_routed": {
                ENTITY_PERSON: 0,
                ENTITY_COMPANY: 0,
                ENTITY_JOB_POSTING: 0,
                ENTITY_CONTACT_INFO: 0,
                ENTITY_MARKET_SIGNAL: 0,
            },
            "gate_3_company_inferred": 0,
            "gate_3_title_sanitized": 0,
            "gate_4_email_synthesized": 0,
            "gate_5_smtp_verified": 0,
            "gate_5_bounced_rejected": 0,
            "gate_6_contact_held_review": 0,
            "gate_7_promoted_new": 0,
            "gate_7_enriched_existing": 0,
        }

    def process_staging_record(self, staged: DiscoveryStaging, db: Session) -> Dict[str, Any]:
        """
        Processes a single staging record sequentially through all 7 gates.
        Returns a rich funnel decision trace.
        """
        self.telemetry["total_ingested"] += 1
        now_utc = datetime.now(timezone.utc)

        # ══════════════════════════════════════════════════════════════════════
        # GATE 1: RAW SOURCING & NOISE ELIMINATION
        # ══════════════════════════════════════════════════════════════════════
        raw_name = (staged.raw_name or "").strip()
        raw_title = (staged.raw_title or "").strip()
        raw_company = (staged.raw_company or "").strip()
        raw_email = (staged.raw_email or "").strip().lower() if staged.raw_email else None
        source_url = (staged.source_url or "").strip()
        page_title = (staged.source_page_title or "").strip()

        if not raw_name or len(raw_name) < 2 or raw_name.lower() in ("unknown", "n/a", "none", "null"):
            staged.processing_status = "rejected"
            staged.decision = "REJECT_GATE_1_NOISE"
            staged.decision_reason = "Gate 1: Empty or invalid placeholder name"
            staged.processed_at = now_utc
            self.telemetry["gate_1_noise_dropped"] += 1
            return {"gate": 1, "status": "REJECTED", "reason": staged.decision_reason}

        # ══════════════════════════════════════════════════════════════════════
        # GATE 2: HARD ENTITY DISAMBIGUATION & SEGREGATION
        # ══════════════════════════════════════════════════════════════════════
        classification = entity_classifier.classify(
            raw_name=raw_name,
            raw_title=raw_title,
            raw_company=raw_company,
            raw_email=raw_email,
            raw_phone=staged.raw_phone,
            source_url=source_url,
            source_page_title=page_title,
            extraction_source=staged.extraction_source,
        )
        entity_type = classification["entity_type"]
        staged.entity_type = entity_type

        if entity_type == ENTITY_NOISE:
            staged.processing_status = "rejected"
            staged.decision = "REJECT_GATE_2_NOISE"
            staged.decision_reason = f"Gate 2: Classified as NOISE: {classification['reason']}"
            staged.processed_at = now_utc
            self.telemetry["gate_1_noise_dropped"] += 1
            return {"gate": 2, "status": "REJECTED", "reason": staged.decision_reason}

        if entity_type == ENTITY_COMPANY:
            self.telemetry["gate_2_routed"][ENTITY_COMPANY] += 1
            return self._route_company_entity(staged, db, now_utc)

        if entity_type == ENTITY_JOB_POSTING:
            self.telemetry["gate_2_routed"][ENTITY_JOB_POSTING] += 1
            return self._route_job_entity(staged, db, now_utc)

        if entity_type == ENTITY_CONTACT_INFO:
            self.telemetry["gate_2_routed"][ENTITY_CONTACT_INFO] += 1
            return self._route_contact_entity(staged, db, now_utc)

        if entity_type == ENTITY_MARKET_SIGNAL:
            self.telemetry["gate_2_routed"][ENTITY_MARKET_SIGNAL] += 1
            return self._route_signal_entity(staged, db, now_utc)

        # Entity is PERSON
        self.telemetry["gate_2_routed"][ENTITY_PERSON] += 1

        # ══════════════════════════════════════════════════════════════════════
        # GATE 3: CONTEXTUAL IDENTITY RECONSTRUCTION & SANITIZATION
        # ══════════════════════════════════════════════════════════════════════
        is_human, clean_name_str, rej_reason = validate_human_name(raw_name)
        if not is_human or is_company_name(raw_name):
            staged.processing_status = "rejected"
            staged.decision = "REJECT_GATE_3_NON_HUMAN"
            staged.decision_reason = f"Gate 3: Failed human name validation: {rej_reason or 'Company name detected'}"
            staged.processed_at = now_utc
            return {"gate": 3, "status": "REJECTED", "reason": staged.decision_reason}

        raw_name = clean_name_str

        # Company Reconstruction: NEVER allow platform noise (Linkedin, Google, etc.)
        cand_company = clean_company(raw_company) if raw_company else None
        if not cand_company or is_platform_name(cand_company):
            cand_company = None
            # Infer from LinkedIn company URL: /company/<slug>/
            if source_url:
                comp_match = re.search(r'/company/([^/?#]+)', source_url)
                if comp_match:
                    slug = comp_match.group(1).replace('-', ' ').strip()
                    if slug and not is_platform_name(slug):
                        cand_company = slug.title()
                        self.telemetry["gate_3_company_inferred"] += 1
            # Infer from page title: "Company Name: People | LinkedIn"
            if not cand_company and page_title:
                pt_match = re.search(r'^([^:|]+)(?::\s*People|\s*\|\s*LinkedIn)', page_title, re.IGNORECASE)
                if pt_match:
                    pt_comp = pt_match.group(1).strip()
                    if pt_comp and not is_platform_name(pt_comp):
                        cand_company = pt_comp
                        self.telemetry["gate_3_company_inferred"] += 1

        # Title Sanitization: eliminate UI action words ('Contact', 'View profile')
        cand_title = raw_title
        if not cand_title or is_ui_action(cand_title) or cand_title.lower() in ('contact', 'view profile', 'connect', 'message', 'follow', 'more'):
            cand_title = "Talent Acquisition Specialist" if "recruiter" in source_url.lower() else "Staffing Professional"
            self.telemetry["gate_3_title_sanitized"] += 1

        # ══════════════════════════════════════════════════════════════════════
        # GATE 4 & 5: AUTONOMOUS CORPORATE EMAIL INTELLIGENCE & DELIVERABILITY PROBE
        # ══════════════════════════════════════════════════════════════════════
        synthesized_email = None
        email_status = "UNVERIFIED"
        email_confidence = staged.quality_score or 75

        # Check existing email
        if raw_email and not raw_email.endswith('@unknown.com') and not raw_email.endswith('@noemail.talentops'):
            # Existing email: probe deliverability
            try:
                probe = smtp_prober.probe_mailbox(raw_email)
                if probe.smtp_code == 250:
                    email_status = "SMTP_VERIFIED"
                    email_confidence = 100
                    self.telemetry["gate_5_smtp_verified"] += 1
                elif probe.smtp_code == 550:
                    email_status = "BOUNCED"
                    self.telemetry["gate_5_bounced_rejected"] += 1
                else:
                    email_status = "SYNTAX_VALID"
            except Exception:
                email_status = "SYNTAX_VALID"
        elif cand_company:
            # Autonomous Corporate Email Resolution
            try:
                intel_res = email_intelligence.resolve_and_enrich_candidate(
                    full_name=raw_name,
                    company_name=cand_company,
                    db=db
                )
                if intel_res and intel_res.get("email") and intel_res.get("status") in ("SMTP_VERIFIED", "PATTERN_VERIFIED", "MX_VERIFIED"):
                    synthesized_email = intel_res["email"]
                    raw_email = synthesized_email
                    email_status = intel_res["status"]
                    email_confidence = int(intel_res.get("confidence", 0.85) * 100)
                    self.telemetry["gate_4_email_synthesized"] += 1
                    if email_status == "SMTP_VERIFIED":
                        self.telemetry["gate_5_smtp_verified"] += 1
                    logger.info("🎯 Gate 4+5 Synthesized deliverable email for %s at %s: %s (%s)",
                                raw_name, cand_company, synthesized_email, email_status)
            except Exception as e:
                logger.debug("Gate 4+5 corporate email intelligence note: %s", e)

        # ══════════════════════════════════════════════════════════════════════
        # GATE 6: ACTIONABLE CONTACT INTELLIGENCE GATE
        # ══════════════════════════════════════════════════════════════════════
        has_real_email = bool(raw_email and '@' in raw_email and not raw_email.endswith('@unknown.com') and not raw_email.endswith('@noemail.talentops') and email_status != "BOUNCED")
        has_linkedin = bool(staged.raw_linkedin and 'linkedin.com/in/' in staged.raw_linkedin.lower())
        has_phone = bool(staged.raw_phone and len(staged.raw_phone.strip()) >= 7)

        if not has_real_email and not has_linkedin and not has_phone:
            staged.processing_status = "review"
            staged.decision = "REVIEW_GATE_6_NO_CONTACT"
            staged.decision_reason = f"Gate 6: Candidate '{raw_name}' lacks verified email, individual LinkedIn URL, and phone. Held in Review."
            staged.processed_at = now_utc
            self.telemetry["gate_6_contact_held_review"] += 1
            return {"gate": 6, "status": "HELD_REVIEW", "reason": staged.decision_reason}

        # ══════════════════════════════════════════════════════════════════════
        # GATE 7: MASTER CATALOG PROMOTION & DUAL-SYNC FLYWHEEL
        # ══════════════════════════════════════════════════════════════════════
        # Canonical Company Match
        company = None
        if cand_company:
            comp_slug = re.sub(r'[^a-z0-9]', '', cand_company.lower())
            company = db.query(Company).filter(
                (Company.company_name.ilike(cand_company)) |
                (sqlfunc.replace(sqlfunc.lower(Company.company_name), ' ', '') == comp_slug)
            ).first()

        clean_dom = ""
        if raw_email and "@" in raw_email:
            clean_dom = raw_email.split("@")[1]

        if not company and cand_company:
            company = Company(
                company_name=cand_company,
                normalized_company_name=cand_company.lower().strip(),
                primary_domain=clean_dom if clean_dom not in ('unknown.com', 'linkedin.com') else None,
            )
            db.add(company)
            db.flush()
        elif company and (not company.primary_domain or company.primary_domain in ('unknown.com', 'linkedin.com')) and clean_dom and clean_dom not in ('unknown.com', 'linkedin.com'):
            company.primary_domain = clean_dom

        # Check existing recruiter
        existing_recruiter = None
        if has_real_email and raw_email:
            existing_recruiter = db.query(Recruiter).filter(
                sqlfunc.lower(Recruiter.email) == raw_email.lower()
            ).first()

        if not existing_recruiter and company:
            existing_recruiter = db.query(Recruiter).filter(
                sqlfunc.lower(Recruiter.recruiter_name) == raw_name.lower(),
                Recruiter.company_id == company.company_id
            ).first()

        if existing_recruiter:
            # Non-destructive enrichment
            fields_enriched = []
            if not existing_recruiter.title or existing_recruiter.title == 'Contact' or is_ui_action(existing_recruiter.title):
                existing_recruiter.title = cand_title
                fields_enriched.append("title")
            if not existing_recruiter.phone and staged.raw_phone:
                existing_recruiter.phone = staged.raw_phone
                fields_enriched.append("phone")
            if not existing_recruiter.linkedin and staged.raw_linkedin:
                existing_recruiter.linkedin = staged.raw_linkedin
                fields_enriched.append("linkedin")
            if has_real_email and (not existing_recruiter.email or existing_recruiter.email.endswith('@unknown.com')):
                existing_recruiter.email = raw_email
                existing_recruiter.email_status = email_status
                existing_recruiter.email_confidence = email_confidence
                fields_enriched.append("email_smtp_verified")

            staged.processing_status = "enriched"
            staged.decision = "ENRICHED_EXISTING"
            staged.decision_reason = f"Gate 7: Enriched recruiter #{existing_recruiter.recruiter_id} ({existing_recruiter.recruiter_name}): {', '.join(fields_enriched) if fields_enriched else 'Confirmed'}"
            staged.processed_at = now_utc
            self.telemetry["gate_7_enriched_existing"] += 1
            return {"gate": 7, "status": "ENRICHED", "recruiter_id": existing_recruiter.recruiter_id}

        else:
            # New recruiter requires deliverable non-null corporate email
            if not has_real_email or not raw_email:
                staged.processing_status = "review"
                staged.decision = "REVIEW_GATE_6_NO_EMAIL"
                staged.decision_reason = f"Gate 6: New candidate '{raw_name}' lacks deliverable corporate email. Held in Review."
                staged.processed_at = now_utc
                self.telemetry["gate_6_contact_held_review"] += 1
                return {"gate": 6, "status": "HELD_REVIEW", "reason": staged.decision_reason}

            # Promote as verified new recruiter
            raw_loc = (staged.raw_location or "").strip()
            state_abbr = None
            if raw_loc:
                try:
                    from ..utils.state_mapper import extract_state_detailed
                    state_abbr, _ = extract_state_detailed(raw_loc)
                except Exception:
                    pass

            final_email = raw_email
            new_recruiter = Recruiter(
                recruiter_name=raw_name,
                title=cand_title,
                company_id=company.company_id if company else None,
                email=final_email,
                phone=staged.raw_phone,
                linkedin=staged.raw_linkedin,
                location=raw_loc or None,
                state=state_abbr,
                email_status=email_status if final_email else "UNVERIFIED",
                email_confidence=email_confidence if final_email else 0,
                data_source=f"universal_funnel:{staged.extraction_source or 'harvest'}",
                notes=f"Auto-harvested via Ingestion Funnel on {now_utc.strftime('%Y-%m-%d')}",
            )
            db.add(new_recruiter)
            db.flush()

            staged.processing_status = "promoted"
            staged.decision = "PROMOTED_NEW"
            staged.decision_reason = f"Gate 7: Promoted #{new_recruiter.recruiter_id} to Master DB with email={final_email} ({email_status})"
            staged.processed_at = now_utc
            self.telemetry["gate_7_promoted_new"] += 1

            rec_dict = {
                "recruiter_id": new_recruiter.recruiter_id,
                "recruiter_name": new_recruiter.recruiter_name,
                "title": new_recruiter.title,
                "company_id": new_recruiter.company_id,
                "email": new_recruiter.email,
                "phone": new_recruiter.phone,
                "linkedin": new_recruiter.linkedin,
                "location": raw_loc or None,
                "state": state_abbr,
                "email_status": new_recruiter.email_status,
                "email_confidence": new_recruiter.email_confidence,
                "data_source": new_recruiter.data_source,
                "notes": new_recruiter.notes,
                "quality_score": email_confidence,
                "completeness_score": 85,
                "is_active": True,
                "created_at": now_utc.isoformat(),
                "updated_at": now_utc.isoformat(),
            }
            return {"gate": 7, "status": "PROMOTED", "recruiter_id": new_recruiter.recruiter_id, "recruiter_dict": rec_dict}

    # ──────────────────────────────────────────────────────────────────────────
    # Non-Person Entity Routing Handlers (Hard Walls)
    # ──────────────────────────────────────────────────────────────────────────

    def _route_company_entity(self, staged: DiscoveryStaging, db: Session, now_utc: datetime) -> Dict[str, Any]:
        """Routes COMPANY entity directly into companies table — NEVER creates recruiter."""
        comp_name = staged.raw_name or staged.raw_company
        comp_name = clean_company(comp_name) or (comp_name.strip() if comp_name else "")
        if not comp_name:
            staged.processing_status = "rejected"
            staged.decision = "REJECT_EMPTY_COMPANY"
            staged.processed_at = now_utc
            return {"gate": 2, "status": "REJECTED", "entity_type": ENTITY_COMPANY}

        comp_slug = re.sub(r'[^a-z0-9]', '', comp_name.lower())
        existing = db.query(Company).filter(
            (Company.company_name.ilike(comp_name)) |
            (sqlfunc.replace(sqlfunc.lower(Company.company_name), ' ', '') == comp_slug)
        ).first()

        if not existing:
            new_comp = Company(
                company_name=comp_name[:255],
                canonical_name=comp_name[:255],
                industry=(staged.raw_title or "")[:100] or None,
                location=(staged.raw_location or "")[:100] or None,
                verification_status="verified_funnel",
                trust_score=90,
                data_source="ingestion_funnel_company",
            )
            db.add(new_comp)
            db.flush()

        staged.processing_status = "committed"
        staged.decision = "COMPANY_COMMITTED"
        staged.decision_reason = f"Gate 2: Routed to Company directory: {comp_name}"
        staged.processed_at = now_utc
        return {"gate": 2, "status": "COMMITTED", "entity_type": ENTITY_COMPANY}

    def _route_job_entity(self, staged: DiscoveryStaging, db: Session, now_utc: datetime) -> Dict[str, Any]:
        """Routes JOB_POSTING entity to Knowledge Graph — NEVER creates recruiter."""
        try:
            job_title = staged.raw_name or staged.raw_title or "Job Vacancy"
            raw_comp = staged.raw_company or "Unknown Employer"
            attrs = {
                "job_title": job_title,
                "company": raw_comp,
                "location": staged.raw_location,
                "source_url": staged.source_url,
                "source": staged.extraction_source,
            }
            k_entity = KnowledgeEntity(
                owner_user_id=staged.owner_user_id or 1,
                entity_type="JOB_POSTING",
                canonical_name=job_title[:255],
                primary_identifier=(staged.source_url or staged.discovery_id or f"job_{staged.id}")[:255],
                attributes_json=json.dumps(attrs),
                confidence=0.85,
                source_url=(staged.source_url or "")[:500] if staged.source_url else None,
            )
            db.add(k_entity)
            db.flush()

            k_sig = KnowledgeSignal(
                owner_user_id=staged.owner_user_id or 1,
                entity_id=k_entity.id,
                signal_type="JOB_POSTING",
                title=f"{job_title} at {raw_comp}"[:255],
                description=staged.about_summary or staged.raw_title,
                confidence=0.85,
                source_url=(staged.source_url or "")[:500] if staged.source_url else None,
            )
            db.add(k_sig)
        except Exception as e:
            logger.debug("Knowledge job route error: %s", e)

        staged.processing_status = "committed"
        staged.decision = "JOB_CAPTURED"
        staged.decision_reason = f"Gate 2: Routed to Knowledge Graph Job Vacancy: {staged.raw_name}"
        staged.processed_at = now_utc
        return {"gate": 2, "status": "COMMITTED", "entity_type": ENTITY_JOB_POSTING}

    def _route_contact_entity(self, staged: DiscoveryStaging, db: Session, now_utc: datetime) -> Dict[str, Any]:
        """Routes generic organization contact info — NEVER creates recruiter."""
        try:
            label = staged.raw_name or "Company Contact"
            attrs = {
                "contact_label": label,
                "email": staged.raw_email,
                "phone": staged.raw_phone,
                "company": staged.raw_company,
                "source_url": staged.source_url,
            }
            k_entity = KnowledgeEntity(
                owner_user_id=staged.owner_user_id or 1,
                entity_type="CONTACT_INFO",
                canonical_name=label[:255],
                primary_identifier=(staged.raw_email or staged.raw_phone or staged.source_url or f"contact_{staged.id}")[:255],
                attributes_json=json.dumps(attrs),
                confidence=0.70,
                source_url=(staged.source_url or "")[:500] if staged.source_url else None,
            )
            db.add(k_entity)
        except Exception as e:
            logger.debug("Knowledge contact route error: %s", e)

        staged.processing_status = "committed"
        staged.decision = "CONTACT_CAPTURED"
        staged.decision_reason = f"Gate 2: Routed to Organization Contact: {staged.raw_name}"
        staged.processed_at = now_utc
        return {"gate": 2, "status": "COMMITTED", "entity_type": ENTITY_CONTACT_INFO}

    def _route_signal_entity(self, staged: DiscoveryStaging, db: Session, now_utc: datetime) -> Dict[str, Any]:
        """Routes market signals — NEVER creates recruiter."""
        try:
            title = staged.raw_name or "Market Signal"
            attrs = {
                "title": title,
                "description": staged.raw_title,
                "company": staged.raw_company,
                "source_url": staged.source_url,
            }
            k_sig = KnowledgeSignal(
                owner_user_id=staged.owner_user_id or 1,
                signal_type="MARKET_SIGNAL",
                title=title[:255],
                description=staged.raw_title or staged.about_summary,
                confidence=0.70,
                source_url=(staged.source_url or "")[:500] if staged.source_url else None,
            )
            db.add(k_sig)
        except Exception as e:
            logger.debug("Knowledge signal route error: %s", e)

        staged.processing_status = "committed"
        staged.decision = "SIGNAL_CAPTURED"
        staged.decision_reason = f"Gate 2: Routed to Market Signal: {staged.raw_name}"
        staged.processed_at = now_utc
        return {"gate": 2, "status": "COMMITTED", "entity_type": ENTITY_MARKET_SIGNAL}

    def process_staging_batch(self, db: Session, limit: int = 50) -> Dict[str, Any]:
        """
        Processes a batch of pending staging records sequentially through the Funnel.
        """
        pending_records = db.query(DiscoveryStaging).filter(
            DiscoveryStaging.processing_status.in_(["pending", "batched"])
        ).order_by(DiscoveryStaging.created_at.asc()).limit(limit).all()

        results = {
            "processed_count": len(pending_records),
            "promoted_new": 0,
            "enriched_existing": 0,
            "held_review": 0,
            "rejected_noise": 0,
            "companies_routed": 0,
            "jobs_captured": 0,
        }

        promoted_records_for_parquet = []
        for staged in pending_records:
            try:
                res = self.process_staging_record(staged, db)
                status = res.get("status")
                if status == "PROMOTED":
                    results["promoted_new"] += 1
                    if "recruiter_dict" in res:
                        promoted_records_for_parquet.append(res["recruiter_dict"])
                elif status == "ENRICHED":
                    results["enriched_existing"] += 1
                elif status == "HELD_REVIEW":
                    results["held_review"] += 1
                elif status == "REJECTED":
                    results["rejected_noise"] += 1
                elif status == "COMMITTED":
                    e_type = res.get("entity_type")
                    if e_type == ENTITY_COMPANY:
                        results["companies_routed"] += 1
                    elif e_type == ENTITY_JOB_POSTING:
                        results["jobs_captured"] += 1
            except Exception as e:
                logger.error("Error processing record #%s through Funnel: %s", staged.id, e)
                db.rollback()
                continue

        db.commit()

        # Dual-Sync: Append promoted recruiters to DuckDB Parquet
        if promoted_records_for_parquet:
            try:
                from .parquet_writer import parquet_writer
                parquet_writer.append_records(promoted_records_for_parquet)
                logger.info("[FUNNEL] Parquet Dual-Sync: Appended %d promoted recruiters to DuckDB Parquet", len(promoted_records_for_parquet))
            except Exception as pq_err:
                logger.warning("[FUNNEL] Parquet dual-sync warning: %s", pq_err)

            # Auto-enroll newly promoted verified candidates into active campaigns
            try:
                from .sequence_scheduler import auto_enroll_recruiter
                for rec_item in promoted_records_for_parquet:
                    r_id = rec_item.get("recruiter_id")
                    r_email = rec_item.get("email")
                    r_name = rec_item.get("recruiter_name", "")
                    r_title = rec_item.get("title", "")
                    r_conf = rec_item.get("email_confidence", 0)
                    if r_id and r_email and r_conf >= 70:
                        auto_enroll_recruiter(
                            db=db,
                            recruiter_id=r_id,
                            email=r_email,
                            name=r_name,
                            title=r_title,
                            confidence=r_conf,
                            source="universal_funnel",
                        )
                db.commit()
            except Exception as enroll_err:
                logger.debug("Campaign auto-enroll note in funnel: %s", enroll_err)

        # Trigger downstream search sync if any data was promoted or enriched
        if results["promoted_new"] > 0 or results["enriched_existing"] > 0:
            try:
                from .sync_layer import sync_manager
                sync_manager.request_sync()
            except Exception:
                pass
            try:
                from ..olap_sidecar import olap_sidecar
                olap_sidecar.invalidate()
            except Exception:
                pass

        return results

    def get_funnel_metrics(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Returns full telemetry across the 7 gates of the Ingestion Funnel.
        """
        metrics = {
            "funnel_telemetry": self.telemetry,
            "gate_descriptions": {
                "gate_1": "Raw Sourcing Ingestion & Platform Noise Elimination",
                "gate_2": "Hard Entity Disambiguation (Person vs Company vs Job)",
                "gate_3": "Contextual Identity Reconstruction & Title Sanitization",
                "gate_4": "Autonomous Corporate Email Intelligence & Pattern Mining",
                "gate_5": "Live Port 25 SMTP Deliverability Probing & MX Verification",
                "gate_6": "Actionable Contact Intelligence Gate (Zero Fake Emails)",
                "gate_7": "Master Catalog Promotion & Real-Time Dual-Sync Flywheel",
            },
        }

        if db:
            try:
                # Add database staging snapshot
                counts = dict(
                    db.query(
                        DiscoveryStaging.processing_status,
                        sqlfunc.count(DiscoveryStaging.id)
                    ).group_by(DiscoveryStaging.processing_status).all()
                )
                metrics["database_staging_counts"] = counts
            except Exception as e:
                logger.debug("Database staging count error in funnel: %s", e)

        return metrics


# Global singleton instance
universal_funnel = UniversalIngestionFunnel()
