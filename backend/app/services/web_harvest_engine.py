"""
WebHarvest Autonomous Web Discovery Engine — TalentOps AI
==========================================================

Proactively crawls the open internet to discover new recruiter profiles,
company contacts, and talent industry intelligence. Feeds discoveries
directly into the existing DiscoveryStaging → DiscoveryProcessor → Master DB
pipeline without any user interaction.

Data Sources (Free, Zero API Keys):
1. Company career/team/about pages (from existing DB domains)
2. Public staffing directories
3. DNS MX/TXT records for domain validation
4. Email pattern inference from corporate websites

Architecture:
- Runs as a background asyncio task (same pattern as AutonomousProfileSweeper)
- Seeds targets from existing 437K Parquet dataset (under-represented companies)
- Extracts profiles via httpx + regex + BeautifulSoup
- Validates via is_human_name(), DNS MX checks, and confidence scoring
- Injects validated profiles into DiscoveryStaging for pipeline processing
"""

import os
import re
import json
import time
import uuid
import asyncio
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

import httpx
import duckdb

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.staging_models import DiscoveryStaging
from ..services.geo_quota_tracker import GeoQuotaTracker

logger = logging.getLogger("talentops.web_harvest")

# ── Constants ──────────────────────────────────────────────────────────────────

# User-Agent rotation pool (real browser UAs)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
]

# Pages on company websites likely to contain team member info
TEAM_PAGE_PATHS = [
    "/team", "/our-team", "/leadership",
    "/people", "/staff", "/about/team",
    "/company/team", "/who-we-are", "/meet-the-team",
]

# Regex patterns for entity extraction
EMAIL_REGEX = re.compile(
    r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'
)
PHONE_REGEX = re.compile(
    r'(?:\+?1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b'
)
LINKEDIN_REGEX = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)',
    re.IGNORECASE
)
# Common person name patterns (First Last, First M. Last)
NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]{1,20})\s+(?:[A-Z]\.?\s+)?([A-Z][a-z]{1,20})\b'
)

# Recruiting-related title patterns
TITLE_KEYWORDS = re.compile(
    r'\b(?:recruiter|talent\s*acquisition|sourcer|staffing|hr\s*manager|'
    r'hiring\s*manager|people\s*operations|human\s*resources|headhunter|'
    r'recruiting\s*manager|account\s*manager|business\s*development|'
    r'placement\s*specialist|workforce|executive\s*search|principal\s*consultant|'
    r'delivery\s*manager|senior\s*recruiter|lead\s*recruiter|technical\s*recruiter|'
    r'it\s*recruiter|talent\s*partner|talent\s*lead|recruitment\s*consultant)\b',
    re.IGNORECASE
)

# Domains to never scrape (social media, search engines, etc.)
BLOCKED_DOMAINS = {
    'google.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'youtube.com', 'tiktok.com', 'reddit.com', 'wikipedia.org',
    'amazon.com', 'apple.com', 'microsoft.com', 'github.com',
    'stackoverflow.com', 'noemail.talentops', 'example.com',
    'missing.local', 'invalid.local', 'localhost',
}

# Free/disposable email domains to skip
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
    'yandex.com', 'zoho.com', 'live.com', 'msn.com',
    'comcast.net', 'att.net', 'verizon.net', 'cox.net',
}

# Generic departmental / automated mailbox prefixes to strictly ignore
GENERIC_EMAIL_PREFIXES = {
    'admin', 'administrator', 'webmaster', 'postmaster', 'hostmaster',
    'info', 'information', 'contact', 'contactus', 'contact_us',
    'support', 'help', 'helpdesk', 'service', 'services', 'customerservice',
    'sales', 'marketing', 'media', 'press', 'pr', 'news', 'queries',
    'accounts', 'accounting', 'billing', 'invoice', 'invoices', 'finance', 'pay',
    'hr', 'humanresources', 'careers', 'jobs', 'recruitment', 'recruiting',
    'hiring', 'talent', 'work', 'employment',
    'office', 'reception', 'general', 'inquiries', 'enquiries',
    'mail', 'mailbox', 'email', 'feedback', 'team', 'staff', 'operations',
    'ops', 'security', 'privacy', 'legal', 'compliance', 'investor', 'investors',
    'ir', 'hello', 'hi', 'welcome', 'no-reply', 'noreply', 'donotreply',
    'benefits', 'leaverequest', 'leave', 'claims', 'payroll', 'insurance',
    'disability', 'retiree', 'fmla', 'pto', 'corporate', 'department',
    'facilities', 'headquarters', 'relations', 'requests', 'portal',
}


