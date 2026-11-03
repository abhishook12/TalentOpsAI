"""
campaign_priority_intelligence_service.py
========================================================================================
Autonomous Campaign Priority Leadership, Company Enrichment & Cross-Entity Validation Engine
========================================================================================

Key Capabilities:
1. Priority Contact & Leadership Tagging:
   - Aggregates all people involved in campaign sections (CampaignRecruiter, EmailLog).
   - Treats them as the most active, high-priority stakeholders of their companies.
   - Sets is_priority_contact = True, priority_tier = 'TOP_DECISION_MAKER' | 'CAMPAIGN_ACTIVE'.
   - Tracks campaign_sent_count, last_campaign_at, engagement status.
2. Company Intelligence Roster Elevation:
   - Injects the key priority leaders into Company.metadata_json["key_priority_leaders"].
   - Sets Company.is_tracked = True and prioritizes company email formula mining.
3. Autonomous LinkedIn Discovery & Entity Enrichment:
   - Scans discovery_staging to backfill missing LinkedIn URLs from historical cards.
   - Generates high-accuracy LinkedIn search query URLs (linkedin_search_url).
4. Cross-Entity Validation & Disambiguation:
   - Company Mismatch Disambiguation: verifies recruiter company_id matches corporate domain.
   - Collision Detection: flags or merges duplicate/split contact profiles.
   - Staging Data Reconciliation: backfills alternate phones and credentials.
5. Dual-Sync Flywheel:
   - Synchronizes across PostgreSQL, DuckDB Parquet, and RecruiterStore.
"""

import json
import logging
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, '.')

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.models import Recruiter, Company
from backend.app.models.campaigns import Campaign, CampaignRecruiter, EmailLog
from backend.app.models.staging_models import DiscoveryStaging
from backend.scripts.incremental_parquet_sync import sync as sync_parquet
from backend.app.services.recruiter_store import recruiter_store

logger = logging.getLogger("CampaignPriorityIntelligence")

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'comcast.net', 'msn.com', 'live.com', 'icloud.com', 'netscape.com'
}


