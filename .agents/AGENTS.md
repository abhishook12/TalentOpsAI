# Permanent Scout Dual-Sync Rule (Strict Mandate)

Whenever ANY update, platform addition, heuristic enhancement, field extraction modification, or configuration change (even small changes) is made to Desktop Scout (scout_desktop/), it MUST simultaneously and automatically be updated and synchronized across the Web Site Scout, Backend, and Fleet Dashboard without requiring the user to remind you.

## 1. Scope & Synchronization Requirements

Every change touching Desktop Scout must be audited and applied across the following layers:

### A. Desktop Scout (scout_desktop/)
1. Target Allowlist & Window Filtering:
   - scout_desktop/core/window_tracker.py: Ensure window process and title matching include the platform (e.g., Target 7: ZoomInfo, Apollo).
   - scout_desktop/app.py: Ensure Gate 3 allowed_domains contains the target domain(s).
2. Browser & Context Classification:
   - scout_desktop/core/browser_tracker.py: Register platform in KNOWN_PLATFORMS, define context regex (e.g. /profile/, /contacts, /search), and add title parsing patterns.
3. Extraction & Noise Filtering:
   - scout_desktop/extractor/patterns.py: Add platform-specific UI action words to UI_ACTIONS and non-candidate noise blacklist.
   - scout_desktop/extractor/semantic_factorizer.py: Register platform in is_verified_sourcing_platform and factorize candidate names, titles, and breadcrumbs.
   - scout_desktop/extractor/entity_extractor.py: Add layout parsing, breadcrumbs, and regex matching.
4. Desktop UI & Versioning:
   - scout_desktop/ui/main_window.py: Include platform scanning states, active status badges, and allowlist labels.
   - scout_desktop/config.json & scout_desktop/version.py: Maintain synchronized version numbering.

### B. Backend Services & Telemetry (backend/)
1. Contributor & Telemetry Ingestion:
   - backend/app/services/scout_contributor_service.py: Add platform to default source_counts breakdown and URL attribution heuristics.
   - backend/app/routes/scout_contributors.py: Update endpoint docs and API response filters.
2. Staging & Processing Pipelines:
   - backend/app/models/staging_models.py & backend/app/services/discovery_processor.py: Support new extraction attributes and platform sources.

### C. Web Frontend & Fleet UI (frontend/)
1. Scout Drawer & Profile Badges:
   - frontend/src/components/ScoutUserProfileDrawer.jsx: Add custom color, background badge, icon, and platform category descriptor in the Source breakdown tab.
2. Navigation & Versioning:
   - frontend/src/components/Sidebar.jsx: Update Desktop Scout version pill to match desktop release.
3. Hub & Onboarding Documentation:
   - frontend/src/pages/ExtensionHub.jsx: Reflect all newly supported sourcing platforms.

---

## 2. Strict Verification Mandate (Rule 11)
Before reporting completion to the user:
- Execute at least 3 distinct verification checks with verifiable proof.
- Verify Desktop extraction logic, Backend telemetry/source counting, and Frontend build integrity.

---

## 3. Permanent Autonomous Engine Perpetuity & Never-Stop Mandate (Strict User Mandate)

All autonomous discovery, harvesting, enrichment, and pipeline background engines MUST run perpetually 24/7/365 without exception:

1. **Zero Browser Dependency**: All background engines (WebHarvest, Night Sweeper, Offline Buffer Watchdog, Sequence Schedulers) MUST operate 100% server-side and headless. Under NO circumstances should any crawler or background process depend on whether a browser tab (`localhost:5173`) is open, focused, minimized, or closed.
2. **Anti-Starvation & Immortality Guard**: Seed generators and target selection loops must NEVER enter a 0-target idle deadlock when domains enter cooldown. Expired cooldowns must automatically decay, and emergency immortal baseline seeds must activate to guarantee perpetual cycle execution.
3. **Internal Auto-Revival (Engine Immunity Sentinel)**: The in-process `EngineImmunitySentinel` must remain active in `main.py`, checking engine heartbeats every 30s and auto-reviving any stopped or stagnated loop in <5 seconds.
4. **OS-Level Process Supervisor**: `backend/talentops_supervisor.py` must remain permanently running via Windows Startup (`shell:startup`) and Windows Task Scheduler (`TalentOpsPerpetualSupervisor`). If the backend process ever crashes, terminates, or the PC wakes from sleep/hibernation, the supervisor must immediately auto-relaunch it.
5. **No Code May Break This Guarantee**: No future agent is permitted to disable, remove, or comment out these sentinel layers or make background workers contingent on user UI actions.

---

## 4. Permanent System Architecture Mandate — Systemic Embedding of User Directives (Strict User Mandate)

Every user requirement, rule, instruction, or architectural preference is a PERMANENT, NON-NEGOTIABLE COMMAND to be implemented directly into the system code, automated pipelines, database schemas, and background sentinels:

1. **Never a One-Off Patch**: Every instruction given by the user must be engineered as a permanent, systemic mechanism. It must automatically govern all current records AND all upcoming, future discoveries without requiring the user to ever repeat the instruction.
2. **Permanent Autonomous Ingestion Compliance**: All background harvesters, crawlers, Desktop Scout nodes, and staging enrichers must permanently adhere to user commands natively during every execution loop.
3. **No Code May Dilute User Directives**: Future agents are forbidden from reverting, softening, bypassing, or removing logic codified per user directives.

---

## 5. Permanent Autonomous Corporate Email Intelligence & Deliverability Gate (Strict Mandate)

Whenever ANY candidate profile is staged or ingested that has a confirmed or inferrable company but lacks a confirmed, deliverable email, the system MUST autonomously execute the following 5-phase intelligence loop:

1. **Phase 1: Autonomous Domain & Entity Resolution**:
   - Company names must never be platform noise (`Linkedin`, `Google`, `Facebook`, etc.).
   - If raw company is a platform name or missing, infer the true company from the URL context (e.g. `/company/<slug>/`) or source page title.
   - Clean UI action terms (`Contact`, `View Profile`, `Connect`, etc.) out of job titles immediately.
   - Resolve company's canonical corporate domain via dictionary, database match (whitespace-insensitive slug matching), and DNS MX verification.
2. **Phase 2: Cross-Colleague Pattern Mining**:
   - Query existing colleagues in the master catalog (`recruiters`) at that corporate domain.
   - Reverse-engineer empirical email formulas (`first.last`, `f_last`, `first`, `first_last`, etc.) from verified colleagues.
   - Prioritize empirical colleague patterns over generic seeds.
3. **Phase 3: Multi-Formula Permutation Synthesis**:
   - Synthesize corporate email candidates for the person using the deduced company formula(s).
4. **Phase 4: Non-Intrusive Live Deliverability Probing (Port 25 SMTP & MX)**:
   - Perform live DNS MX lookup and identify provider (Google Workspace, Microsoft 365, etc.).
   - Execute non-intrusive Port 25 SMTP RCPT TO mailbox handshake probes.
   - Code 250: Mailbox exists -> verified deliverable (`SMTP_VERIFIED`).
   - Code 550: Server rejects mailbox -> cycle through remaining permutations until finding deliverable format or concluding bounce.
   - Catchall: Assign `CATCHALL_VERIFIED` / `PATTERN_VERIFIED` with high confidence.
   - Auto-persist verified formulas to `company_email_patterns` to train the intelligence registry for future colleagues.
5. **Phase 5: Master DB Committal & Hard Lockdown**:
   - Attach ONLY deliverable corporate emails.
   - Synthetic placeholder emails (`@unknown.com`, `@noemail.talentops`) are HARD BLOCKED across all gates and databases.