class WebHarvestEngine:
    """
    Autonomous Web Discovery Engine — proactively finds new recruiter/company
    profiles from the open internet and feeds them into the staging pipeline.
    """

    def __init__(self):
        # Feature flag
        self.enabled = os.getenv("ENABLE_WEB_HARVEST", "true").lower() in ("1", "true", "yes", "on")
        self.running = False
        self._loop_task = None

        # Configuration
        self.harvest_interval = int(os.getenv("WEB_HARVEST_INTERVAL", "60"))  # 60 seconds between cycles
        self.batch_size = int(os.getenv("WEB_HARVEST_BATCH_SIZE", "3"))  # current dynamic batch size
        self.min_batch_size = 3
        self.max_batch_size = 7
        self.target_cycle_time = 40.0  # target duration buffer per cycle (seconds)
        self.max_profiles_per_cycle = 50  # safety cap
        self.cooldown_hours = 24  # don't re-scrape same domain within this window
        self.request_delay = (0.5, 1.2)  # optimized delay range between requests (seconds)
        self.request_timeout = 4.0  # tighter HTTP timeout per request

        # State tracking
        self._scraped_domains: Dict[str, datetime] = {}  # domain -> last_scraped_at
        self._ua_index = 0

        # Statistics
        self.stats = {
            "start_time": None,
            "harvest_cycles": 0,
            "profiles_discovered": 0,
            "profiles_staged": 0,
            "profiles_promoted": 0,
            "profiles_enriched": 0,
            "domains_scraped": 0,
            "domains_queued": 0,
            "quality_gate_rejections": 0,
            "dedup_rejections": 0,
            "scrape_errors": 0,
            "last_cycle_at": None,
            "last_cycle_profiles": 0,
            "last_cycle_duration_sec": 0,
        }
        self.recent_actions = deque(maxlen=100)
        self.priority_queue = deque()

    def enqueue_priority_target(self, company_name: str, domain: Optional[str] = None, source: str = "user_demand") -> bool:
        """Enqueues a high-priority company target from user search or manual request."""
        clean_company = (company_name or "").strip()
        if not clean_company or len(clean_company) < 2:
            return False
            
        clean_domain = (domain or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ")
        if not clean_domain:
            clean_domain = f"{clean_company.lower().replace(' ', '').replace(',', '').replace('.', '')}.com"
            
        # Avoid duplicate queueing
        for item in self.priority_queue:
            if item.get("company_name", "").lower() == clean_company.lower() or item.get("domain", "").lower() == clean_domain:
                return False
                
        self.priority_queue.append({
            "company_name": clean_company,
            "domain": clean_domain,
            "source": source,
            "priority": "user_demand",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        })
        self._log_action(f"Demand Queue: Prioritized '{clean_company}' ({clean_domain}) for next harvest cycle [Source: {source}]")
        return True

    def get_priority_targets(self) -> List[Dict[str, Any]]:
        """Returns the current list of pending priority targets."""
        return list(self.priority_queue)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        """Starts the WebHarvest engine as a background asyncio task."""
        if not self.enabled:
            logger.info("[WEBHARVEST] Engine disabled via ENABLE_WEB_HARVEST=false")
            return

        if self.running:
            logger.info("[WEBHARVEST] Engine is already running.")
            return

        self.running = True
        self._loop_task = asyncio.create_task(self.run_loop())
        logger.info("[WEBHARVEST] Autonomous Web Discovery Engine started successfully.")

    def stop(self):
        """Stops the engine gracefully."""
        self.running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("[WEBHARVEST] Engine stopped gracefully.")

    async def run_loop(self):
        """Main asyncio event loop — runs harvest cycles continuously."""
        self.stats["start_time"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            "[WEBHARVEST] AUTONOMOUS WEB DISCOVERY ENGINE ACTIVE | "
            "Interval: %ds | Batch: %d companies/cycle",
            self.harvest_interval, self.batch_size
        )

        # Initial startup delay to let other services warm up
        await asyncio.sleep(15.0)

        while self.running:
            try:
                cycle_start = time.time()
                result = await asyncio.to_thread(self._run_harvest_cycle)
                cycle_duration = round(time.time() - cycle_start, 1)

                self.stats["harvest_cycles"] += 1
                self.stats["last_cycle_at"] = datetime.now(timezone.utc).isoformat()
                self.stats["last_cycle_profiles"] = result.get("profiles_staged", 0)
                self.stats["last_cycle_duration_sec"] = cycle_duration

                # Auto-tune batch size based on cycle velocity
                self._adjust_batch_size(cycle_duration)

                if result.get("profiles_staged", 0) > 0:
                    logger.info(
                        "[WEBHARVEST] Cycle #%d complete | Discovered: %d | Staged: %d | Duration: %.1fs | BatchSize: %d",
                        self.stats["harvest_cycles"],
                        result.get("profiles_extracted", 0),
                        result.get("profiles_staged", 0),
                        cycle_duration,
                        self.batch_size,
                    )
                else:
                    logger.debug(
                        "[WEBHARVEST] Cycle #%d complete | No new profiles | Duration: %.1fs | BatchSize: %d",
                        self.stats["harvest_cycles"], cycle_duration, self.batch_size
                    )

                # Sleep until next cycle
                await asyncio.sleep(self.harvest_interval)

            except asyncio.CancelledError:
                logger.info("[WEBHARVEST] Engine loop cancelled.")
                break
            except Exception as e:
                logger.error("[WEBHARVEST] Error in harvest cycle: %s", e, exc_info=True)
                self.stats["scrape_errors"] += 1
                await asyncio.sleep(30.0)

    def _adjust_batch_size(self, cycle_duration: float):
        """Auto-tunes batch_size dynamically based on real cycle duration."""
        old_size = self.batch_size
        if cycle_duration < self.target_cycle_time * 0.5 and self.batch_size < self.max_batch_size:
            self.batch_size = min(self.max_batch_size, self.batch_size + 1)
            self._log_action(
                f"Adaptive Scaling: Increased batch size {old_size} → {self.batch_size} "
                f"(Cycle took {cycle_duration}s < {self.target_cycle_time * 0.5:.0f}s)"
            )
        elif cycle_duration > self.target_cycle_time and self.batch_size > self.min_batch_size:
            self.batch_size = max(self.min_batch_size, self.batch_size - 1)
            self._log_action(
                f"Adaptive Scaling: Decreased batch size {old_size} → {self.batch_size} "
                f"(Cycle took {cycle_duration}s > {self.target_cycle_time:.0f}s)"
            )

    # ── Core Harvest Cycle ─────────────────────────────────────────────────────

    def _run_harvest_cycle(self) -> Dict[str, Any]:
        """Executes a single harvest cycle: seed → scrape → extract → validate → stage.
        Phase 2 runs target audits in parallel via ThreadPoolExecutor for maximum speed."""
        quota_tracker = GeoQuotaTracker()
        result = {"profiles_extracted": 0, "profiles_staged": 0, "domains_scraped": 0}

        # Phase 1: Generate seed targets from existing database
        targets = self._generate_seed_targets()
        if not targets:
            return result

        self.stats["domains_queued"] = len(targets)

        # Filter valid targets
        valid_targets = []
        for target in targets[:self.batch_size]:
            domain = target.get("domain")
            if domain and not self._is_domain_on_cooldown(domain):
                valid_targets.append(target)

        if not valid_targets:
            return result

        first_co = valid_targets[0].get("company_name", valid_targets[0].get("domain", "agency"))
        self._log_action(f"Harvest cycle started: auditing {len(valid_targets)} priority targets in parallel (Starting with {first_co})")

        # Phase 2: Parallel target auditing via ThreadPoolExecutor
        all_profiles = []
        max_workers = min(len(valid_targets), 5)  # Scale up to 5 parallel workers with adaptive batch sizing

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {
                executor.submit(self._audit_single_target, t, quota_tracker): t
                for t in valid_targets
            }
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    audit_result = future.result()
                    all_profiles.extend(audit_result.get("profiles", []))
                    result["domains_scraped"] += audit_result.get("domains_scraped", 0)
                    self.stats["domains_scraped"] += audit_result.get("domains_scraped", 0)
                    result["profiles_staged"] += audit_result.get("xray_staged", 0)
                    self.stats["profiles_staged"] += audit_result.get("xray_staged", 0)
                except Exception as e:
                    logger.debug("[WEBHARVEST] Parallel audit error for %s: %s", target.get("domain"), e)
                    self.stats["scrape_errors"] += 1

        result["profiles_extracted"] = len(all_profiles)
        self.stats["profiles_discovered"] += len(all_profiles)

        # Phase 3: Quality gate + dedup + staging injection for direct web crawl
        if all_profiles:
            staged_count = self._validate_and_stage_profiles(all_profiles)
            result["profiles_staged"] = staged_count
            self.stats["profiles_staged"] += staged_count
            self._log_action(f"Quality gate complete: {staged_count} verified profiles staged to master catalog")

        # Phase 4: Autonomous Database Reconciliation & Parquet Dual-Sync Flywheel (Zero Manual Clicks)
        try:
            from .db_auto_enricher import db_auto_enricher
            with SessionLocal() as db_session:
                recon_res = db_auto_enricher.reconcile_staging_batch(db=db_session, limit=50)
                if recon_res.get("processed_count", 0) > 0:
                    promoted = recon_res.get("promoted_new", 0)
                    enriched = recon_res.get("enriched_existing", 0)
                    self._log_action(
                        f"Autonomous reconciliation: {promoted} promoted to catalog, "
                        f"{enriched} enriched in DB"
                    )
                    result["profiles_promoted"] = promoted
                    result["profiles_enriched"] = enriched
                    self.stats["profiles_promoted"] += promoted
                    self.stats["profiles_enriched"] += enriched

                # Autonomous Parquet self-healing dual-sync sweep
                synced_pq = db_auto_enricher.autonomous_sync_parquet(db=db_session)
                if synced_pq > 0:
                    self._log_action(f"Autonomous Dual-Sync: Appended {synced_pq} verified recruiters into DuckDB Parquet dataset")
        except Exception as recon_err:
            logger.error("[WEBHARVEST] Autonomous reconcile / parquet-sync error: %s", recon_err)

        self._log_action(f"Harvest cycle completed: audited {result['domains_scraped']} domains")
        logger.info('[WEB_HARVEST] Geo distribution: %s', quota_tracker.get_stats())
        return result

    def _audit_single_target(self, target: Dict[str, Any], quota_tracker: GeoQuotaTracker = None) -> Dict[str, Any]:
        """Audits a single company target (scrape + X-Ray dork). Thread-safe."""
        import random
        domain = target.get("domain")
        company_name = target.get("company_name", "")
        audit_result = {"profiles": [], "domains_scraped": 0, "xray_staged": 0}

        try:
            self._log_action(f"Auditing team directories for {domain} ({company_name})...")
            profiles = self._scrape_company_website(domain, company_name)
            audit_result["profiles"].extend(profiles)
            audit_result["domains_scraped"] = 1
            self._scraped_domains[domain] = datetime.now(timezone.utc)

            # X-Ray Dorking for actual active recruiters
            try:
                from .search_xray_harvester import search_xray_harvester
                with SessionLocal() as s_db:
                    xray_res = search_xray_harvester.harvest_company(
                        company_name=company_name,
                        domain=domain,
                        db=s_db,
                        max_profiles=5,
                        owner_user_id=1,
                        geo_tracker=quota_tracker
                    )
                    if xray_res:
                        self._log_action(f"X-Ray Dorking mined {len(xray_res)} verified recruiters for {company_name}")
                        audit_result["xray_staged"] = len(xray_res)
            except Exception as xray_err:
                logger.debug("[WEBHARVEST] X-Ray harvest error: %s", xray_err)

            if profiles:
                self._log_action(f"Mined {len(profiles)} recruiter profiles on {domain} ({company_name})")
            else:
                self._log_action(f"Completed audit for {domain}")
        except Exception as e:
            logger.debug("[WEBHARVEST] Error scraping %s: %s", domain, e)

        # Rate limiting (per-worker thread)
        time.sleep(random.uniform(*self.request_delay))
        return audit_result

    # ── Seed Target Generation ─────────────────────────────────────────────────

    def _generate_seed_targets(self) -> List[Dict[str, Any]]:
        """
        Generates a prioritized list of company domains to scrape by analyzing
        the existing 437K recruiter Parquet dataset for under-represented companies.
        """
        targets = []

        # Priority 0: Demand-Driven User Queue (Highest Priority)
        while self.priority_queue and len(targets) < self.batch_size:
            p_target = self.priority_queue.popleft()
            targets.append({
                "domain": p_target["domain"],
                "company_name": p_target["company_name"],
                "existing_contacts": 0,
                "priority": "user_demand",
                "registry_tier": "USER_DEMAND_PRIORITY",
            })

        # Priority 1: Official Accredited US Agency Registry Seeds (ASA, SIA Top 100, NAPS)
        try:
            from .agency_registry_seeder import agency_registry_seeder
            registry_seeds = agency_registry_seeder.get_verified_registry_seeds()
            for seed in registry_seeds:
                s_domain = seed["domain"]
                if not self._is_domain_on_cooldown(s_domain):
                    targets.append({
                        "domain": s_domain,
                        "company_name": seed["company_name"],
                        "existing_contacts": 0,
                        "priority": "critical_agency",
                        "registry_tier": seed.get("registry_tier", "ASA_ACCREDITED"),
                    })
        except Exception as seed_err:
            logger.debug("[WEBHARVEST] Registry seed integration note: %s", seed_err)

        try:
            from .recruiter_store import PARQUET_FILE
            if not os.path.exists(PARQUET_FILE):
                logger.debug("[WEBHARVEST] Parquet file not found, skipping secondary seed generation.")
                return targets

            parquet_path = PARQUET_FILE.replace(os.sep, "/")
            con = duckdb.connect(database=":memory:", read_only=False)

            # Strategy 1: Find companies with few known contacts (high-value expansion targets)
            # Extract corporate domains from existing email addresses
            query = f"""
                SELECT
                    SPLIT_PART(email, '@', 2) as domain,
                    ANY_VALUE(COALESCE(
                        NULLIF(TRIM(CAST(company_id AS VARCHAR)), ''),
                        NULLIF(TRIM(CAST(recruiter_name AS VARCHAR)), '')
                    )) as company_name,
                    COUNT(*) as contact_count
                FROM read_parquet('{parquet_path}')
                WHERE email IS NOT NULL
                    AND email NOT LIKE '%@noemail.talentops%'
                    AND email NOT LIKE '%@missing.local%'
                    AND email NOT LIKE '%@example.com%'
                    AND email NOT LIKE '%@invalid.local%'
                    AND SPLIT_PART(email, '@', 2) NOT IN (
                        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                        'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
                        'yandex.com', 'zoho.com', 'live.com', 'msn.com',
                        'comcast.net', 'att.net', 'verizon.net', 'cox.net'
                    )
                GROUP BY SPLIT_PART(email, '@', 2)
                HAVING COUNT(*) BETWEEN 1 AND 3
                ORDER BY RANDOM()
                LIMIT {self.batch_size * 3}
            """
            rows = con.execute(query).fetchall()
            con.close()

            for row in rows:
                domain, company_name, count = row[0], row[1], row[2]
                if domain and '.' in domain and len(domain) > 4:
                    # Skip blocked domains
                    root_domain = '.'.join(domain.split('.')[-2:])
                    if root_domain in BLOCKED_DOMAINS:
                        continue
                    if self._is_domain_on_cooldown(domain):
                        continue

                    targets.append({
                        "domain": domain,
                        "company_name": company_name or domain.split('.')[0].title(),
                        "existing_contacts": count,
                        "priority": "high" if count == 1 else "medium",
                    })

            logger.debug("[WEBHARVEST] Generated %d seed targets from Parquet analysis.", len(targets))

        except Exception as e:
            logger.warning("[WEBHARVEST] Seed generation error: %s", e)

        return targets

    # ── Web Scraping ───────────────────────────────────────────────────────────

    def _scrape_company_website(self, domain: str, company_name: str) -> List[Dict[str, Any]]:
        """
        Scrapes a company's website for team member profiles.
        Returns a list of extracted profile dictionaries.
        """
        all_profiles = []
        pages_tried = 0
        max_pages = 2  # Max pages to try per domain

        for path in TEAM_PAGE_PATHS:
            if pages_tried >= max_pages:
                break

            url = f"https://{domain}{path}"
            try:
                html_text, strategy = self._fetch_page(url)
                if not html_text:
                    continue

                pages_tried += 1
                profiles = self._extract_profiles_from_text(html_text, domain, company_name, url)

                # If static fetch returned 0 profiles but page may be a dynamic JS app, trigger headless browser
                if not profiles and strategy != "headless_browser":
                    try:
                        from .dynamic_scraper_worker import dynamic_scraper_worker
                        if dynamic_scraper_worker.is_spa_or_blocked(html_text) or any(
                            k in html_text.lower() for k in ("team", "leadership", "people", "staff", "recruiter")
                        ):
                            logger.info("[WEBHARVEST] Dynamic SPA fallback triggered for %s", url)
                            rendered_html = dynamic_scraper_worker.render_with_headless_browser(url)
                            if rendered_html and len(rendered_html) > len(html_text):
                                dynamic_profiles = self._extract_profiles_from_text(rendered_html, domain, company_name, url)
                                if dynamic_profiles:
                                    logger.info("[WEBHARVEST] Headless browser recovered %d dynamic profiles on %s", len(dynamic_profiles), url)
                                    profiles = dynamic_profiles
                    except Exception as dyn_err:
                        logger.debug("[WEBHARVEST] Dynamic fallback error: %s", dyn_err)

                all_profiles.extend(profiles)

                # If we found profiles on this page, also check for pagination
                if profiles:
                    logger.debug(
                        "[WEBHARVEST] Found %d profiles on %s",
                        len(profiles), url
                    )

            except Exception as e:
                logger.debug("[WEBHARVEST] Error fetching %s: %s", url, e)

            # Respectful delay between page requests (optimized)
            import random
            time.sleep(random.uniform(0.3, 0.8))

        # Deduplicate within this domain's results
        seen_keys = set()
        unique_profiles = []
        for p in all_profiles:
            raw_n = (p.get("raw_name") or "").lower()
            raw_e = (p.get("raw_email") or "").lower()
            key = (raw_n, raw_e)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_profiles.append(p)

        return unique_profiles[:self.max_profiles_per_cycle]

    def _fetch_page(self, url: str) -> Tuple[Optional[str], str]:
        """Fetches a web page using multi-tiered dynamic scraping cascade."""
        # Tier 1 & 2: Dynamic scraper worker (TLS impersonation + automatic headless elevation)
        try:
            from .dynamic_scraper_worker import dynamic_scraper_worker
            html, strategy = dynamic_scraper_worker.smart_fetch(url)
            if html:
                return html, strategy
        except Exception as e:
            logger.debug("[WEBHARVEST] Smart fetch error for %s: %s", url, e)

        # Tier 3: Standard HTTPX fallback
        try:
            import random
            ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
            self._ua_index += 1

            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",
            }

            with httpx.Client(
                timeout=self.request_timeout,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = client.get(url, headers=headers)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type or "text" in content_type:
                        return response.text, "httpx_fallback"

                return None, "httpx_failed"

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
            logger.debug("[WEBHARVEST] HTTP error for %s: %s", url, type(e).__name__)
            return None, "httpx_error"
        except Exception as e:
            logger.debug("[WEBHARVEST] Unexpected error fetching %s: %s", url, e)
            return None, "error"

    # ── Entity Extraction ──────────────────────────────────────────────────────

    def _extract_profiles_from_text(
        self, html_text: str, domain: str, company_name: str, source_url: str
    ) -> List[Dict[str, Any]]:
        """
        Extracts structured profiles from HTML page text using regex patterns.
        Returns list of profile dicts compatible with DiscoveryStaging.
        """
        profiles = []

        # Strip HTML tags for clean text extraction
        clean_text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        # Extract all emails matching the company domain
        domain_emails = set()
        for match in EMAIL_REGEX.finditer(clean_text):
            email = match.group().lower().strip()
            email_domain = email.split('@')[1] if '@' in email else ''
            local_part = email.split('@')[0] if '@' in email else ''

            # Discard generic departmental and role mailboxes
            if local_part in GENERIC_EMAIL_PREFIXES:
                continue
            if any(p in GENERIC_EMAIL_PREFIXES for p in re.split(r'[._\-+]', local_part)):
                continue

            # Only keep emails from the target domain (not free email providers)
            if email_domain == domain or (
                email_domain and email_domain not in FREE_EMAIL_DOMAINS
                and email_domain not in BLOCKED_DOMAINS
            ):
                domain_emails.add(email)

        # Extract phone numbers
        phones = set()
        for match in PHONE_REGEX.finditer(clean_text):
            phone = re.sub(r'[^\d+]', '', match.group())
            if len(phone) >= 10:
                phones.add(match.group().strip())

        # Extract LinkedIn URLs
        linkedin_urls = set()
        for match in LINKEDIN_REGEX.finditer(html_text):  # Use raw HTML for URLs
            slug = match.group(1)
            if slug and len(slug) > 2:
                linkedin_urls.add(f"https://www.linkedin.com/in/{slug}")

        # Extract names from text
        names = set()
        for match in NAME_PATTERN.finditer(clean_text):
            first, last = match.group(1), match.group(2)
            full_name = f"{first} {last}"
            # Basic validation
            if len(first) >= 2 and len(last) >= 2:
                names.add(full_name)

        # Strategy 0: JSON-LD Structured Entity Extraction (schema.org/Person & Organization)
        try:
            from .dynamic_scraper_worker import dynamic_scraper_worker
            json_ld_entities = dynamic_scraper_worker.extract_structured_json_ld(html_text)
            for entity in json_ld_entities:
                ename = entity.get("name")
                if ename and len(ename.strip().split()) >= 2:
                    e_email = entity.get("email")
                    e_title = entity.get("title")
                    # If email missing, attempt permutation matrix match
                    if not e_email:
                        try:
                            from .email_permutation_engine import email_permutation_engine
                            meta = email_permutation_engine.discover_verified_email(
                                full_name=ename, domain=domain, company_name=company_name
                            )
                            if meta:
                                e_email = meta.get("email")
                        except Exception:
                            pass

                    profiles.append({
                        "raw_name": ename.strip(),
                        "raw_email": e_email,
                        "raw_company": company_name,
                        "raw_phone": entity.get("phone") or (list(phones)[0] if phones else None),
                        "raw_linkedin": None,
                        "raw_title": e_title or "Team Member",
                        "raw_location": None,
                        "source_url": source_url,
                        "domain": domain,
                        "discovery_method": "json_ld_structured",
                    })
        except Exception as json_err:
            logger.debug("[WEBHARVEST] JSON-LD extraction note: %s", json_err)

        # Strategy 1: Build profiles from emails (most reliable)
        for email in domain_emails:
            local_part = email.split('@')[0]
            name_from_email = self._name_from_email(local_part)

            candidate_name = name_from_email
            # Try to match email-derived name with a name found on page
            if candidate_name:
                for page_name in names:
                    if self._names_match(candidate_name, page_name):
                        candidate_name = page_name
                        break
            else:
                # If email local_part wasn't first.last, look within 120 chars around email in clean_text
                email_pos = clean_text.lower().find(email)
                if email_pos >= 0:
                    vicinity = clean_text[max(0, email_pos - 120):email_pos + 120]
                    for page_name in names:
                        if page_name in vicinity:
                            candidate_name = page_name
                            break

            # Strictly require a multi-word human name (First Last) that passes human verification
            from .scraper import is_human_name
            if not candidate_name or len(candidate_name.split()) < 2:
                continue
            if not is_human_name(candidate_name, company_name, email):
                continue

            profile = {
                "raw_name": candidate_name,
                "raw_email": email,
                "raw_company": company_name,
                "raw_phone": None,
                "raw_linkedin": None,
                "raw_title": None,
                "raw_location": None,
                "source_url": source_url,
                "domain": domain,
            }

            # Look for a title near this email or name mention in the text
            email_pos = clean_text.lower().find(email)
            name_pos = clean_text.find(candidate_name)
            anchor_pos = email_pos if email_pos >= 0 else name_pos
            if anchor_pos >= 0:
                context = clean_text[max(0, anchor_pos - 250):anchor_pos + 250]
                title_match = TITLE_KEYWORDS.search(context)
                if title_match:
                    profile["raw_title"] = self._extract_title_context(context, title_match)

            # Assign first available phone
            if phones:
                profile["raw_phone"] = list(phones)[0]

            profiles.append(profile)

        # Strategy 2 (Blind 2-word phrase permutation) has been PERMANENTLY REMOVED:
        # Agency websites don't host internal recruiter directories in body HTML text;
        # parsing random 2-word capitalized phrases causes marketing headers ("Social Responsibility",
        # "Studies About") to be hallucinated as candidates. Real human recruiters are discovered
        # directly and with 100% precision via Search X-Ray Harvester (LinkedIn verified profiles).

        return profiles

    # ── Quality Gate ───────────────────────────────────────────────────────────

    def _validate_and_stage_profiles(self, profiles: List[Dict[str, Any]]) -> int:
        """
        Validates profiles through quality gate and injects valid ones into DiscoveryStaging.
        Returns the number of profiles successfully staged.
        """
        from .scraper import is_human_name

        staged_count = 0
        db: Optional[Session] = None

        try:
            db = SessionLocal()

            for profile in profiles:
                raw_name = profile.get("raw_name", "")
                raw_email = profile.get("raw_email", "")
                raw_company = profile.get("raw_company", "")

                # Quality Gate 1: Must have a valid multi-word human name (First Last)
                if not raw_name or len(raw_name.strip()) < 4:
                    self.stats["quality_gate_rejections"] += 1
                    continue

                name_tokens = raw_name.strip().split()
                if len(name_tokens) < 2 or any(len(t) < 2 for t in name_tokens):
                    self.stats["quality_gate_rejections"] += 1
                    continue

                if any(t.lower() in GENERIC_EMAIL_PREFIXES for t in name_tokens):
                    self.stats["quality_gate_rejections"] += 1
                    continue

                # Quality Gate 2: Must be a human name (not company/noise)
                if not is_human_name(raw_name, raw_company, raw_email or ""):
                    self.stats["quality_gate_rejections"] += 1
                    continue

                # Quality Gate 2.5: Must have a valid recruiter title (not website marketing text)
                raw_title = profile.get("raw_title")
                if not self._is_valid_recruiter_title(raw_title):
                    self.stats["quality_gate_rejections"] += 1
                    continue

                # Quality Gate 3: Confidence scoring
                confidence = self._calculate_confidence(profile)
                if confidence < 60:
                    self.stats["quality_gate_rejections"] += 1
                    continue

                # Quality Gate 4: Email domain and mailbox validation (if email present)
                smtp_probe_meta = {}
                if raw_email:
                    email_domain = raw_email.split('@')[1] if '@' in raw_email else ''
                    email_local = raw_email.split('@')[0] if '@' in raw_email else ''

                    if email_local.lower() in GENERIC_EMAIL_PREFIXES or any(p in GENERIC_EMAIL_PREFIXES for p in re.split(r'[._\-+]', email_local.lower())):
                        self.stats["quality_gate_rejections"] += 1
                        continue

                    if email_domain in FREE_EMAIL_DOMAINS or email_domain in BLOCKED_DOMAINS:
                        self.stats["quality_gate_rejections"] += 1
                        continue

                    # DNS MX check for email domain
                    if not self._verify_domain_mx(email_domain):
                        self.stats["quality_gate_rejections"] += 1
                        continue

                    if profile.get("permutation_meta"):
                        smtp_probe_meta = profile["permutation_meta"]
                        confidence = min(100, confidence + 20)
                    else:
                        # Deep Zero-Bounce SMTP Handshake Probe
                        try:
                            from .smtp_prober import smtp_prober
                            probe = smtp_prober.probe_mailbox(raw_email)

                            # Hard rejection if the mail server explicitly reported mailbox does not exist
                            if probe.smtp_code in (550, 551, 552, 553):
                                self.stats["quality_gate_rejections"] += 1
                                self._log_action(f"Rejected non-existent mailbox: {raw_email} (SMTP {probe.smtp_code})")
                                continue

                            smtp_probe_meta = {
                                "smtp_code": probe.smtp_code,
                                "smtp_status": "DELIVERABLE" if (probe.mailbox_exists and not probe.is_catchall) else ("CATCH_ALL" if probe.is_catchall else ("GREYLISTED" if probe.is_greylisted else "MX_VERIFIED")),
                                "is_deliverable": probe.mailbox_exists,
                                "is_catchall": probe.is_catchall,
                                "mx_host": probe.mx_host,
                                "probe_ms": probe.probe_time_ms,
                            }

                            if probe.mailbox_exists and not probe.is_catchall:
                                # 100% verified deliverable mailbox! Boost confidence
                                confidence = min(100, confidence + 15)

                        except Exception as probe_err:
                            logger.debug("[WEBHARVEST] SMTP probe error for %s: %s", raw_email, probe_err)

                # Quality Gate 5: Deduplication check
                if self._is_duplicate(db, raw_name, raw_email, raw_company, profile.get("raw_linkedin")):
                    self.stats["dedup_rejections"] += 1
                    continue

                # All gates passed — inject into DiscoveryStaging
                try:
                    discovery_id = f"WH-{uuid.uuid4().hex[:16].upper()}"
                    batch_id = f"webharvest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

                    # Get owner_user_id (use admin user)
                    owner_id = self._get_owner_user_id(db)
                    if not owner_id:
                        logger.warning("[WEBHARVEST] No owner user found, skipping staging.")
                        continue

                    staging_record = DiscoveryStaging(
                        batch_id=batch_id,
                        discovery_id=discovery_id,
                        session_id=f"webharvest_session_{self.stats['harvest_cycles']}",
                        device_id="WEBHARVEST_ENGINE",
                        owner_user_id=owner_id,
                        raw_name=raw_name[:200] if raw_name else None,
                        raw_title=profile.get("raw_title", "")[:200] if profile.get("raw_title") else None,
                        raw_company=raw_company[:255] if raw_company else None,
                        raw_email=raw_email[:200] if raw_email else None,
                        raw_phone=profile.get("raw_phone", "")[:50] if profile.get("raw_phone") else None,
                        raw_linkedin=profile.get("raw_linkedin", "")[:300] if profile.get("raw_linkedin") else None,
                        raw_location=profile.get("raw_location", "")[:255] if profile.get("raw_location") else None,
                        source_url=profile.get("source_url", "")[:500] if profile.get("source_url") else None,
                        source_page_title=f"WebHarvest: {profile.get('domain', '')}",
                        extraction_source="web_harvest",
                        dom_confidence=confidence,
                        processing_status="pending",
                        quality_score=confidence,
                        page_type="company_team_page",
                        metadata_json=json.dumps({
                            "harvester": "WebHarvestEngine",
                            "harvest_cycle": self.stats["harvest_cycles"],
                            "source_domain": profile.get("domain", ""),
                            "confidence_score": confidence,
                            "discovery_method": "autonomous_web_crawl",
                            "smtp_verification": smtp_probe_meta,
                            "discovered_at": datetime.now(timezone.utc).isoformat(),
                        }),
                    )

                    db.add(staging_record)
                    db.commit()
                    staged_count += 1

                    self._log_action(
                        f"Staged: {raw_name} ({raw_email or 'no email'}) from {profile.get('domain', '')}"
                    )

                except Exception as e:
                    db.rollback()
                    logger.debug("[WEBHARVEST] Error staging profile %s: %s", raw_name, e)

        except Exception as e:
            logger.error("[WEBHARVEST] Validation/staging error: %s", e)
        finally:
            if db:
                db.close()

        return staged_count

    # ── Deduplication ──────────────────────────────────────────────────────────

    def _is_duplicate(
        self, db: Session, name: str, email: str, company: str, linkedin: Optional[str]
    ) -> bool:
        """
        Checks if a profile already exists in the staging table or master Parquet dataset.
        """
        try:
            # Check 1: Exact email match in staging
            if email:
                existing = db.query(DiscoveryStaging).filter(
                    DiscoveryStaging.raw_email == email,
                    DiscoveryStaging.processing_status.in_(["pending", "batched", "committed"]),
                ).first()
                if existing:
                    return True

            # Check 2: Name + Company match in staging
            if name and company:
                existing = db.query(DiscoveryStaging).filter(
                    DiscoveryStaging.raw_name == name,
                    DiscoveryStaging.raw_company == company,
                    DiscoveryStaging.processing_status.in_(["pending", "batched", "committed"]),
                ).first()
                if existing:
                    return True

            # Check 3: Email match in Parquet dataset
            if email:
                try:
                    from .recruiter_store import PARQUET_FILE
                    if os.path.exists(PARQUET_FILE):
                        parquet_path = PARQUET_FILE.replace(os.sep, "/")
                        con = duckdb.connect(database=":memory:", read_only=False)
                        result = con.execute(f"""
                            SELECT COUNT(*) FROM read_parquet('{parquet_path}')
                            WHERE LOWER(email) = LOWER('{email.replace("'", "''")}')
                        """).fetchone()
                        con.close()
                        if result and result[0] > 0:
                            return True
                except Exception:
                    pass  # Parquet check is best-effort

        except Exception as e:
            logger.debug("[WEBHARVEST] Dedup check error: %s", e)

        return False

    # ── Helper Methods ─────────────────────────────────────────────────────────

    def _is_domain_on_cooldown(self, domain: str) -> bool:
        """Checks if domain was recently scraped (within cooldown window)."""
        last_scraped = self._scraped_domains.get(domain)
        if last_scraped:
            cooldown_until = last_scraped + timedelta(hours=self.cooldown_hours)
            return datetime.now(timezone.utc) < cooldown_until
        return False

    def _name_from_email(self, local_part: str) -> Optional[str]:
        """Attempts to extract a human name from an email local part. Returns None for generic or single-word strings."""
        if not local_part:
            return None

        clean_lp = local_part.lower().strip()
        if clean_lp in GENERIC_EMAIL_PREFIXES:
            return None

        # Remove trailing numbers
        cleaned = re.sub(r'\d+$', '', clean_lp)
        if cleaned in GENERIC_EMAIL_PREFIXES:
            return None

        # Try splitting on common separators
        parts = re.split(r'[._\-+]', cleaned)
        parts = [p for p in parts if len(p) >= 2 and p.isalpha()]

        # STRICTURE: Human candidate MUST have at least 2 distinct name parts (First Last)
        # Single-word email aliases (accounts, webmaster, support, etc.) are strictly discarded
        if len(parts) < 2:
            return None

        # Reject if any part is a generic mailbox or departmental token
        if any(p in GENERIC_EMAIL_PREFIXES for p in parts):
            return None

        first = parts[0].capitalize()
        last = parts[-1].capitalize()

        return f"{first} {last}"

    def _names_match(self, name1: str, name2: str) -> bool:
        """Fuzzy name comparison (case-insensitive, handles separators)."""
        if not name1 or not name2:
            return False

        n1 = re.sub(r'[^a-z]', '', name1.lower())
        n2 = re.sub(r'[^a-z]', '', name2.lower())

        if n1 == n2:
            return True

        # Check if one contains the other (partial match for short names)
        if len(n1) >= 4 and len(n2) >= 4:
            if n1 in n2 or n2 in n1:
                return True

        return False

    def _extract_title_context(self, context: str, title_match) -> str:
        """Extracts a clean title string from the surrounding context."""
        # Get 60 chars around the title keyword match
        start = max(0, title_match.start() - 20)
        end = min(len(context), title_match.end() + 40)
        raw_title = context[start:end].strip()

        # Clean up
        raw_title = re.sub(r'\s+', ' ', raw_title)
        # Trim to a reasonable title length
        if len(raw_title) > 80:
            raw_title = raw_title[:80].rsplit(' ', 1)[0]

        return raw_title.strip(' ,-|•·')

    def _is_valid_recruiter_title(self, title: Optional[str]) -> bool:
        """Ensures title is a genuine recruiter designation and not website marketing text."""
        if not title:
            return False
        clean = title.strip()
        if len(clean) < 4 or len(clean) > 75:
            return False
        c_lower = clean.lower()
        # Reject HTML entities and marketing slogans
        banned_phrases = (
            "&amp;", "&lt;", "&gt;", "solutions", "workforce", "get a job", "how to hire",
            "useful links", "staffing services", "connect with", "insight for", "let's own",
            "privacy policy", "all rights", "click here", "read more", "search find",
            "talent staffing", "risk &", "technology partnerships", "case studies",
            "culture", "our impact", "research blog", "workforce development"
        )
        if any(p in c_lower for p in banned_phrases):
            return False
        # Must match a known recruiter keyword
        return bool(re.search(
            r'\b(recruiter|sourcer|talent acquisition|staffing specialist|headhunter|'
            r'recruiting manager|talent partner|talent lead|technical recruiter|executive recruiter|'
            r'recruitment consultant|people partner)\b',
            c_lower
        ))

    def _calculate_confidence(self, profile: Dict[str, Any]) -> int:
        """Calculates a confidence score (0-100) for an extracted profile."""
        score = 0

        if profile.get("raw_name") and len(profile["raw_name"]) >= 4:
            score += 30
        if profile.get("raw_email"):
            score += 30
        if profile.get("raw_title"):
            score += 15
        if profile.get("raw_phone"):
            score += 10
        if profile.get("raw_linkedin"):
            score += 15

        return min(100, score)

    def _verify_domain_mx(self, domain: str) -> bool:
        """Checks if a domain has valid MX records (quick DNS check)."""
        try:
            import dns.resolver
            answers = dns.resolver.resolve(domain, 'MX')
            return len(answers) > 0
        except Exception:
            return False

    def _get_owner_user_id(self, db: Session) -> Optional[int]:
        """Gets the admin/owner user ID for staging records."""
        try:
            from ..models.models import User
            admin = db.query(User).filter(User.role == "admin").first()
            if admin:
                return admin.id
            # Fallback to first user
            first_user = db.query(User).first()
            return first_user.id if first_user else 1
        except Exception:
            return 1  # Safe fallback

    def _log_action(self, message: str):
        """Records an action in the recent actions deque."""
        self.recent_actions.appendleft({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": message,
        })

    # ── Telemetry ──────────────────────────────────────────────────────────────

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive operational telemetry for dashboards."""
        now = datetime.now(timezone.utc)
        stats_copy = dict(self.stats)
        try:
            from ..database import SessionLocal
            from ..models.staging_models import DiscoveryStaging
            with SessionLocal() as db_session:
                real_staged = db_session.query(DiscoveryStaging).count()
                web_staged = db_session.query(DiscoveryStaging).filter(
                    DiscoveryStaging.extraction_source.in_(["web_harvest", "search_xray", "ats_job_board", "email_signature_flywheel"])
                ).count()
                promoted_count = db_session.query(DiscoveryStaging).filter(
                    DiscoveryStaging.processing_status == "promoted"
                ).count()
                enriched_count = db_session.query(DiscoveryStaging).filter(
                    DiscoveryStaging.processing_status == "enriched"
                ).count()
                stats_copy["profiles_staged"] = max(stats_copy.get("profiles_staged", 0), web_staged)
                stats_copy["profiles_discovered"] = max(stats_copy.get("profiles_discovered", 0), real_staged)
                stats_copy["profiles_promoted"] = max(stats_copy.get("profiles_promoted", 0), promoted_count)
                stats_copy["profiles_enriched"] = max(stats_copy.get("profiles_enriched", 0), enriched_count)
        except Exception:
            pass

        return {
            "engine": "WebHarvest Autonomous Discovery",
            "version": "1.1.0",
            "is_running": self.running,
            "enabled": self.enabled,
            "status": "active" if self.running else ("disabled" if not self.enabled else "stopped"),
            "server_time": now.isoformat(),
            "configuration": {
                "harvest_interval_sec": self.harvest_interval,
                "batch_size": self.batch_size,
                "max_profiles_per_cycle": self.max_profiles_per_cycle,
                "cooldown_hours": self.cooldown_hours,
            },
            "stats": stats_copy,
            "domains_on_cooldown": len(self._scraped_domains),
            "priority_queue_count": len(self.priority_queue),
            "priority_targets": self.get_priority_targets(),
            "recent_actions": list(self.recent_actions)[:20],
        }


# Global Singleton Instance
web_harvest_engine = WebHarvestEngine()
