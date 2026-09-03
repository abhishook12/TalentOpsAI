import re
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from ..models.staging_models import DiscoveryStaging, ResolvedPerson
from ..models.models import Recruiter, Company
from ..models.knowledge_models import KnowledgeEntity, KnowledgeRelationship, KnowledgeSignal, SemanticObservation
from ..models.extension_models import ExtensionDiscoveryEvent
from ..utils.normalizer import (
    normalize_text,
    extract_domain,
    is_ui_action,
    is_platform_name,
    is_job_posting_title,
    validate_human_name,
    classify_page_type,
    clean_title,
    clean_company,
    split_title_and_company,
    calculate_field_confidences,
    evaluate_evidence_grounding,
    build_semantic_graph_document,
    SEMANTIC_TYPE_REGISTRY,
    UI_ACTION_TERMS,
    PLATFORM_NAMES,
)

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
                DiscoveryStaging.processing_status == 'pending'
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

            # 2. Cluster observations into person identities
            clusters = self._cluster_observations(grounded_records)
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

            # 5. Mark all staging records with processed timestamp
            for record in grounded_records:
                record.processed_at = datetime.now(timezone.utc)
                self.db.add(record)

            self.db.commit()

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
            r_li = self._normalize_linkedin(r.raw_linkedin)
            r_email = self._normalize_email(r.raw_email)
            r_phone = normalize_text(r.raw_phone) if r.raw_phone else ""
            r_name = self._normalize_name(r.raw_name)
            r_company = normalize_text(r.raw_company) if r.raw_company else ""

            for cluster in clusters:
                c_li_set = {self._normalize_linkedin(c.raw_linkedin) for c in cluster if c.raw_linkedin}
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
        canonical_name = self._normalize_name(most_common([r.raw_name for r in cluster])) or "Unknown Professional"
        primary_email = most_common([self._normalize_email(r.raw_email) for r in cluster])
        primary_phone = most_common([r.raw_phone for r in cluster])
        linkedin_url = most_common([r.raw_linkedin for r in cluster])
        location = most_common([r.raw_location for r in cluster])

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

        current_title = clean_titles[-1] if clean_titles else "Professional"
        previous_title = None
        if clean_titles and len(set(clean_titles)) > 1:
            for tit in reversed(clean_titles[:-1]):
                if tit.lower() != current_title.lower():
                    previous_title = tit
                    break

        # Calculate Identity Confidence Score
        conf = 0.0
        if canonical_name and canonical_name != "Unknown Professional":
            conf += 0.25
        if linkedin_url:
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
        conf = min(conf, 1.0)

        # Field-level confidences (0-100)
        obs_count = len(cluster)
        name_conf = int((sum(1 for r in cluster if r.raw_name) / obs_count) * 100)
        title_conf = int((sum(1 for r in cluster if r.raw_title) / obs_count) * 100)
        comp_conf = int((sum(1 for r in cluster if r.raw_company) / obs_count) * 100)
        email_conf = int((sum(1 for r in cluster if r.raw_email) / obs_count) * 100)
        phone_conf = int((sum(1 for r in cluster if r.raw_phone) / obs_count) * 100)

        owner_user_id = cluster[0].owner_user_id if cluster else 1

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

        return person

    def _match_master_db(self, person: ResolvedPerson) -> Tuple[Optional[Recruiter], float]:
        """
        Matches a ResolvedPerson against existing master `recruiters` table.
        Returns (matched_recruiter, match_confidence).
        """
        # 1. Match by LinkedIn URL (Very Strong: 0.95)
        if person.linkedin_url:
            slug = self._normalize_linkedin(person.linkedin_url)
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
                Recruiter.recruiter_name.ilike(f"%{person.canonical_name.strip()}%")
            ).all()

            for c in candidates:
                c_norm_name = normalize_text(c.recruiter_name)
                if c_norm_name == norm_name:
                    # Same phone match -> 0.80
                    if person.primary_phone and c.phone and normalize_text(c.phone) == normalize_text(person.primary_phone):
                        return c, CONFIDENCE_STRONG

                    # Same company match
                    c_comp_name = c.company.company_name if c.company else None
                    if person.current_company and c_comp_name:
                        if normalize_text(person.current_company) == normalize_text(c_comp_name):
                            # Conflict check: Different LinkedIn profiles
                            if c.linkedin and person.linkedin_url:
                                if self._normalize_linkedin(c.linkedin) != self._normalize_linkedin(person.linkedin_url):
                                    return c, 0.50  # Downgrade match confidence
                            return c, 0.75

            # Weak name-only matches
            for c in candidates:
                if normalize_text(c.recruiter_name) == norm_name:
                    return c, CONFIDENCE_WEAK

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
            if person.identity_confidence >= AUTO_COMMIT_THRESHOLD:
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'NEW',
                    'reason': f'High-confidence new candidate entity (score {person.identity_confidence:.2f})',
                }
            else:
                return {
                    'person': person,
                    'recruiter': None,
                    'decision': 'REVIEW',
                    'reason': f'Low identity confidence ({person.identity_confidence:.2f}) — human verification required',
                }

        # Case 2: Master match found
        new_fields = []
        if person.primary_email and not master_match.email:
            new_fields.append('email')
        if person.primary_phone and not master_match.phone:
            new_fields.append('phone')
        if person.linkedin_url and not master_match.linkedin:
            new_fields.append('linkedin')
        if person.current_title and not master_match.title:
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

        # Deep Profile Field Checks
        import json
        meta = json.loads(master_match.metadata_json) if master_match.metadata_json else {}
        if person.education and not meta.get("education"):
            new_fields.append('education')
        if person.skills and not meta.get("skills"):
            new_fields.append('skills')
        if person.experience_history and not meta.get("experience_history"):
            new_fields.append('experience_history')
        if person.about_summary and not meta.get("about_summary"):
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

        # Conflict checks: Contradictory corporate email domains
        if master_match.email and person.primary_email:
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
        if (len(new_fields) > 0 or has_new_company) and match_confidence >= AUTO_COMMIT_THRESHOLD:
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
        if len(new_fields) == 0 and match_confidence >= AUTO_COMMIT_THRESHOLD:
            return {
                'person': person,
                'recruiter': master_match,
                'decision': 'DUPLICATE',
                'reason': 'Record already exists with identical or subset attributes',
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
                stats['new'] += 1
                company_id = None

                # Resolve or create company
                if person.primary_email and '@' in person.primary_email:
                    email_domain = person.primary_email.split('@')[-1].lower()
                    if email_domain not in FREE_EMAIL_DOMAINS:
                        comp = self.db.query(Company).filter(
                            Company.primary_domain == email_domain
                        ).first()
                        if comp:
                            company_id = comp.company_id
                        elif person.current_company:
                            new_comp = Company(
                                company_name=person.current_company.strip(),
                                canonical_name=person.current_company.strip(),
                                primary_domain=email_domain,
                                website=f"https://{email_domain}",
                                verification_status="unverified",
                                trust_score=75,
                                data_source="extension_staged",
                            )
                            self.db.add(new_comp)
                            self.db.flush()
                            company_id = new_comp.company_id

                if not company_id and person.current_company:
                    comp = self.db.query(Company).filter(
                        Company.company_name.ilike(person.current_company.strip())
                    ).first()
                    if comp:
                        company_id = comp.company_id
                    else:
                        new_comp = Company(
                            company_name=person.current_company.strip(),
                            canonical_name=person.current_company.strip(),
                            verification_status="unverified",
                            trust_score=70,
                            data_source="extension_staged",
                        )
                        self.db.add(new_comp)
                        self.db.flush()
                        company_id = new_comp.company_id

                # Create master Recruiter
                fallback_email = person.primary_email or f"ext_{secrets.token_hex(8)}@noemail.talentops"
                
                metadata_dict = {
                    "education": person.education,
                    "skills": json.loads(person.skills) if person.skills else None,
                    "experience_history": json.loads(person.experience_history) if person.experience_history else None,
                    "about_summary": person.about_summary,
                    "connections_count": person.connections_count,
                    "followers_count": person.followers_count,
                }
                
                new_recruiter = Recruiter(
                    user_id=person.owner_user_id,
                    recruiter_name=person.canonical_name,
                    title=person.current_title or "Recruiter / Talent Partner",
                    company_id=company_id,
                    email=fallback_email,
                    phone=person.primary_phone,
                    linkedin=person.linkedin_url,
                    location=person.location,
                    data_source="extension",
                    is_active=True,
                    needs_review=bool(person.identity_confidence < 0.85 or not person.primary_email),
                    trust_score=int(person.identity_confidence * 100),
                    metadata_json=json.dumps({k: v for k, v in metadata_dict.items() if v is not None})
                )
                self.db.add(new_recruiter)
                self.db.flush()

                person.recruiter_id = new_recruiter.recruiter_id

                # Create Audit Trail
                first_stg = staging_records[0] if staging_records else None
                event = ExtensionDiscoveryEvent(
                    discovery_id=first_stg.discovery_id if first_stg else f"DISC-{secrets.token_hex(4).upper()}",
                    capture_id=first_stg.capture_id if first_stg else None,
                    device_id=first_stg.device_id if first_stg else "scout-batch",
                    owner_user_id=person.owner_user_id,
                    recruiter_id=new_recruiter.recruiter_id,
                    recruiter_name=new_recruiter.recruiter_name,
                    company_name=person.current_company,
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
                stats['enriched'] += 1
                fields_enriched = []

                if person.primary_email and (not recruiter.email or recruiter.email.endswith("@noemail.talentops")):
                    recruiter.email = person.primary_email
                    fields_enriched.append("Email")
                if person.primary_phone and not recruiter.phone:
                    recruiter.phone = person.primary_phone
                    fields_enriched.append("Phone")
                if person.linkedin_url and not recruiter.linkedin:
                    recruiter.linkedin = person.linkedin_url
                    fields_enriched.append("LinkedIn")
                if person.current_title and (not recruiter.title or recruiter.title == "Recruiter"):
                    recruiter.title = person.current_title
                    fields_enriched.append("Title")
                if person.location and not recruiter.location:
                    recruiter.location = person.location
                    fields_enriched.append("Location")

                # Handle company change
                if person.current_company:
                    m_comp_name = recruiter.company.company_name if recruiter.company else None
                    if not m_comp_name or normalize_text(person.current_company) != normalize_text(m_comp_name):
                        comp = self.db.query(Company).filter(
                            Company.company_name.ilike(person.current_company.strip())
                        ).first()
                        if not comp:
                            comp = Company(
                                company_name=person.current_company.strip(),
                                canonical_name=person.current_company.strip(),
                                trust_score=75,
                                data_source="extension_enrichment",
                            )
                            self.db.add(comp)
                            self.db.flush()
                        recruiter.company_id = comp.company_id
                        fields_enriched.append(f"Company: {person.current_company}")

                # Deep Profile Progressive Enrichment
                meta = json.loads(recruiter.metadata_json) if recruiter.metadata_json else {}
                if person.education and not meta.get("education"):
                    meta["education"] = person.education
                    fields_enriched.append("Education")
                if person.skills and not meta.get("skills"):
                    meta["skills"] = json.loads(person.skills)
                    fields_enriched.append("Skills")
                if person.experience_history and not meta.get("experience_history"):
                    meta["experience_history"] = json.loads(person.experience_history)
                    fields_enriched.append("Experience")
                if person.about_summary and not meta.get("about_summary"):
                    meta["about_summary"] = person.about_summary
                    fields_enriched.append("About")
                if person.connections_count and not meta.get("connections_count"):
                    meta["connections_count"] = person.connections_count
                if person.followers_count and not meta.get("followers_count"):
                    meta["followers_count"] = person.followers_count
                
                recruiter.metadata_json = json.dumps(meta)

                self.db.add(recruiter)
                person.recruiter_id = recruiter.recruiter_id

                first_stg = staging_records[0] if staging_records else None
                event = ExtensionDiscoveryEvent(
                    discovery_id=first_stg.discovery_id if first_stg else f"DISC-{secrets.token_hex(4).upper()}",
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
                event = ExtensionDiscoveryEvent(
                    discovery_id=first_stg.discovery_id if first_stg else f"DISC-{secrets.token_hex(4).upper()}",
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
        if record.raw_name:
            score += 25
        if record.raw_title:
            score += 20
        if record.raw_company:
            score += 15
        if record.raw_email and not record.raw_email.endswith('@noemail.talentops'):
            score += 10
        if record.raw_phone:
            score += 10
        if record.raw_linkedin:
            score += 10
        if record.raw_location:
            score += 5
        if record.source_url and 'linkedin.com' in record.source_url:
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
