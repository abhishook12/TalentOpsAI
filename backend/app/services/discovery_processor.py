import re
import json
import logging
import secrets
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from ..models.staging_models import DiscoveryStaging, ResolvedPerson
from ..models.models import Recruiter, Company, RecruiterEmail, RecruiterPhone, RecruiterLocation
from ..models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from ..models.extension_models import ExtensionDiscoveryEvent
from ..utils.normalizer import (
    normalize_text,
    extract_domain,
    is_ui_action,
    is_platform_name,
    is_job_posting_title,
    validate_human_name,
    validate_company_for_person,
    classify_page_type,
    clean_title,
    clean_company,
    clean_location_text,
    split_title_and_company,
    calculate_field_confidences,
    evaluate_evidence_grounding,
    build_semantic_graph_document,
    SEMANTIC_TYPE_REGISTRY,
    UI_ACTION_TERMS,
    PLATFORM_NAMES,
    is_company_name,
    is_valid_email,
)
from ..utils.title_normalizer import classify_title
from ..utils.state_recovery import infer_state_from_sources
from .email_intelligence_service import email_intelligence

logger = logging.getLogger('talentops.discovery_processor')

# Identity confidence thresholds
CONFIDENCE_VERY_STRONG = 0.95  # LinkedIn URL or verified corporate email match
CONFIDENCE_STRONG = 0.80       # Phone+name or name+company+location
CONFIDENCE_MODERATE = 0.60     # Name+company only
CONFIDENCE_WEAK = 0.40         # Name-only match

# Decision thresholds
AUTO_COMMIT_THRESHOLD = 0.70   # >= this -> auto-commit (NEW or ENRICH)
REVIEW_THRESHOLD = 0.40        # >= this but < AUTO_COMMIT -> REVIEW
IGNORE_THRESHOLD = 0.40        # < this -> IGNORE

# Usefulness threshold
MIN_USEFULNESS_SCORE = 35

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'live.com', 'msn.com', 'me.com', 'mail.com',
    'protonmail.com', 'ymail.com', 'comcast.net', 'att.net',
    'noemail.talentops',
}

BOGUS_COMPANY_NAMES = {
    'home', 'feed', 'jobright', 'chatgpt', 'chat', 'turboscribe', 
    'email id table', 'ats', 'at', 'gemini', 'guided search partners', 
    'guided search', "i'm locking", "i''m locking", 'overview', 'employees', 
    'active window', 'candidate card', 'quick search', 'homepage', 'inbox', 
    'contacts', 'search', 'notifications', 'network', 'jobs', 'messaging', 
    'me', 'format text', 'sent items', 'address book', 'ctv- phone',
    'chelsie walsh', 'kelly moran', 'jeff thomas', 'brenda geisler',
    'cotamt', 'cotamt fim any', 'cotamt fim', 'fim any', 'fim',
    'contact info', 'contact details', 'contact profile', 'mutual connections',
    'see all connections', 'any'
}


