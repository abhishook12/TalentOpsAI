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