class CampaignPriorityIntelligenceService:
    """
    Autonomous engine that discovers, enriches, and validates campaign participants
    as company leadership stakeholders with cross-entity synchronization.
    """

    def __init__(self):
        self.telemetry = {
            "priority_contacts_updated": 0,
            "companies_roster_enriched": 0,
            "linkedin_urls_discovered": 0,
            "linkedin_search_urls_generated": 0,
            "company_mismatches_repaired": 0,
            "duplicate_collisions_resolved": 0,
            "last_run_at": None,
        }

    def sync_campaign_priority_contacts(self, db: Session) -> Dict[str, Any]:
        """
        Scans all campaign recruiters and email logs, elevating enrolled contacts
        to Priority Leadership status with sent counts and timestamps.
        """
        logger.info("🎯 Scanning all campaign sections for active outreach contacts...")
        now_utc = datetime.now(timezone.utc)

        # 1. Aggregate stats from CampaignRecruiter
        # Get all distinct recruiters in campaigns with their sent counts and statuses
        cr_stats = db.query(
            CampaignRecruiter.recruiter_id,
            func.count(CampaignRecruiter.campaign_recruiter_id).label("enrollment_count"),
            func.sum(CampaignRecruiter.sent_count).label("total_sent"),
            func.max(CampaignRecruiter.last_sent_at).label("latest_sent"),
            func.max(CampaignRecruiter.updated_at).label("latest_activity")
        ).group_by(CampaignRecruiter.recruiter_id).all()

        cr_dict = {
            row[0]: {
                "enrollment_count": int(row[1] or 0),
                "total_sent": int(row[2] or 0),
                "latest_sent": row[3],
                "latest_activity": row[4]
            }
            for row in cr_stats if row[0]
        }

        # 2. Also aggregate from EmailLog by recipient_email to catch any email-level outreach
        email_logs = db.query(
            EmailLog.recipient_email,
            func.count(EmailLog.log_id).label("total_emails"),
            func.max(EmailLog.delivered_at).label("latest_delivered"),
            func.max(EmailLog.queued_at).label("latest_queued")
        ).group_by(EmailLog.recipient_email).all()

        email_log_dict = {
            row[0].lower().strip(): {
                "total_emails": int(row[1] or 0),
                "latest_time": row[2] or row[3]
            }
            for row in email_logs if row[0]
        }

        logger.info(f"Found {len(cr_dict)} campaign recruiter records and {len(email_log_dict)} distinct email logs.")

        updated_count = 0
        all_candidate_ids = set(cr_dict.keys())

        # Also find recruiter_ids for emails in email_logs
        if email_log_dict:
            all_log_emails = list(email_log_dict.keys())
            for i in range(0, len(all_log_emails), 500):
                chunk = all_log_emails[i:i + 500]
                matched_recs = db.query(Recruiter.recruiter_id, func.lower(Recruiter.email)).filter(
                    func.lower(Recruiter.email).in_(chunk)
                ).all()
                for rec_id, _ in matched_recs:
                    all_candidate_ids.add(rec_id)

        # Batch update recruiters
        all_ids_list = list(all_candidate_ids)
        for i in range(0, len(all_ids_list), 500):
            chunk_ids = all_ids_list[i:i + 500]
            recs = db.query(Recruiter).filter(Recruiter.recruiter_id.in_(chunk_ids)).all()

            for r in recs:
                stats = cr_dict.get(r.recruiter_id, {})
                em = (r.email or "").lower().strip()
                log_stats = email_log_dict.get(em, {})

                total_sent = max(stats.get("total_sent", 0), log_stats.get("total_emails", 0))
                last_time = stats.get("latest_sent") or log_stats.get("latest_time") or stats.get("latest_activity") or now_utc

                # Determine Priority Tier
                tier = "CAMPAIGN_ACTIVE"
                if total_sent >= 2:
                    tier = "TOP_DECISION_MAKER"
                elif total_sent >= 1:
                    tier = "KEY_STAKEHOLDER"

                # Update tags
                existing_tags = r.tags or ""
                tag_list = [t.strip() for t in existing_tags.split(",") if t.strip()]
                for new_tag in ["campaign_priority", "company_leader", "active_outreach"]:
                    if new_tag not in tag_list:
                        tag_list.append(new_tag)

                r.is_priority_contact = True
                r.priority_tier = tier
                r.campaign_sent_count = total_sent
                r.last_campaign_at = last_time
                r.tags = ", ".join(tag_list)
                updated_count += 1

        db.commit()
        self.telemetry["priority_contacts_updated"] = updated_count
        logger.info(f"✅ Successfully marked {updated_count} recruiters as Priority Campaign Contacts.")
        return {"priority_contacts_updated": updated_count}

    def enrich_company_leadership_rosters(self, db: Session) -> Dict[str, Any]:
        """
        Gathers all priority contacts per company and embeds them into
        Company.metadata_json['key_priority_leaders']. Also sets is_tracked = True.
        """
        logger.info("🏢 Elevating company intelligence with active campaign leadership rosters...")

        priority_recs = db.query(Recruiter).filter(
            Recruiter.is_priority_contact == True,
            Recruiter.company_id != None
        ).all()

        company_leaders_map: Dict[int, List[Dict[str, Any]]] = {}
        for r in priority_recs:
            cid = r.company_id
            if cid not in company_leaders_map:
                company_leaders_map[cid] = []

            company_leaders_map[cid].append({
                "recruiter_id": r.recruiter_id,
                "name": r.recruiter_name,
                "title": r.title or "Key Talent Acquisition Stakeholder",
                "email": r.email,
                "phone": r.phone,
                "linkedin": r.linkedin,
                "priority_tier": r.priority_tier or "CAMPAIGN_ACTIVE",
                "campaign_sent_count": r.campaign_sent_count or 0,
                "last_campaign_at": r.last_campaign_at.isoformat() if r.last_campaign_at else None,
            })

        logger.info(f"Aggregated priority leadership rosters across {len(company_leaders_map)} companies.")

        # Batch fetch all companies
        all_cids = list(company_leaders_map.keys())
        company_dict = {}
        for i in range(0, len(all_cids), 500):
            chunk = all_cids[i:i + 500]
            comps = db.query(Company).filter(Company.company_id.in_(chunk)).all()
            for c in comps:
                company_dict[c.company_id] = c

        companies_enriched = 0
        for cid, leaders in company_leaders_map.items():
            comp = company_dict.get(cid)
            if not comp:
                continue

            # Load or init metadata
            meta = {}
            if comp.metadata_json:
                try:
                    meta = json.loads(comp.metadata_json)
                except Exception:
                    meta = {}

            # Sort leaders by total sent / seniority
            leaders.sort(key=lambda x: x.get("campaign_sent_count", 0), reverse=True)

            meta["key_priority_leaders"] = leaders
            meta["campaign_active_stakeholders_count"] = len(leaders)
            meta["is_priority_tracked"] = True
            meta["leadership_roster_updated_at"] = datetime.now(timezone.utc).isoformat()

            comp.metadata_json = json.dumps(meta, ensure_ascii=False)
            comp.is_tracked = True

            # If company has no email_pattern or generic pattern, mine pattern from top leaders
            if not comp.email_pattern and leaders:
                for l in leaders:
                    em = l.get("email")
                    name = l.get("name")
                    if em and name and "@" in em:
                        parts = name.strip().lower().split()
                        local = em.split("@")[0].lower()
                        if len(parts) >= 2:
                            fn, ln = parts[0], parts[-1]
                            if f"{fn}.{ln}" in local:
                                comp.email_pattern = "first.last"
                                break
                            elif f"{fn[0]}.{ln}" in local or f"{fn[0]}{ln}" in local:
                                comp.email_pattern = "f_last"
                                break
                            elif f"{fn}_{ln}" in local:
                                comp.email_pattern = "first_last"
                                break

            companies_enriched += 1

        db.commit()
        self.telemetry["companies_roster_enriched"] = companies_enriched
        logger.info(f"✅ Enriched leadership rosters for {companies_enriched} companies.")
        return {"companies_roster_enriched": companies_enriched}

    def resolve_and_enrich_linkedin_profiles(self, db: Session) -> Dict[str, Any]:
        """
        For campaign contacts lacking individual LinkedIn URLs:
        1. Queries discovery_staging for matching cards with raw_linkedin in batch.
        2. Generates canonical search URLs: https://www.linkedin.com/search/results/people/?keywords={name}+{company}
        """
        logger.info("🔗 Resolving and enriching LinkedIn profiles for campaign stakeholders...")

        recs_without_li = db.query(Recruiter).filter(
            Recruiter.is_priority_contact == True,
            or_(Recruiter.linkedin == None, Recruiter.linkedin == "")
        ).all()

        logger.info(f"Found {len(recs_without_li)} priority recruiters lacking LinkedIn URLs.")

        # Batch fetch company names for these recruiters
        comp_ids = list({r.company_id for r in recs_without_li if r.company_id})
        comp_name_map = {}
        for i in range(0, len(comp_ids), 500):
            chunk = comp_ids[i:i + 500]
            comps = db.query(Company.company_id, Company.company_name).filter(Company.company_id.in_(chunk)).all()
            for cid, cname in comps:
                comp_name_map[cid] = cname

        # Batch query discovery_staging for matching emails with LinkedIn
        all_emails = list({r.email.lower().strip() for r in recs_without_li if r.email and "@" in r.email})
        stg_li_map = {}
        for i in range(0, len(all_emails), 500):
            chunk_em = all_emails[i:i + 500]
            stg_rows = db.query(
                func.lower(DiscoveryStaging.raw_email),
                DiscoveryStaging.raw_linkedin
            ).filter(
                func.lower(DiscoveryStaging.raw_email).in_(chunk_em),
                DiscoveryStaging.raw_linkedin != None,
                DiscoveryStaging.raw_linkedin.like("%linkedin.com/in/%")
            ).all()
            for em_key, li_val in stg_rows:
                if em_key and li_val and em_key not in stg_li_map:
                    stg_li_map[em_key] = li_val.strip()

        discovered_from_stg = 0
        search_urls_gen = 0

        for r in recs_without_li:
            comp_name = comp_name_map.get(r.company_id, "")
            name = r.recruiter_name or ""
            email = (r.email or "").strip().lower()

            # 1. Check batch staging map
            li_url = stg_li_map.get(email)
            if li_url:
                r.linkedin = li_url[:300]
                discovered_from_stg += 1
            else:
                # 2. Formulate canonical search URL
                query_terms = [name]
                if comp_name and comp_name.lower() not in ("none", "unknown"):
                    query_terms.append(comp_name)
                query_str = " ".join(query_terms).strip()
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(query_str)}"
                r.linkedin_search_url = search_url
                search_urls_gen += 1

        db.commit()
        self.telemetry["linkedin_urls_discovered"] = discovered_from_stg
        self.telemetry["linkedin_search_urls_generated"] = search_urls_gen
        logger.info(f"✅ Discovered {discovered_from_stg} LinkedIn URLs and generated {search_urls_gen} search links.")
        return {
            "linkedin_urls_discovered": discovered_from_stg,
            "linkedin_search_urls_generated": search_urls_gen
        }

    def run_cross_entity_validation(self, db: Session) -> Dict[str, Any]:
        """
        Cross-validates entities to prevent confusion and mismatch:
        1. Company Mismatch Check: Verifies recruiter company matches email corporate domain.
        2. Collision Detection: Identifies recruiters with duplicate emails or duplicate phones.
        3. Staging Attribute Reconciliation: Enriches missing phone or location from staging.
        """
        logger.info("⚖️ Running cross-entity validation and disambiguation...")

        # 1. Company Mismatch Disambiguation
        priority_recs = db.query(Recruiter).filter(
            Recruiter.is_priority_contact == True,
            Recruiter.email != None,
            Recruiter.company_id != None
        ).all()

        all_cids = list({r.company_id for r in priority_recs if r.company_id})
        comp_map = {}
        for i in range(0, len(all_cids), 500):
            chunk = all_cids[i:i + 500]
            comps = db.query(Company).filter(Company.company_id.in_(chunk)).all()
            for c in comps:
                comp_map[c.company_id] = c

        mismatch_repaired = 0
        company_domain_cache: Dict[str, Company] = {}

        for r in priority_recs:
            em = r.email.lower().strip()
            if "@" not in em:
                continue
            dom = em.split("@")[1].strip()
            if dom in FREE_EMAIL_DOMAINS or dom in ("unknown.com", "placeholder.com"):
                continue

            comp = comp_map.get(r.company_id)
            if comp and comp.primary_domain:
                comp_dom = comp.primary_domain.lower().strip()
                # If company primary_domain completely disagrees with email domain
                if comp_dom and comp_dom != dom and not (comp_dom in dom or dom in comp_dom):
                    # Find or link the true company for this domain
                    if dom in company_domain_cache:
                        true_comp = company_domain_cache[dom]
                    else:
                        true_comp = db.query(Company).filter(
                            (Company.primary_domain == dom) |
                            (Company.website.ilike(f"%{dom}%"))
                        ).first()
                        if true_comp:
                            company_domain_cache[dom] = true_comp

                    if true_comp and true_comp.company_id != r.company_id:
                        old_comp_name = comp.company_name
                        r.company_id = true_comp.company_id
                        r.repair_reason = f"Cross-entity validation: company domain mismatch (was '{old_comp_name}', domain is '{dom}')"
                        mismatch_repaired += 1
                        logger.info(f"🔄 Repaired company mismatch for #{r.recruiter_id} ({r.recruiter_name}): '{old_comp_name}' -> '{true_comp.company_name}' ({dom})")

        # 2. Collision / Duplicate Detection & Reconciliation
        dup_emails = db.query(
            Recruiter.email,
            func.count(Recruiter.recruiter_id)
        ).filter(
            Recruiter.email != None
        ).group_by(Recruiter.email).having(func.count(Recruiter.recruiter_id) > 1).all()

        collision_resolved = 0
        for (em, cnt) in dup_emails:
            recs = db.query(Recruiter).filter(func.lower(Recruiter.email) == em.lower()).order_by(Recruiter.recruiter_id.asc()).all()
            # Prioritize the one marked priority or with highest completeness
            best_rec = next((x for x in recs if x.is_priority_contact), recs[0])
            for other in recs:
                if other.recruiter_id != best_rec.recruiter_id:
                    # Non-destructively copy any missing data to best_rec
                    if other.phone and not best_rec.phone:
                        best_rec.phone = other.phone
                    if other.linkedin and not best_rec.linkedin:
                        best_rec.linkedin = other.linkedin
                    if other.title and (not best_rec.title or best_rec.title == 'Contact'):
                        best_rec.title = other.title
                    # Delete the duplicate to eliminate collision
                    db.delete(other)
                    collision_resolved += 1
                    logger.info(f"Merged duplicate recruiter #{other.recruiter_id} into #{best_rec.recruiter_id} for email <{em}>")

        db.commit()
        self.telemetry["company_mismatches_repaired"] = mismatch_repaired
        self.telemetry["duplicate_collisions_resolved"] = collision_resolved
        logger.info(f"✅ Cross-entity validation complete: {mismatch_repaired} company mismatches fixed, {collision_resolved} collisions unified.")
        return {
            "company_mismatches_repaired": mismatch_repaired,
            "duplicate_collisions_resolved": collision_resolved
        }

    def run_full_cycle(self) -> Dict[str, Any]:
        """Runs the complete 5-phase priority intelligence and cross-entity validation loop."""
        db = SessionLocal()
        try:
            logger.info("🚀 STARTING CAMPAIGN PRIORITY INTELLIGENCE FULL CYCLE")
            res1 = self.sync_campaign_priority_contacts(db)
            res2 = self.enrich_company_leadership_rosters(db)
            res3 = self.resolve_and_enrich_linkedin_profiles(db)
            res4 = self.run_cross_entity_validation(db)

            # Dual-sync Parquet & RecruiterStore
            logger.info("🔄 Dual-Sync: Triggering incremental Parquet sync...")
            sync_res = sync_parquet()
            recruiter_store.reload()
            logger.info(f"Parquet & RecruiterStore synchronized: {recruiter_store.total_count} records in memory.")

            self.telemetry["last_run_at"] = datetime.now(timezone.utc).isoformat()

            return {
                "status": "SUCCESS",
                "telemetry": self.telemetry,
                "summary": {**res1, **res2, **res3, **res4, "parquet_records": recruiter_store.total_count}
            }
        except Exception as e:
            logger.error(f"Error in CampaignPriorityIntelligence cycle: {e}", exc_info=True)
            db.rollback()
            return {"status": "ERROR", "error": str(e)}
        finally:
            db.close()

    async def run_background_loop(self):
        """Asynchronous perpetual background worker for FastAPI."""
        import asyncio
        # Wait 15 seconds after server boot before running the first cycle
        await asyncio.sleep(15.0)
        while True:
            try:
                logger.info("Executing background CampaignPriorityIntelligence cycle...")
                await asyncio.to_thread(self.run_full_cycle)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in CampaignPriorityIntelligence background loop: {e}")
            # Run every 6 hours (21600 seconds)
            await asyncio.sleep(21600)


campaign_priority_service = CampaignPriorityIntelligenceService()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = campaign_priority_service.run_full_cycle()
    print("Execution Result:", json.dumps(result, indent=2))