class DiscoveryProcessor:
    def __init__(self, db: Session):
        self.db = db

    def process_pending_batch(self, limit: int = 100) -> dict:
        """
        Process pending staging records in batches.
        Runs Evidence Grounding Gate, clusters valid records, resolves entities,
        matches against master DB, makes decisions, and updates DB.
        """
        try:
            records = self.db.query(DiscoveryStaging).filter(
                DiscoveryStaging.processing_status.in_(['pending', 'batched'])
            ).order_by(DiscoveryStaging.created_at.asc()).limit(limit).all()

            if not records:
                return {
                    'processed': 0,
                    'new': 0,
                    'enriched': 0,
                    'duplicate': 0,
                    'review': 0,
                    'ignored': 0,
                    'conflict': 0,
                    'rejected': 0,
                }

            # 1. HARD GATE: Evidence Grounding Check on Every Observation
            grounded_records = []
            rejected_count = 0

            for r in records:
                grounding = evaluate_evidence_grounding(
                    raw_name=r.raw_name,
                    raw_title=r.raw_title,
                    raw_company=r.raw_company,
                    page_url=r.source_url,
                    page_title=r.source_page_title,
                    entity_type=getattr(r, 'entity_type', None),
                )

                if not grounding["is_grounded"]:
                    # REJECT UNGROUNDED CLAIM: Never touch master DB
                    r.processing_status = 'rejected'
                    r.decision = 'REJECT_UNGROUNDED'
                    r.decision_reason = "; ".join(grounding["rejection_reasons"])
                    r.identity_confidence = 0.0
                    r.processed_at = datetime.now(timezone.utc)
                    self.db.add(r)
                    rejected_count += 1
                else:
                    # Additional: Validate company name isn't system noise; if invalid, sanitize to None (do NOT reject human candidate)
                    if r.raw_company:
                        comp_valid, comp_reason = validate_company_for_person(
                            r.raw_company, person_name=r.raw_name
                        )
                        if not comp_valid:
                            logger.info("Sanitizing noise company '%s' for candidate '%s': %s", r.raw_company, r.raw_name, comp_reason)
                            r.raw_company = None
                    r.processing_status = 'batched'
                    grounded_records.append(r)

            self.db.commit()

            if not grounded_records:
                return {
                    'processed': len(records),
                    'new': 0,
                    'enriched': 0,
                    'duplicate': 0,
                    'review': 0,
                    'ignored': 0,
                    'conflict': 0,
                    'rejected': rejected_count,
                }

            # 1b. HARD INVARIANT: Separate Company/Organization Entities from Person Observations
            from ..utils.normalizer import is_company_name, is_company_industry
            candidate_records = []
            company_committed_count = 0

            for r in grounded_records:
                is_comp = (
                    is_company_name(r.raw_name) or
                    (r.source_url and '/company/' in r.source_url and not r.raw_email and not r.raw_phone and (not r.raw_linkedin or '/company/' in r.raw_linkedin))
                )

                if is_comp:
                    # Commit directly to Company table (NEVER create a fake recruiter)
                    comp_name = r.raw_name or r.raw_company
                    if comp_name:
                        comp_name = clean_company(comp_name) or comp_name.strip()
                    if comp_name and comp_name.lower().strip() not in BOGUS_COMPANY_NAMES:
                        existing_comp = self.db.query(Company).filter(
                            Company.company_name.ilike(comp_name)
                        ).first()

                        comp_website = None
                        if r.metadata_json:
                            try:
                                m_dict = json.loads(r.metadata_json)
                                comp_website = m_dict.get('website')
                            except Exception:
                                pass

                        if not existing_comp:
                            new_comp = Company(
                                company_name=comp_name,
                                canonical_name=comp_name,
                                industry=r.raw_title or None,
                                location=r.raw_location or None,
                                website=comp_website,
                                linkedin_url=r.raw_linkedin or None,
                                metadata_json=r.metadata_json or None,
                                verification_status="verified_extension",
                                trust_score=90,
                                data_source="extension_company_extractor",
                            )
                            self.db.add(new_comp)
                            self.db.flush()
                        else:
                            # Enrich existing company with incoming details
                            if not existing_comp.industry and r.raw_title:
                                existing_comp.industry = r.raw_title
                            if not existing_comp.location and r.raw_location:
                                existing_comp.location = r.raw_location
                            if not existing_comp.website and comp_website:
                                existing_comp.website = comp_website
                            if not existing_comp.linkedin_url and r.raw_linkedin:
                                existing_comp.linkedin_url = r.raw_linkedin
                            if not existing_comp.metadata_json and r.metadata_json:
                                existing_comp.metadata_json = r.metadata_json
                            self.db.add(existing_comp)
                            self.db.flush()

                        r.processing_status = 'committed'
                        r.decision = 'COMPANY_COMMITTED'
                        r.decision_reason = f'Recognized organizational entity: {comp_name}'
                        r.identity_confidence = 1.0
                        r.processed_at = datetime.now(timezone.utc)
                        self.db.add(r)
                        company_committed_count += 1
                else:
                    candidate_records.append(r)

            self.db.flush()

            # 2. Cluster candidate observations into person identities
            clusters = self._cluster_observations(candidate_records)
            decisions = []

            # 3. Resolve each cluster & match against master DB
            for cluster in clusters:
                resolved = self._resolve_cluster(cluster)
                match, conf = self._match_master_db(resolved)
                decision = self._make_decision(resolved, match, conf)
                decisions.append(decision)

            # 4. Execute decisions & commit
            stats = self._execute_decisions(decisions)
            stats['rejected'] = stats.get('rejected', 0) + rejected_count
            stats['companies_committed'] = company_committed_count

            # 5. Mark all staging records with processed timestamp
            for record in grounded_records:
                record.processed_at = datetime.now(timezone.utc)
                self.db.add(record)

            self.db.commit()

            # High-Speed Master DB Sync: Notify sync_manager so Parquet, DuckDB, and Search index refresh instantly
            if stats.get('new', 0) > 0 or stats.get('enriched', 0) > 0 or stats.get('companies_committed', 0) > 0:
                try:
                    from ..olap_sidecar import olap_sidecar
                    olap_sidecar.invalidate()
                except Exception as ie:
                    logger.debug("OlapSidecar invalidation note: %s", ie)
                try:
                    from .sync_layer import sync_manager
                    sync_manager.request_sync()
                    logger.info("Triggered real-time sync_manager reload for live search & DB consistency")
                except Exception as se:
                    logger.debug("SyncManager notification note: %s", se)
                try:
                    from ..routes.analytics import analytics_cache
                    analytics_cache.clear()
                    logger.info("Cleared analytics cache for immediate UI freshness")
                except Exception as ce:
                    logger.debug("AnalyticsCache clear note: %s", ce)

            stats['processed'] = len(records)
            logger.info("Discovery batch processed: %s", stats)
            return stats

        except Exception as e:
            logger.error("Error in batch processing: %s", e, exc_info=True)
            self.db.rollback()
            return {'processed': 0, 'error': str(e)}

    def _normalize_name(self, name: Optional[str]) -> str:
        if not name:
            return ""
        name = str(name).strip()
        # Remove degree connection bullets: "· 2nd", "• 1st", etc.
        name = re.sub(r'[·•]\s*\d+(?:st|nd|rd|th)?', '', name, flags=re.IGNORECASE)
        # Remove degree badges
        for badge in ['1st degree connection', '2nd degree connection', '3rd+ degree connection', '1st', '2nd', '3rd+', '3rd']:
            name = name.replace(badge, '')
        # Split on titles or separators (hyphens/pipes/em-dash)
        parts = re.split(r'[-–—|]', name)[0]
        cleaned = re.sub(r'[^\w\s\'.]', ' ', parts).strip()
        cleaned = " ".join(cleaned.split())
        return cleaned.title()

    def _normalize_linkedin(self, url: Optional[str]) -> str:
        if not url:
            return ""
        url = str(url).lower().strip()
        if 'linkedin.com/in/' in url:
            parts = url.split('linkedin.com/in/')
            if len(parts) > 1:
                slug = parts[1].split('/')[0].split('?')[0].rstrip('/')
                return slug
        return url.rstrip('/')

    def _normalize_email(self, email: Optional[str]) -> str:
        if not email:
            return ""
        email = str(email).lower().strip()
        if 'noemail.talentops' in email:
            return ""
        return email

    def _cluster_observations(self, records: List[DiscoveryStaging]) -> List[List[DiscoveryStaging]]:
        """
        Group staging records that refer to the same identity.
        Uses signal hierarchy: LinkedIn URL > Email > Phone+Name > Name+Company.
        """
        clusters: List[List[DiscoveryStaging]] = []

        for r in records:
            matched_cluster = None
            r_li = self._normalize_linkedin(getattr(r, "canonical_profile_url", None) or r.raw_linkedin or (r.source_url if r.source_url and "linkedin.com/in/" in r.source_url else None))
            r_email = self._normalize_email(r.raw_email)
            r_phone = normalize_text(r.raw_phone) if r.raw_phone else ""
            r_name = self._normalize_name(r.raw_name)
            r_company = normalize_text(r.raw_company) if r.raw_company else ""

            for cluster in clusters:
                c_li_set = {
                    self._normalize_linkedin(getattr(c, "canonical_profile_url", None) or c.raw_linkedin or (c.source_url if c.source_url and "linkedin.com/in/" in c.source_url else None))
                    for c in cluster
                    if getattr(c, "canonical_profile_url", None) or c.raw_linkedin or c.source_url
                }
                c_email_set = {self._normalize_email(c.raw_email) for c in cluster if c.raw_email}
                c_phone_set = {normalize_text(c.raw_phone) for c in cluster if c.raw_phone}
                c_name_set = {self._normalize_name(c.raw_name) for c in cluster if c.raw_name}
                c_comp_set = {normalize_text(c.raw_company) for c in cluster if c.raw_company}

                # 1. Very Strong: Same LinkedIn URL
                if r_li and r_li in c_li_set:
                    matched_cluster = cluster
                    break

                # 2. Very Strong: Same Real Email
                if r_email and r_email in c_email_set:
                    matched_cluster = cluster
                    break

                # 3. Strong: Same Phone + Compatible Name
                if r_phone and r_phone in c_phone_set and r_name and any(r_name.lower() in cn.lower() or cn.lower() in r_name.lower() for cn in c_name_set):
                    matched_cluster = cluster
                    break

                # 4. Moderate: Same Name + Same Company
                if r_name and r_name in c_name_set and r_company and r_company in c_comp_set:
                    matched_cluster = cluster
                    break

            if matched_cluster is not None:
                matched_cluster.append(r)
            else:
                clusters.append([r])

        return clusters

    UI_ACTION_TERMS = {
        'connect', 'contact', 'message', 'follow', 'following', 'pending',
        'see more', 'show all', 'view profile', 'more', 'save', 'endorse',
        'share', 'like', 'comment', 'send', 'withdraw', 'join', 'apply'
    }
    PLATFORM_NAMES = {'linkedin', 'indeed', 'glassdoor', 'ziprecruiter', 'monster'}

    def _resolve_cluster(self, cluster: List[DiscoveryStaging]) -> ResolvedPerson:
        """
        Consolidate a cluster of observations into a single ResolvedPerson entity.
        Calculates field-level confidences, extracts employment progression,
        and strictly eliminates UI action terms from titles and platform names from companies.
        """
        def most_common(items):
            valid = [i for i in items if i]
            if not valid:
                return None
            return max(set(valid), key=valid.count)

        # 1. Clean Title and Company across observations
        clean_titles = []
        clean_companies = []

        for r in cluster:
            t, c = split_title_and_company(
                raw_title=r.raw_title,
                raw_company=r.raw_company,
                page_context=r.source_page_title
            )

            if t and not is_ui_action(t):
                clean_titles.append(t)
            if c and not is_platform_name(c):
                clean_companies.append(c)

        # Most reliable values across observations
        raw_canonical = most_common([r.raw_name for r in cluster])
        canonical_name = self._normalize_name(raw_canonical) or "Unknown Professional"
        is_human, clean_human, _ = validate_human_name(canonical_name)
        if is_human and clean_human:
            canonical_name = clean_human

        primary_email = most_common([self._normalize_email(r.raw_email) for r in cluster])
        primary_phone = most_common([r.raw_phone for r in cluster])
        linkedin_url = most_common([r.raw_linkedin for r in cluster])
        raw_loc = most_common([r.raw_location for r in cluster])
        location = clean_location_text(raw_loc) or raw_loc

        # Progressive Profile Attributes
        education = most_common([getattr(r, "education", None) for r in cluster])
        followers_count = most_common([getattr(r, "followers_count", None) for r in cluster])
        connections_count = most_common([getattr(r, "connections_count", None) for r in cluster])
        about_summary = most_common([getattr(r, "about_summary", None) for r in cluster])
        
        # Merge progressive complex JSON fields (grab longest/richest)
        skills_opts = [getattr(r, "skills", None) for r in cluster if getattr(r, "skills", None)]
        skills = max(skills_opts, key=len) if skills_opts else None
        
        exp_opts = [getattr(r, "experience_history", None) for r in cluster if getattr(r, "experience_history", None)]
        experience_history = max(exp_opts, key=len) if exp_opts else None
        
        # Track employment history and job changes (Current vs Previous)
        previous_company = most_common([getattr(r, "previous_company", None) for r in cluster if getattr(r, "previous_company", None)])
        
        current_company = None
        if clean_companies:
            if previous_company:
                for comp in reversed(clean_companies):
                    if comp.lower() != previous_company.lower():
                        current_company = comp
                        break
            if not current_company:
                current_company = clean_companies[-1] # newest

        if not previous_company and clean_companies and len(set(clean_companies)) > 1:
            for comp in reversed(clean_companies[:-1]):
                if comp.lower() != current_company.lower():
                    previous_company = comp
                    break

        raw_current_title = clean_titles[-1] if clean_titles else "Professional"
        current_title_intel = classify_title(raw_current_title)
        current_title = current_title_intel["canonical_title"]

        previous_title = None
        if clean_titles and len(set(clean_titles)) > 1:
            for tit in reversed(clean_titles[:-1]):
                if tit.lower() != raw_current_title.lower() and tit.lower() != current_title.lower():
                    prev_intel = classify_title(tit)
                    previous_title = prev_intel["canonical_title"]
                    break

        # Fallback: if linkedin_url is not set, infer from source_url if individual profile URL
        if not linkedin_url:
            for r in cluster:
                if r.source_url and 'linkedin.com/in/' in r.source_url:
                    linkedin_url = r.source_url
                    break

        canonical_profile_url = most_common([getattr(r, "canonical_profile_url", None) for r in cluster]) or linkedin_url
        page_type = most_common([getattr(r, "page_type", None) for r in cluster])
        field_confidence_json = next((getattr(r, "field_confidence_json", None) for r in cluster if getattr(r, "field_confidence_json", None)), None)
        evidence_json = next((getattr(r, "evidence_json", None) for r in cluster if getattr(r, "evidence_json", None)), None)
        if not linkedin_url and canonical_profile_url and "linkedin.com/in/" in canonical_profile_url:
            linkedin_url = canonical_profile_url

        # Corporate Email Guesser & MX Verifier Enrichment
        email_intel_data = None
        if canonical_name and canonical_name != "Unknown Professional" and current_company:
            try:
                intel_res = email_intelligence.resolve_and_enrich_candidate(
                    full_name=canonical_name,
                    company_name=current_company,
                    existing_email=primary_email,
                    db=self.db
                )
                if intel_res and intel_res.get("email"):
                    email_intel_data = intel_res
                    if not primary_email or primary_email.endswith('@noemail.talentops'):
                        primary_email = intel_res["email"]
            except Exception as e:
                logger.debug("Candidate email intelligence resolution note: %s", e)

        # Calculate Identity Confidence Score
        conf = 0.0
        if canonical_name and canonical_name != "Unknown Professional":
            conf += 0.25
        if linkedin_url or canonical_profile_url:
            conf += 0.30
        if current_company:
            conf += 0.15
        if current_title and current_title.lower() not in self.UI_ACTION_TERMS:
            conf += 0.10
        if primary_email:
            conf += 0.15
        if primary_phone:
            conf += 0.10
        if location:
            conf += 0.05
        # Progressive profile attributes boost identity confidence
        if education:
            conf += 0.05
        if skills:
            conf += 0.05
        if experience_history:
            conf += 0.05

        has_platform_signal = any(
            (r.source_url and any(s in r.source_url.lower() for s in ["linkedin", "zoominfo", "apollo", "indeed", "chat.google", "teams", "simplyhired", "glassdoor", "wellfound", "dice", "hired", "lever", "github"]))
            or (r.source_page_title and any(s in r.source_page_title.lower() for s in ["linkedin", "zoominfo", "apollo", "indeed", "- chat", "teams", "simplyhired", "glassdoor", "wellfound", "dice", "hired", "lever", "github"]))
            or (getattr(r, "extraction_source", None) and any(s in str(r.extraction_source).lower() for s in ["chat", "teams", "linkedin", "dice", "hired", "wellfound"]))
            for r in cluster
        )
        if not (linkedin_url or canonical_profile_url) and has_platform_signal:
            conf += 0.20

        conf = min(conf, 1.0)

        # Field-level confidences (0-100)
        obs_count = len(cluster)
        name_conf = int((sum(1 for r in cluster if r.raw_name) / obs_count) * 100)
        title_conf = int((sum(1 for r in cluster if r.raw_title) / obs_count) * 100)
        comp_conf = int((sum(1 for r in cluster if r.raw_company) / obs_count) * 100)
        email_conf = int((sum(1 for r in cluster if r.raw_email) / obs_count) * 100)
        if email_intel_data and email_intel_data.get("email"):
            email_conf = max(email_conf, int(email_intel_data.get("confidence", 0.8) * 100))
        phone_conf = int((sum(1 for r in cluster if r.raw_phone) / obs_count) * 100)

        # Aggregate metadata_json (badges, firmographics, channels, title intelligence)
        meta_dict = {}
        if email_intel_data:
            meta_dict["email_intel"] = email_intel_data
        for r in cluster:
            if getattr(r, "metadata_json", None) and isinstance(r.metadata_json, str) and r.metadata_json.startswith("{"):
                try:
                    m = json.loads(r.metadata_json)
                    for k, v in m.items():
                        if v is not None and k not in meta_dict:
                            meta_dict[k] = v
                except Exception:
                    pass

        # Attach structured Title Intelligence to ResolvedPerson
        meta_dict["title_intel"] = {
            "canonical_title": current_title_intel["canonical_title"],
            "raw_title": raw_current_title,
            "seniority_level": current_title_intel["seniority_level"],
            "seniority_score": current_title_intel["seniority_score"],
            "legacy_seniority": current_title_intel["legacy_seniority"],
            "domain_specialization": current_title_intel["domain_specialization"],
            "specialization_label": current_title_intel["specialization_label"],
            "role_family": current_title_intel["role_family"],
            "is_people_manager": current_title_intel["is_people_manager"],
        }
        metadata_json_str = json.dumps(meta_dict)

        owner_user_id = cluster[0].owner_user_id if cluster else 1

        # Reject bogus company names from factorizing as employers
        if current_company and current_company.lower().strip() in BOGUS_COMPANY_NAMES:
            current_company = None
        if previous_company and previous_company.lower().strip() in BOGUS_COMPANY_NAMES:
            previous_company = None

        person = ResolvedPerson(
            owner_user_id=owner_user_id,
            canonical_name=canonical_name,
            current_title=current_title,
            current_company=current_company,
            previous_title=previous_title,
            previous_company=previous_company,
            primary_email=primary_email,
            primary_phone=primary_phone,
            linkedin_url=linkedin_url,
            location=location,
            education=education,
            followers_count=followers_count,
            connections_count=connections_count,
            about_summary=about_summary,
            skills=skills,
            experience_history=experience_history,
            metadata_json=metadata_json_str,
            page_type=page_type,
            canonical_profile_url=canonical_profile_url,
            field_confidence_json=field_confidence_json,
            evidence_json=evidence_json,
            identity_confidence=round(conf, 2),
            observation_count=obs_count,
            name_confidence=name_conf,
            title_confidence=title_conf,
            company_confidence=comp_conf,
            email_confidence=email_conf,
            phone_confidence=phone_conf,
        )

        self.db.add(person)
        self.db.flush()

        # Link staging records to this resolved person
        for r in cluster:
            r.resolved_person_id = person.id
            r.identity_confidence = round(conf, 2)
            r.quality_score = self._calculate_usefulness(r)
            self.db.add(r)
        self.db.flush()

        return person

    def _match_master_db(self, person: ResolvedPerson) -> Tuple[Optional[Recruiter], float]:
        """
        Matches a ResolvedPerson against existing master `recruiters` table.
        Returns (matched_recruiter, match_confidence).
        """
        # 1. Match by Canonical Profile URL or LinkedIn URL (Very Strong: 0.95)
        prof_url = getattr(person, "canonical_profile_url", None) or person.linkedin_url
        if prof_url:
            slug = self._normalize_linkedin(prof_url)
            if slug and len(slug) > 3:
                match = self.db.query(Recruiter).filter(
                    Recruiter.linkedin.ilike(f"%{slug}%")
                ).first()
                if match:
                    return match, CONFIDENCE_VERY_STRONG

        # 2. Match by Verified Email (Very Strong: 0.95)
        if person.primary_email:
            match = self.db.query(Recruiter).filter(
                Recruiter.email == person.primary_email.strip().lower()
            ).first()
            if match:
                return match, CONFIDENCE_VERY_STRONG

        # 3. Match by Name + Company / Phone
        if person.canonical_name and person.canonical_name != "Unknown Professional":
            norm_name = normalize_text(person.canonical_name)
            candidates = self.db.query(Recruiter).filter(
                (Recruiter.normalized_recruiter_name == norm_name) |
                (Recruiter.recruiter_name.ilike(f"%{person.canonical_name.strip()}%"))
            ).limit(20).all()

            for c in candidates:
                c_norm_name = normalize_text(c.recruiter_name)
                if c_norm_name == norm_name:
                    # If both have LinkedIn profiles and they differ, they are definitively distinct people!
                    if c.linkedin and person.linkedin_url:
                        c_slug = self._normalize_linkedin(c.linkedin)
                        p_slug = self._normalize_linkedin(person.linkedin_url)
                        if c_slug and p_slug and c_slug != p_slug:
                            continue

                    # If both have corporate emails and domains differ, and companies differ
                    if c.email and person.primary_email:
                        c_domain = c.email.split('@')[-1].lower() if '@' in c.email else ''
                        p_domain = person.primary_email.split('@')[-1].lower() if '@' in person.primary_email else ''
                        if c_domain and p_domain and c_domain != p_domain and c_domain not in FREE_EMAIL_DOMAINS and p_domain not in FREE_EMAIL_DOMAINS:
                            c_comp = c.company.company_name if c.company else None
                            if person.current_company and c_comp and normalize_text(person.current_company) != normalize_text(c_comp):
                                continue

                    # Same phone match -> 0.80
                    if person.primary_phone and c.phone and normalize_text(c.phone) == normalize_text(person.primary_phone):
                        return c, CONFIDENCE_STRONG

                    # Same company match -> 0.75
                    c_comp_name = c.company.company_name if c.company else None
                    if person.current_company and c_comp_name:
                        if normalize_text(person.current_company) == normalize_text(c_comp_name):
                            return c, 0.75

            # Weak name-only matches (only if person has NO unique identifiers like LinkedIn or verified email)
            if not person.linkedin_url and not person.primary_email:
                for c in candidates:
                    if normalize_text(c.recruiter_name) == norm_name:
                        return c, CONFIDENCE_WEAK

        # 4. Search DuckDB Parquet recruiter_store (the 437,933 canonical master database)
        try:
            from .recruiter_store import recruiter_store
            recruiter_store._ensure_loaded()
            conn = recruiter_store._get_conn()
            if conn:
                matched_row = None
                conf = 0.0

                # A. Match by LinkedIn slug in Parquet
                if person.linkedin_url:
                    slug = self._normalize_linkedin(person.linkedin_url)
                    if slug and len(slug) > 3:
                        res = conn.execute(
                            "SELECT recruiter_id, recruiter_name, email, linkedin, phone, title, company_id, location, specialization FROM recruiters WHERE linkedin ILIKE ? LIMIT 1",
                            [f"%{slug}%"]
                        ).fetchone()
                        if res:
                            matched_row = res
                            conf = CONFIDENCE_VERY_STRONG

                # B. Match by verified email in Parquet
                if not matched_row and person.primary_email and "noemail" not in person.primary_email.lower():
                    res = conn.execute(
                        "SELECT recruiter_id, recruiter_name, email, linkedin, phone, title, company_id, location, specialization FROM recruiters WHERE LOWER(email) = ? LIMIT 1",
                        [person.primary_email.strip().lower()]
                    ).fetchone()
                    if res:
                        matched_row = res
                        conf = CONFIDENCE_VERY_STRONG

                # C. Match by Name + Company in Parquet
                if not matched_row and person.canonical_name and person.canonical_name != "Unknown Professional":
                    c_rows = conn.execute(
                        "SELECT recruiter_id, recruiter_name, email, linkedin, phone, title, company_id, location, specialization FROM recruiters WHERE LOWER(recruiter_name) LIKE ? LIMIT 10",
                        [f"%{person.canonical_name.strip().lower()}%"]
                    ).fetchall()
                    norm_name = normalize_text(person.canonical_name)
                    for r_row in c_rows:
                        if normalize_text(r_row[1]) == norm_name:
                            if person.current_company and r_row[6] and normalize_text(person.current_company) == normalize_text(str(r_row[6])):
                                matched_row = r_row
                                conf = 0.75
                                break

                if matched_row:
                    r_id, r_name, r_email, r_li, r_phone, r_title, r_comp, r_loc, r_spec = matched_row
                    # Check if already imported into PostgreSQL
                    existing_pg = self.db.query(Recruiter).filter(
                        (Recruiter.recruiter_name == r_name) | (Recruiter.email == r_email)
                    ).first()
                    if existing_pg:
                        return existing_pg, conf

                    if not r_email or r_email.endswith("@noemail.talentops"):
                        return None, 0.0

                    # Find or create company
                    c_id = None
                    if r_comp and str(r_comp).strip().lower() not in BOGUS_COMPANY_NAMES:
                        c_obj = self.db.query(Company).filter(Company.company_name.ilike(str(r_comp).strip())).first()
                        if not c_obj:
                            c_obj = Company(company_name=str(r_comp).strip(), canonical_name=str(r_comp).strip(), trust_score=80)
                            self.db.add(c_obj)
                            self.db.flush()
                        c_id = c_obj.company_id

                    # Hydrate canonical recruiter into PostgreSQL so it can be enriched
                    hydrated_rec = Recruiter(
                        recruiter_name=r_name,
                        email=r_email,
                        linkedin=r_li,
                        phone=r_phone,
                        title=r_title or "Recruiter",
                        specialization=r_spec,
                        company_id=c_id,
                        location=r_loc,
                        data_source="parquet_canonical",
                        is_active=True,
                        needs_review=False,
                        trust_score=85,
                    )
                    self.db.add(hydrated_rec)
                    self.db.flush()
                    logger.info("Hydrated canonical master recruiter from Parquet into PostgreSQL: %s (ID %s)", r_name, hydrated_rec.recruiter_id)
                    return hydrated_rec, conf

        except Exception as se:
            logger.debug("Parquet master matching note: %s", se)

        return None, 0.0

    def _make_decision(self, person: ResolvedPerson, master_match: Optional[Recruiter], match_confidence: float) -> dict:
        """
        Determines the decision outcome:
        NEW, ENRICH, DUPLICATE, CONFLICT, REVIEW, or IGNORE.
        """
        if person.identity_confidence < IGNORE_THRESHOLD and not (person.primary_email or person.linkedin_url or person.primary_phone):
            return {
                'person': person,
                'recruiter': master_match,
                'decision': 'IGNORE',
                'reason': 'Insufficient identifying signals across observations',
            }

        # Case 1: No match in master DB
        if not master_match:
            # Hard Gate: Verify candidate is a genuine human name before auto-committing NEW recruiter
            is_human_candidate, clean_cand_name, human_reason = validate_human_name(person.canonical_name)
            if not is_human_candidate or person.canonical_name == "Unknown Professional":
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'REVIEW',
                    'reason': f'INVALID_HUMAN_NAME: {human_reason or "Unknown candidate name"} — held in Review Queue before mainline commitment',
                }
            if clean_cand_name and clean_cand_name != person.canonical_name:
                person.canonical_name = clean_cand_name

            has_strong_profile = bool(
                (person.linkedin_url and "linkedin.com/in/" in person.linkedin_url)
                or (getattr(person, "canonical_profile_url", None) and "linkedin.com/in/" in str(person.canonical_profile_url))
            )
            has_verified_email = bool(
                person.primary_email and not person.primary_email.endswith("@noemail.talentops") and is_valid_email(person.primary_email)
            )
            has_contact = bool(has_verified_email or person.primary_phone)
            has_clean_company = bool(person.current_company and person.current_company.lower().strip() not in BOGUS_COMPANY_NAMES)
            has_employment = bool(person.current_title and has_clean_company)
            has_primary_anchor = bool(has_strong_profile or has_contact or has_employment)

            # Evaluate candidates for auto-commitment to the main line (Recruiters table)
            if has_primary_anchor and has_verified_email and (person.identity_confidence >= AUTO_COMMIT_THRESHOLD or (has_employment and person.identity_confidence >= 0.65)):
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'NEW',
                    'reason': f'High-confidence new candidate entity with primary anchor (score {person.identity_confidence:.2f})',
                }
            elif has_strong_profile and (has_employment or person.identity_confidence >= 0.70):
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'NEW',
                    'reason': f'Verified profile entity discovered via Scout (score {person.identity_confidence:.2f})',
                }
            elif has_employment and person.identity_confidence >= 0.70:
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'NEW',
                    'reason': f'Corroborated employment entity discovered via Scout (score {person.identity_confidence:.2f})',
                }
            elif has_employment and not has_strong_profile and not has_verified_email:
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'REVIEW',
                    'reason': f'TITLE_COMPANY_ONLY: Corroborated title & company found, but held in Review Queue awaiting stable profile URL or verified email (confidence {person.identity_confidence:.2f})',
                }
            elif has_primary_anchor and not has_verified_email:
                if person.identity_confidence >= 0.60:
                    return {
                        'person': person,
                        'recruiter': None,
                        'decision': 'NEW',
                        'reason': f'Candidate entity discovered via Scout (score {person.identity_confidence:.2f})',
                    }
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'REVIEW',
                    'reason': f'Awaiting verified deliverable email enrichment (confidence {person.identity_confidence:.2f})',
                }
            else:
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'REVIEW',
                    'reason': f'MISSING_STABLE_ANCHOR: Insufficient anchors or confidence ({person.identity_confidence:.2f}) — human verification required',
                }

        # Case 2: Master match found
        new_fields = []
        # Email enrichment (also upgrades from placeholder @noemail)
        if person.primary_email and (not master_match.email or master_match.email.endswith('@noemail.talentops')):
            if not master_match.email or master_match.email.lower() != person.primary_email.lower():
                new_fields.append('email')
        if person.primary_phone and not master_match.phone:
            new_fields.append('phone')
        if person.linkedin_url and not master_match.linkedin:
            new_fields.append('linkedin')

        # Title change / promotion detection
        has_new_title = False
        if person.current_title and master_match.title:
            if master_match.title in ("Recruiter", "Professional") or normalize_text(person.current_title) != normalize_text(master_match.title):
                has_new_title = True
                new_fields.append('title')
        elif person.current_title and not master_match.title:
            has_new_title = True
            new_fields.append('title')

        if person.location and not master_match.location:
            new_fields.append('location')

        # Company change detection
        has_new_company = False
        m_comp_name = master_match.company.company_name if master_match.company else None
        if person.current_company:
            if not m_comp_name or normalize_text(person.current_company) != normalize_text(m_comp_name):
                has_new_company = True
                new_fields.append('company')

        # Deep Profile Progressive Field Checks
        import json
        meta = json.loads(master_match.metadata_json) if master_match.metadata_json else {}
        if person.education and not meta.get("education"):
            new_fields.append('education')
        if person.skills:
            try:
                inc_skills = json.loads(person.skills) if isinstance(person.skills, str) else person.skills
                exist_skills = meta.get("skills") or []
                if not exist_skills or len(inc_skills) > len(exist_skills):
                    new_fields.append('skills')
            except Exception:
                new_fields.append('skills')

        if person.experience_history:
            try:
                inc_exp = json.loads(person.experience_history) if isinstance(person.experience_history, str) else person.experience_history
                exist_exp = meta.get("experience_history") or []
                if not exist_exp or len(inc_exp) > len(exist_exp):
                    new_fields.append('experience')
            except Exception:
                new_fields.append('experience')

        if person.about_summary:
            exist_about = meta.get("about_summary") or ""
            if not exist_about or len(person.about_summary) > len(exist_about) + 15:
                new_fields.append('about_summary')

        # Conflict checks: Contradictory LinkedIn URLs
        if master_match.linkedin and person.linkedin_url:
            m_slug = self._normalize_linkedin(master_match.linkedin)
            p_slug = self._normalize_linkedin(person.linkedin_url)
            if m_slug and p_slug and m_slug != p_slug:
                return {
                    'person': person,
                    'recruiter': master_match,
                    'decision': 'CONFLICT',
                    'reason': f'Conflicting LinkedIn profiles: Master has "{master_match.linkedin}" vs Staged "{person.linkedin_url}"',
                }

        # Conflict checks: Contradictory corporate email domains (ignore dummy noemail.talentops)
        if master_match.email and not master_match.email.endswith('@noemail.talentops') and person.primary_email:
            m_domain = master_match.email.split('@')[-1].lower() if '@' in master_match.email else ''
            p_domain = person.primary_email.split('@')[-1].lower() if '@' in person.primary_email else ''
            if m_domain and p_domain and m_domain != p_domain:
                if m_domain not in FREE_EMAIL_DOMAINS and p_domain not in FREE_EMAIL_DOMAINS and not has_new_company:
                    return {
                        'person': person,
                        'recruiter': master_match,
                        'decision': 'CONFLICT',
                        'reason': f'Conflicting corporate email domains: @{m_domain} vs @{p_domain}',
                    }

        # Outcome: ENRICH
        if (len(new_fields) > 0 or has_new_company) and match_confidence >= 0.60:
            reason_str = f"Discovered new attributes: {', '.join(new_fields)}"
            if has_new_company and m_comp_name:
                reason_str += f" (Employer transition detected: {m_comp_name} -> {person.current_company})"
            return {
                'person': person,
                'recruiter': master_match,
                'decision': 'ENRICH',
                'reason': reason_str,
            }

        # Outcome: DUPLICATE
        if len(new_fields) == 0 and match_confidence >= 0.60:
            return {
                'person': person,
                'recruiter': master_match,
                'decision': 'DUPLICATE',
                'reason': 'Record already exists with identical or subset attributes',
            }

        # If match was weak (< 0.60, e.g. name only match of 0.40) and candidate has distinct attributes
        if match_confidence < 0.60 and person.canonical_name and person.canonical_name != "Unknown Professional" and (person.current_company or person.current_title or person.linkedin_url or getattr(person, "canonical_profile_url", None)):
            return {
                'person': person,
                'recruiter': None,
                'decision': 'NEW',
                'reason': f'Distinct candidate entity (weak name-only match {match_confidence:.2f} with existing recruiter {master_match.recruiter_id})',
            }

        # Outcome: REVIEW
        return {
            'person': person,
            'recruiter': master_match,
            'decision': 'REVIEW',
            'reason': f'Uncertain match confidence ({match_confidence:.2f}) — manual review recommended',
        }

    def _execute_decisions(self, decisions: List[dict]) -> dict:
        """
        Executes decision actions, applies master DB updates, and creates audit events.
        """
        stats = {'new': 0, 'enriched': 0, 'duplicate': 0, 'review': 0, 'ignored': 0, 'conflict': 0}

        for d in decisions:
            person = d['person']
            recruiter = d['recruiter']
            decision = d['decision']
            reason = d.get('reason', '')

            # Update staging records
            staging_records = self.db.query(DiscoveryStaging).filter(
                DiscoveryStaging.resolved_person_id == person.id
            ).all()

            for r in staging_records:
                r.decision = decision
                r.decision_reason = reason
                if decision in ('REVIEW', 'CONFLICT'):
                    r.processing_status = 'review'
                elif decision == 'IGNORE':
                    r.processing_status = 'rejected'
                else:
                    r.processing_status = 'committed'

            # Execute master database modifications
            if decision == 'NEW':
                is_human_cand, clean_cand_nm, _ = validate_human_name(person.canonical_name)
                if not is_human_cand or person.canonical_name == "Unknown Professional":
                    stats['review'] += 1
                    continue
                if clean_cand_nm:
                    person.canonical_name = clean_cand_nm

                stats['new'] += 1
                company_id = None

                clean_target_comp = clean_company(person.current_company)
                if clean_target_comp and clean_target_comp.lower().strip() in BOGUS_COMPANY_NAMES:
                    clean_target_comp = None

                clean_loc = clean_location_text(person.location) or person.location
                inferred_st_res = infer_state_from_sources([
                    ("recruiter_location", clean_loc),
                    ("notes", person.about_summary),
                    ("metadata_json", person.metadata_json),
                ])
                inferred_st = inferred_st_res["state"] if inferred_st_res else None
                clean_city = None
                if clean_loc:
                    c_parts = [p.strip() for p in clean_loc.split(",") if p.strip()]
                    if c_parts:
                        clean_city = c_parts[0].lower()

                # Resolve or create company
                if person.primary_email and '@' in person.primary_email:
                    email_domain = person.primary_email.split('@')[-1].lower()
                    if email_domain not in FREE_EMAIL_DOMAINS:
                        comp = self.db.query(Company).filter(
                            Company.primary_domain == email_domain
                        ).first()
                        if comp:
                            company_id = comp.company_id
                            if not comp.state and inferred_st:
                                comp.state = inferred_st
                                self.db.add(comp)
                            if not comp.location and clean_loc:
                                comp.location = clean_loc
                                self.db.add(comp)
                        elif clean_target_comp:
                            new_comp = Company(
                                company_name=clean_target_comp,
                                canonical_name=clean_target_comp,
                                primary_domain=email_domain,
                                website=f"https://{email_domain}",
                                location=clean_loc,
                                state=inferred_st,
                                verification_status="unverified",
                                trust_score=75,
                                data_source="extension_staged",
                            )
                            self.db.add(new_comp)
                            self.db.flush()
                            company_id = new_comp.company_id

                if not company_id and clean_target_comp:
                    comp = self.db.query(Company).filter(
                        Company.company_name.ilike(clean_target_comp)
                    ).first()
                    if comp:
                        company_id = comp.company_id
                        if not comp.state and inferred_st:
                            comp.state = inferred_st
                            self.db.add(comp)
                        if not comp.location and clean_loc:
                            comp.location = clean_loc
                            self.db.add(comp)
                    else:
                        new_comp = Company(
                            company_name=clean_target_comp,
                            canonical_name=clean_target_comp,
                            location=clean_loc,
                            state=inferred_st,
                            verification_status="unverified",
                            trust_score=70,
                            data_source="extension_staged",
                        )
                        self.db.add(new_comp)
                        self.db.flush()
                        company_id = new_comp.company_id

                # Guard: Never insert an organization/company as a human Recruiter
                if is_company_name(person.canonical_name):
                    c_name = clean_company(person.canonical_name) or person.canonical_name.strip()
                    if c_name.lower() in BOGUS_COMPANY_NAMES:
                        continue
                    c_match = self.db.query(Company).filter(Company.company_name.ilike(c_name)).first()
                    co_meta = {}
                    if getattr(person, "metadata_json", None):
                        try:
                            co_meta = json.loads(person.metadata_json) if isinstance(person.metadata_json, str) else dict(person.metadata_json)
                        except Exception:
                            pass
                    if not c_match:
                        c_match = Company(
                            company_name=c_name,
                            canonical_name=c_name,
                            verification_status="verified_extension",
                            trust_score=90,
                            data_source="extension_company_extractor",
                            metadata_json=json.dumps(co_meta) if co_meta else None
                        )
                        self.db.add(c_match)
                        self.db.flush()
                    elif co_meta and not c_match.metadata_json:
                        c_match.metadata_json = json.dumps(co_meta)
                        self.db.add(c_match)
                    continue

                # Generate deliverable email or deterministic synthetic provisional email
                if not person.primary_email or person.primary_email.endswith('@noemail.talentops'):
                    raw_slug = re.sub(r'[^a-z0-9]', '.', (person.canonical_name or "candidate").strip().lower())
                    slug = re.sub(r'\.+', '.', raw_slug).strip('.') or "candidate"
                    id_seed = f"{person.owner_user_id}_{person.canonical_name}_{person.current_company}_{person.linkedin_url}_{person.id}"
                    hash_suffix = hashlib.sha256(id_seed.encode('utf-8')).hexdigest()[:8]
                    fallback_email = f"{slug}_{hash_suffix}@noemail.talentops"
                    needs_review_val = True
                    review_reason_val = "Discovered via Scout (awaiting email enrichment)"
                else:
                    fallback_email = person.primary_email.strip().lower()
                    needs_review_val = bool(person.identity_confidence < 0.85)
                    review_reason_val = "Low confidence identity" if needs_review_val else None

                # Defensive check: if a recruiter with this email already exists, link instead of colliding
                existing_rec = self.db.query(Recruiter).filter(Recruiter.email == fallback_email).first()
                if existing_rec:
                    person.recruiter_id = existing_rec.recruiter_id
                    stats['duplicate'] += 1
                    continue

                # Calculate comprehensive title intelligence
                t_intel = classify_title(person.current_title or "Recruiter")

                metadata_dict = {
                    "education": person.education,
                    "skills": json.loads(person.skills) if person.skills else None,
                    "experience_history": json.loads(person.experience_history) if person.experience_history else None,
                    "about_summary": person.about_summary,
                    "connections_count": person.connections_count,
                    "followers_count": person.followers_count,
                    "seniority_level": t_intel["legacy_seniority"],
                    "granular_seniority": t_intel["seniority_level"],
                    "seniority_score": t_intel["seniority_score"],
                    "domain_specialization": t_intel["domain_specialization"],
                    "specialization_label": t_intel["specialization_label"],
                    "role_family": t_intel["role_family"],
                    "is_people_manager": t_intel["is_people_manager"],
                    "canonical_title": t_intel["canonical_title"],
                }
                if getattr(person, "metadata_json", None):
                    try:
                        p_meta = json.loads(person.metadata_json) if isinstance(person.metadata_json, str) else dict(person.metadata_json)
                        for k, v in p_meta.items():
                            if v is not None and (k not in metadata_dict or metadata_dict[k] is None):
                                metadata_dict[k] = v
                    except Exception:
                        pass
                
                clean_loc = clean_location_text(person.location) or person.location

                ei = metadata_dict.get("email_intel") or {}
                ei_status = ei.get("status", "unknown") if ei else "unknown"
                ei_conf = int(ei.get("confidence", 0) * 100) if ei else 0
                ei_pattern = ei.get("pattern", "direct") if ei else "direct"
                ei_has_mx = ei.get("has_mx", False) if ei else False
                is_email_gen = bool(ei_status in ["PATTERN_VERIFIED", "MX_VERIFIED"])

                if is_email_gen and ei_has_mx and review_reason_val == "Discovered via Scout (awaiting email enrichment)":
                    needs_review_val = False
                    review_reason_val = None

                new_recruiter = Recruiter(
                    user_id=person.owner_user_id,
                    recruiter_name=person.canonical_name,
                    normalized_recruiter_name=normalize_text(person.canonical_name),
                    title=t_intel["canonical_title"],
                    specialization=t_intel["specialization_label"],
                    taxonomy_category=t_intel["domain_specialization"],
                    company_id=company_id,
                    email=fallback_email,
                    email_status=ei_status if is_email_gen else ("verified" if fallback_email and not fallback_email.endswith('@noemail.talentops') else "unknown"),
                    email_confidence=ei_conf if is_email_gen else (int(person.identity_confidence * 100) if fallback_email and not fallback_email.endswith('@noemail.talentops') else 0),
                    email_source=f"email_intel_{ei_pattern}" if is_email_gen else ("extension" if fallback_email and not fallback_email.endswith('@noemail.talentops') else None),
                    email_generated=is_email_gen,
                    email_verified_at=datetime.now(timezone.utc) if (ei_has_mx or (fallback_email and not fallback_email.endswith('@noemail.talentops'))) else None,
                    phone=person.primary_phone,
                    linkedin=person.linkedin_url,
                    location=clean_loc,
                    state=inferred_st,
                    normalized_city=clean_city,
                    data_source="extension",
                    is_active=True,
                    needs_review=needs_review_val,
                    review_reason=review_reason_val,
                    trust_score=int(person.identity_confidence * 100),
                    metadata_json=json.dumps({k: v for k, v in metadata_dict.items() if v is not None})
                )
                self.db.add(new_recruiter)
                self.db.flush()

                person.recruiter_id = new_recruiter.recruiter_id

                # Structured sub-tables for mainline relational completeness
                if fallback_email and not fallback_email.endswith('@noemail.talentops'):
                    existing_re = self.db.query(RecruiterEmail).filter(RecruiterEmail.email == fallback_email).first()
                    if not existing_re:
                        self.db.add(RecruiterEmail(
                            recruiter_id=new_recruiter.recruiter_id,
                            email=fallback_email,
                            email_type="work",
                            status=ei_status.lower() if is_email_gen else "verified",
                            confidence_score=ei_conf if is_email_gen else int(person.identity_confidence * 100),
                            is_primary=True,
                            is_generated=is_email_gen,
                            source=f"email_intel_{ei_pattern}" if is_email_gen else "extension",
                            verified_at=datetime.now(timezone.utc) if (ei_has_mx or not is_email_gen) else None,
                        ))
                if person.primary_phone:
                    self.db.add(RecruiterPhone(
                        recruiter_id=new_recruiter.recruiter_id,
                        phone_number=person.primary_phone,
                        is_primary=True,
                        belongs_to_person=True,
                        confidence_score=85,
                        source="extension",
                    ))
                if clean_loc:
                    self.db.add(RecruiterLocation(
                        recruiter_id=new_recruiter.recruiter_id,
                        city=clean_loc,
                        location_type="person",
                        is_fallback=False,
                        confidence_score=85,
                        source="extension",
                    ))
                try:
                    from ..routes.recruiters import _update_state_metadata
                    _update_state_metadata(new_recruiter, self.db)
                except Exception as sme:
                    logger.debug("State metadata update note: %s", sme)
                self.db.flush()

                # Create Audit Trail
                first_stg = staging_records[0] if staging_records else None
                event_disc_id = first_stg.discovery_id if first_stg else None
                if not event_disc_id or self.db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.discovery_id == event_disc_id).first():
                    event_disc_id = f"DISC-{secrets.token_hex(8).upper()}"

                event = ExtensionDiscoveryEvent(
                    discovery_id=event_disc_id,
                    capture_id=first_stg.capture_id if first_stg else None,
                    device_id=first_stg.device_id if first_stg else "scout-batch",
                    owner_user_id=person.owner_user_id,
                    recruiter_id=new_recruiter.recruiter_id,
                    recruiter_name=new_recruiter.recruiter_name,
                    company_name=clean_target_comp or person.current_company,
                    title=new_recruiter.title,
                    email=new_recruiter.email,
                    phone=new_recruiter.phone,
                    linkedin_url=new_recruiter.linkedin,
                    location=new_recruiter.location,
                    source_url=first_stg.source_url if first_stg else None,
                    source_page_title=first_stg.source_page_title if first_stg else None,
                    extraction_source="staging_batch_intelligence",
                    confidence=int(person.identity_confidence * 100),
                    db_action="NEW_DISCOVERY",
                    fields_added=json.dumps(["Name", "Title", "Company", "Email" if person.primary_email else None, "Phone" if person.primary_phone else None, "LinkedIn" if person.linkedin_url else None]),
                )
                self.db.add(event)

            elif decision == 'ENRICH':
                if not recruiter:
                    stats['review'] += 1
                    continue
                stats['enriched'] += 1
                fields_enriched = []

                if person.primary_email and (not recruiter.email or recruiter.email.endswith("@noemail.talentops")):
                    recruiter.email = person.primary_email
                    fields_enriched.append("Email")
                    if recruiter.review_reason == "Discovered via Scout (awaiting email enrichment)":
                        recruiter.review_reason = None
                        recruiter.needs_review = False

                    ei_p = None
                    if getattr(person, "metadata_json", None):
                        try:
                            p_meta = json.loads(person.metadata_json) if isinstance(person.metadata_json, str) else person.metadata_json
                            ei_p = p_meta.get("email_intel")
                        except Exception:
                            pass

                    is_gen_p = bool(ei_p and ei_p.get("status") in ["PATTERN_VERIFIED", "MX_VERIFIED"])
                    if ei_p:
                        recruiter.email_status = ei_p.get("status", "verified")
                        recruiter.email_confidence = int(ei_p.get("confidence", 0.85) * 100)
                        recruiter.email_source = f"email_intel_{ei_p.get('pattern', 'direct')}"
                        recruiter.email_generated = is_gen_p
                        if ei_p.get("has_mx"):
                            recruiter.email_verified_at = datetime.now(timezone.utc)

                    existing_re = self.db.query(RecruiterEmail).filter(RecruiterEmail.email == person.primary_email).first()
                    if not existing_re:
                        self.db.add(RecruiterEmail(
                            recruiter_id=recruiter.recruiter_id,
                            email=person.primary_email,
                            email_type="work",
                            status=ei_p.get("status", "verified").lower() if ei_p else "verified",
                            confidence_score=int(ei_p.get("confidence", 0.85) * 100) if ei_p else 90,
                            is_primary=True,
                            is_generated=is_gen_p,
                            source=f"email_intel_{ei_p.get('pattern', 'direct')}" if ei_p else "extension_enrichment",
                            verified_at=datetime.now(timezone.utc) if (ei_p and ei_p.get("has_mx")) else None,
                        ))
                if person.primary_phone and not recruiter.phone:
                    recruiter.phone = person.primary_phone
                    fields_enriched.append("Phone")
                    existing_rp = self.db.query(RecruiterPhone).filter(RecruiterPhone.recruiter_id == recruiter.recruiter_id, RecruiterPhone.phone_number == person.primary_phone).first()
                    if not existing_rp:
                        self.db.add(RecruiterPhone(
                            recruiter_id=recruiter.recruiter_id,
                            phone_number=person.primary_phone,
                            is_primary=True,
                            belongs_to_person=True,
                            confidence_score=85,
                            source="extension_enrichment",
                        ))
                if person.linkedin_url and not recruiter.linkedin:
                    recruiter.linkedin = person.linkedin_url
                    fields_enriched.append("LinkedIn")
                if person.current_title:
                    t_enrich = classify_title(person.current_title)
                    if not recruiter.title or recruiter.title in ("Recruiter", "Professional", "Recruiter / Talent Lead") or t_enrich["canonical_title"] != recruiter.title:
                        recruiter.title = t_enrich["canonical_title"]
                        recruiter.specialization = t_enrich["specialization_label"]
                        recruiter.taxonomy_category = t_enrich["domain_specialization"]
                        fields_enriched.append("Title")
                        fields_enriched.append("Specialization")

                        # Update metadata_json with enriched title intelligence
                        try:
                            r_meta = json.loads(recruiter.metadata_json) if recruiter.metadata_json else {}
                            r_meta["seniority_level"] = t_enrich["legacy_seniority"]
                            r_meta["granular_seniority"] = t_enrich["seniority_level"]
                            r_meta["seniority_score"] = t_enrich["seniority_score"]
                            r_meta["domain_specialization"] = t_enrich["domain_specialization"]
                            r_meta["specialization_label"] = t_enrich["specialization_label"]
                            r_meta["role_family"] = t_enrich["role_family"]
                            r_meta["is_people_manager"] = t_enrich["is_people_manager"]
                            recruiter.metadata_json = json.dumps(r_meta)
                        except Exception:
                            pass
                if person.location and not recruiter.location:
                    clean_enrich_loc = clean_location_text(person.location) or person.location
                    recruiter.location = clean_enrich_loc
                    fields_enriched.append("Location")
                    existing_rl = self.db.query(RecruiterLocation).filter(RecruiterLocation.recruiter_id == recruiter.recruiter_id).first()
                    if not existing_rl:
                        self.db.add(RecruiterLocation(
                            recruiter_id=recruiter.recruiter_id,
                            city=clean_enrich_loc,
                            location_type="person",
                            is_fallback=False,
                            confidence_score=85,
                            source="extension_enrichment",
                        ))
                    try:
                        from ..routes.recruiters import _update_state_metadata
                        _update_state_metadata(recruiter, self.db)
                    except Exception:
                        pass

                if not recruiter.normalized_recruiter_name and recruiter.recruiter_name:
                    recruiter.normalized_recruiter_name = normalize_text(recruiter.recruiter_name)

                # Handle company change
                clean_person_comp = clean_company(person.current_company)
                if clean_person_comp and clean_person_comp.lower().strip() not in BOGUS_COMPANY_NAMES:
                    m_comp_name = recruiter.company.company_name if recruiter.company else None
                    if not m_comp_name or normalize_text(clean_person_comp) != normalize_text(m_comp_name):
                        comp = self.db.query(Company).filter(
                            Company.company_name.ilike(clean_person_comp)
                        ).first()
                        if not comp:
                            comp = Company(
                                company_name=clean_person_comp,
                                canonical_name=clean_person_comp,
                                location=recruiter.location,
                                state=recruiter.state,
                                trust_score=75,
                                data_source="extension_enrichment",
                            )
                            self.db.add(comp)
                            self.db.flush()
                        else:
                            if not comp.state and recruiter.state:
                                comp.state = recruiter.state
                                self.db.add(comp)
                            if not comp.location and recruiter.location:
                                comp.location = recruiter.location
                                self.db.add(comp)
                        recruiter.company_id = comp.company_id
                        fields_enriched.append(f"Company: {clean_person_comp}")

                # Deep Profile Progressive Enrichment
                meta = json.loads(recruiter.metadata_json) if recruiter.metadata_json else {}
                if person.education and not meta.get("education"):
                    meta["education"] = person.education
                    fields_enriched.append("Education")
                if person.skills:
                    try:
                        incoming_skills = json.loads(person.skills) if isinstance(person.skills, str) else person.skills
                        existing_skills = meta.get("skills") or []
                        if len(incoming_skills) > len(existing_skills):
                            meta["skills"] = incoming_skills
                            fields_enriched.append(f"Skills (+{len(incoming_skills) - len(existing_skills)})")
                    except Exception:
                        pass

                if person.experience_history:
                    try:
                        incoming_exp = json.loads(person.experience_history) if isinstance(person.experience_history, str) else person.experience_history
                        existing_exp = meta.get("experience_history") or []
                        if len(incoming_exp) > len(existing_exp):
                            meta["experience_history"] = incoming_exp
                            fields_enriched.append(f"Experience (+{len(incoming_exp) - len(existing_exp)})")
                    except Exception:
                        pass

                if person.about_summary:
                    existing_about = meta.get("about_summary") or ""
                    if len(person.about_summary) > len(existing_about) + 15:
                        meta["about_summary"] = person.about_summary
                        fields_enriched.append("Expanded About")
                if person.connections_count and not meta.get("connections_count"):
                    meta["connections_count"] = person.connections_count
                if person.followers_count and not meta.get("followers_count"):
                    meta["followers_count"] = person.followers_count
                
                recruiter.metadata_json = json.dumps(meta)

                self.db.add(recruiter)
                person.recruiter_id = recruiter.recruiter_id

                first_stg = staging_records[0] if staging_records else None
                event_disc_id = first_stg.discovery_id if first_stg else None
                if not event_disc_id or self.db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.discovery_id == event_disc_id).first():
                    event_disc_id = f"DISC-{secrets.token_hex(8).upper()}"

                event = ExtensionDiscoveryEvent(
                    discovery_id=event_disc_id,
                    capture_id=first_stg.capture_id if first_stg else None,
                    device_id=first_stg.device_id if first_stg else "scout-batch",
                    owner_user_id=person.owner_user_id,
                    recruiter_id=recruiter.recruiter_id,
                    recruiter_name=recruiter.recruiter_name,
                    company_name=person.current_company or (recruiter.company.company_name if recruiter.company else None),
                    title=recruiter.title,
                    email=recruiter.email,
                    phone=recruiter.phone,
                    linkedin_url=recruiter.linkedin,
                    location=recruiter.location,
                    source_url=first_stg.source_url if first_stg else None,
                    source_page_title=first_stg.source_page_title if first_stg else None,
                    extraction_source="staging_batch_intelligence",
                    confidence=int(person.identity_confidence * 100),
                    db_action="ENRICHED",
                    fields_added=json.dumps(fields_enriched),
                )
                self.db.add(event)

            elif decision == 'DUPLICATE':
                stats['duplicate'] += 1
                person.recruiter_id = recruiter.recruiter_id

                first_stg = staging_records[0] if staging_records else None
                event_disc_id = first_stg.discovery_id if first_stg else None
                if not event_disc_id or self.db.query(ExtensionDiscoveryEvent).filter(ExtensionDiscoveryEvent.discovery_id == event_disc_id).first():
                    event_disc_id = f"DISC-{secrets.token_hex(8).upper()}"

                event = ExtensionDiscoveryEvent(
                    discovery_id=event_disc_id,
                    capture_id=first_stg.capture_id if first_stg else None,
                    device_id=first_stg.device_id if first_stg else "scout-batch",
                    owner_user_id=person.owner_user_id,
                    recruiter_id=recruiter.recruiter_id,
                    recruiter_name=recruiter.recruiter_name,
                    company_name=recruiter.company.company_name if recruiter.company else None,
                    title=recruiter.title,
                    email=recruiter.email,
                    phone=recruiter.phone,
                    linkedin_url=recruiter.linkedin,
                    location=recruiter.location,
                    source_url=first_stg.source_url if first_stg else None,
                    source_page_title=first_stg.source_page_title if first_stg else None,
                    extraction_source="staging_batch_intelligence",
                    confidence=int(person.identity_confidence * 100),
                    db_action="PREVIOUSLY_KNOWN",
                    fields_added=json.dumps([]),
                )
                self.db.add(event)

            elif decision == 'CONFLICT':
                stats['conflict'] += 1
                stats['review'] += 1

            elif decision == 'REVIEW':
                stats['review'] += 1

            elif decision == 'IGNORE':
                stats['ignored'] += 1

        return stats

    def _calculate_usefulness(self, record: DiscoveryStaging) -> int:
        score = 0
        name_valid, _, _ = validate_human_name(record.raw_name)
        if name_valid:
            score += 25
        if record.raw_title and not is_ui_action(record.raw_title):
            score += 20
        if record.raw_company:
            comp_valid, _ = validate_company_for_person(record.raw_company, person_name=record.raw_name)
            if comp_valid:
                score += 15
        if record.raw_email and not record.raw_email.endswith('@noemail.talentops'):
            score += 10
        if record.raw_phone:
            score += 10
        if record.raw_linkedin and 'linkedin.com/in/' in record.raw_linkedin:
            score += 10
        if record.raw_location:
            score += 5
        if record.source_url and 'linkedin.com/in/' in record.source_url:
            score += 10
        return min(score, 100)

    def process_knowledge_graph_document(self, graph_doc: Dict[str, Any], owner_user_id: int = 1) -> Dict[str, Any]:
        """
        Ingests and resolves an open-ended Knowledge Graph Document (Entities, Relationships, Signals, Observations).
        Automatically resolves canonical entities, creates relationships, stores signals, and preserves
        all typed observations without forcing rigid schemas.
        """
        stats = {
            "entities_created": 0,
            "relationships_created": 0,
            "signals_created": 0,
            "observations_created": 0,
            "canonical_promotions": 0,
        }

        cid = graph_doc.get("capture_id")
        purl = graph_doc.get("page_url")
        entities_input = graph_doc.get("entities", [])
        relationships_input = graph_doc.get("relationships", [])
        signals_input = graph_doc.get("signals", [])
        observations_input = graph_doc.get("observations", [])

        entity_pk_map = {}  # Map input ID (e.g. 'ent_1') to database KnowledgeEntity.id

        # 1. Ingest Entities
        for e in entities_input:
            etype = e.get("type", "EXTENSIBLE_TYPED_OBSERVATION")
            cname = e.get("canonical_name", "Unknown Entity").strip()
            ident = e.get("primary_identifier", cname)
            attrs = e.get("attributes", {})
            conf = e.get("confidence", 0.95)

            # Check if exists in DB
            existing_ent = self.db.query(KnowledgeEntity).filter(
                KnowledgeEntity.owner_user_id == owner_user_id,
                KnowledgeEntity.entity_type == etype,
                KnowledgeEntity.canonical_name == cname
            ).first()

            if not existing_ent:
                kent = KnowledgeEntity(
                    owner_user_id=owner_user_id,
                    entity_type=etype,
                    canonical_name=cname,
                    primary_identifier=ident,
                    attributes_json=json.dumps(attrs) if attrs else None,
                    confidence=conf,
                    source_capture_id=cid,
                    source_url=purl,
                )
                self.db.add(kent)
                self.db.flush()
                entity_pk_map[e.get("id")] = kent.id
                stats["entities_created"] += 1
            else:
                entity_pk_map[e.get("id")] = existing_ent.id

        # 2. Ingest Relationships
        for rel in relationships_input:
            sub_id = entity_pk_map.get(rel.get("subject"))
            obj_id = entity_pk_map.get(rel.get("object"))
            pred = rel.get("predicate", "ASSOCIATED_WITH")
            rattrs = rel.get("attributes", {})
            is_cur = rel.get("is_current", True)

            if sub_id and obj_id:
                krel = KnowledgeRelationship(
                    owner_user_id=owner_user_id,
                    subject_entity_id=sub_id,
                    predicate=pred,
                    object_entity_id=obj_id,
                    attributes_json=json.dumps(rattrs) if rattrs else None,
                    is_current=is_cur,
                    confidence=rel.get("confidence", 0.95),
                    source_capture_id=cid,
                )
                self.db.add(krel)
                stats["relationships_created"] += 1

        # 3. Ingest Signals
        for sig in signals_input:
            stype = sig.get("type", "STAFFING_SIGNAL")
            stitle = sig.get("title", "Signal")
            sdesc = sig.get("description")
            spayload = sig.get("payload", {})
            
            ksig = KnowledgeSignal(
                owner_user_id=owner_user_id,
                signal_type=stype,
                title=stitle,
                description=sdesc,
                payload_json=json.dumps(spayload) if spayload else None,
                confidence=sig.get("confidence", 0.95),
                source_capture_id=cid,
                source_url=purl,
            )
            self.db.add(ksig)
            stats["signals_created"] += 1

        # 4. Ingest Raw Semantic Observations
        for obs in observations_input:
            sobs = SemanticObservation(
                batch_id=graph_doc.get("batch_id") or ("BATCH-KG-" + secrets.token_hex(4).upper()),
                discovery_id="DISC-KG-" + secrets.token_hex(4).upper(),
                capture_id=cid,
                owner_user_id=owner_user_id,
                subject=obs.get("subject", "Entity"),
                predicate=obs.get("predicate", "HAS_ATTRIBUTE"),
                object_val=str(obs.get("object_val", "")),
                semantic_type=obs.get("semantic_type", "EXTENSIBLE_TYPED_OBSERVATION"),
                context=obs.get("context"),
                attributes_json=json.dumps(obs.get("attributes")) if obs.get("attributes") else None,
                confidence=obs.get("confidence", 0.95),
                processing_status="promoted",
                decision="ACCEPT",
                source_url=purl,
            )
            self.db.add(sobs)
            stats["observations_created"] += 1

        self.db.commit()
        return stats


def run_batch_processor(db: Session, limit: int = 100) -> dict:
    """
    Convenience runner for scheduled background tasks and manual trigger endpoints.
    """
    try:
        processor = DiscoveryProcessor(db)
        return processor.process_pending_batch(limit=limit)
    except Exception as e:
        logger.error("Batch processor execution error: %s", e, exc_info=True)
        return {'error': str(e), 'processed': 0}
