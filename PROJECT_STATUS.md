# ==================================================
# PROJECT_STATUS.md — TalentOps AI (Handover Report)
# Generated: 2026-06-01
# Repo root: C:\TalentOpsAI
# ==================================================

> Note (per request): No code changes were made. This report is based on reading the current repository state and Git history. Neon/Render/Vercel “live status” cannot be queried from the repo alone; where applicable, this document flags items as **Unknown / Needs Verification**.


==================================================
PROJECT OVERVIEW
==================================================

- **Project name:** TalentOps AI
- **Purpose:** Recruitment operations intelligence platform — recruiter/company directory, ranked recruiter search, ETL imports, analytics, and admin tooling.

- **Tech stack**
  - **Frontend:** React 19 + Vite, React Router, TanStack React Query, Axios, Recharts, Tailwind CSS
  - **Backend:** FastAPI + Uvicorn, SQLAlchemy 2.x, Pydantic 2.x, Pandas/OpenPyXL for uploads
  - **Database:** PostgreSQL (designed for Neon in prod; local Postgres supported)

- **Frontend deployment**
  - **Provider:** Vercel
  - **App URL (from `README.md`):** `https://talent-ops-ai.vercel.app`
  - **Routing:** `frontend/vercel.json` rewrites all routes to `/` (SPA routing support).

- **Backend deployment**
  - **Provider:** Render (also includes `railway.json` / `nixpacks.toml` support patterns)
  - **API URL(s) referenced in repo:**
    - `README.md` + `check_site.py`: `https://talentopsai.onrender.com`
    - Frontend production override (`frontend/src/services/api.js` + `frontend/.env.production`): `https://talentopsai-1.onrender.com`
  - **Startup command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (see `backend/Procfile`, `backend/nixpacks.toml`, `backend/railway.json`)

- **Database provider**
  - **Intended provider:** Neon Postgres (per `README.md` and scripts prompting for Neon `DATABASE_URL`)
  - **Connection:** via `DATABASE_URL` env var; SQLAlchemy URL is normalized to `postgresql+psycopg://...` in `backend/app/database.py`.

- **Current architecture (high level)**
  - **React SPA** (`frontend/src/main.jsx` → `frontend/src/App.jsx`) with routes:
    - `/` Dashboard
    - `/recruiters` Recruiters
    - `/ai-search` AI Search (ranked recruiter search)
    - `/analytics` Analytics
    - `/directory` State Directory
    - `/companies` Company Directory
    - `/upload` ETL Upload (Smart upload / paste / legacy CSV / job history)
    - `/admin` Admin Terminal
  - **FastAPI backend** (`backend/app/main.py`) includes routers:
    - `/recruiters`, `/companies`, `/vendors`, `/analytics`, `/upload`, `/admin`, `/auth`
  - **Database layer**
    - ORM models in `backend/app/models/models.py`
    - Direct SQL used for some endpoints (notably ranked search) for performance/SQL features.
  - **Search**
    - Uses Postgres `pg_trgm` similarity + weighted scoring.
    - `pg_trgm` extension is attempted at startup (`backend/app/main.py`).


==================================================
CURRENT WORKING STATUS
==================================================

Status definitions:
- **Working:** Expected to function based on implementation and recent fixes.
- **Partially Working:** Core exists; likely edge cases or dependencies unverified.
- **Broken:** Clear code defect or missing dependency.
- **Needs Testing:** Implemented; must be verified end-to-end against deployed backend/DB.

- **Dashboard:** **Needs Testing**
  - Implemented + recently redesigned; relies on backend counts + visit stats.

- **Recruiters:** **Needs Testing**
  - CRUD/listing/filtering exist on backend (`/recruiters`) and frontend page is present.

- **State Directory:** **Needs Testing**
  - Frontend has export and crash fixes in Git history; backend-side response shapes must be verified.

- **Company Directory:** **Needs Testing**
  - Backend `/companies` endpoints exist; UI page present.

- **Analytics:** **Needs Testing**
  - Uses React Query on frontend; depends on backend analytics/admin visit tracking.

- **ETL Upload:** **Partially Working**
  - Full upload workflow exists (jobs + staging tables + worker), but it is complex and requires verification of:
    - file parsing, job creation, staging population,
    - background processing (`etl_worker`/`etl_pipeline`),
    - UI job history and error reporting.

- **AI Search:** **Partially Working**
  - Frontend UI and backend `/recruiters/search` are implemented.
  - Requires `pg_trgm` extension and benefits from trigram indexes; must be verified on Neon/Render.

- **Database:** **Needs Testing**
  - Schema has evolved beyond `schema.sql` (ORM includes additional tables such as `page_visits`, `upload_jobs`, staging tables).
  - Live data state on Neon cannot be confirmed from repo.

- **Backend APIs:** **Needs Testing**
  - FastAPI is wired with routers and health endpoints; correctness depends on env vars + DB migrations/indexes.

- **Frontend UI:** **Needs Testing**
  - SPA routes exist; depends on correct backend URL selection and CORS.


==================================================
RECENT CHANGES MADE
==================================================

Interpretation: “this session” = the most recent Git commits visible in `git log` (dated 2026-05-23 through 2026-05-30). If you need a different window, re-run `git log --since=...`.

Key recent changes (commit → files → purpose → expected result):

- **2026-05-30 — `ba0e932`**
  - **Files:** `backend/app/database.py`, `backend/app/main.py`, `backend/app/routes/recruiters.py`
  - **Purpose:** Sync pending DB + recruiter route updates (connection pooling, startup behaviors, recruiter logic).
  - **Expected result:** More stable DB connections; startup index/extension logic and recruiter APIs aligned.

- **2026-05-30 — `c293fc7`**
  - **Files:** `frontend/src/pages/AISearch.jsx`
  - **Purpose:** Prevent recruiter detail panel from auto-opening; require explicit row click.
  - **Expected result:** Less confusing UX; avoids “random” recruiter showing when results refresh.

- **2026-05-30 — `70976d6`**
  - **Files:** `frontend/src/components/Sidebar.jsx`, `frontend/src/pages/AISearch.jsx`
  - **Purpose:** AI Search redesign with recruiter detail panel; “real-data-only” empty/loading states.
  - **Expected result:** Modern split-pane search UX; clearer states when no query/results.

- **2026-05-30 — `09ff9ab`**
  - **Files:** `frontend/src/pages/Dashboard.jsx`, `frontend/src/services/api.js`
  - **Purpose:** Normalize dark-mode contrast; force prod API host override when on `talent-ops-ai.vercel.app`.
  - **Expected result:** Readable dashboard in dark theme; avoids wrong backend host in production.

- **2026-05-30 — `57b17cf`**
  - **Files:** `frontend/src/App.jsx`, `frontend/src/pages/Dashboard.jsx`
  - **Purpose:** Add world traffic map + restore dark mode toggle UX elements.
  - **Expected result:** Dashboard richer; theme controls visible.

- **2026-05-30 — `a106dea`**
  - **Files:** `frontend/src/pages/Dashboard.jsx`
  - **Purpose:** Bind KPI totals to `/recruiters` and `/companies` API counts.
  - **Expected result:** KPIs reflect real DB totals rather than placeholders.

- **2026-05-30 — `971c391`, `7b6378e`, `fe771c2`, `a00af28`, `4e75124`**
  - **Files:** Mostly `frontend/src/App.jsx`, `frontend/src/components/Sidebar.jsx`, `frontend/src/pages/Dashboard.jsx`
  - **Purpose:** Shell/sidebar/dashboard redesign and theme palette refresh.
  - **Expected result:** “Editorial recruiter intelligence” look-and-feel across the shell.

- **2026-05-28 — `12082e4`**
  - **Files:** `frontend/.env.production`
  - **Purpose:** Point production API to `https://talentopsai-1.onrender.com`.
  - **Expected result:** Vercel prod build uses the newer Render service host.

- **2026-05-23 — `3180225`, `73f203f`**
  - **Files:** `frontend/src/pages/Analytics.jsx`, `frontend/src/index.css`
  - **Purpose:** Analytics data fetching via React Query; chart readability fixes.
  - **Expected result:** More reliable fetching/loading states; readable analytics visuals.

- **2026-05-23 — `4333613`, `386ec32`**
  - **Files:** `frontend/src/pages/StateDirectory.jsx` (and backend pyc artifacts committed in history)
  - **Purpose:** XLS export button; fix crash when API returns paginated object.
  - **Expected result:** State directory stable across response shapes; export capability.

- **2026-05-23 — `69e2009`**
  - **Files:** `frontend/src/App.jsx`
  - **Purpose:** Handle `ChunkLoadError` after Vercel deploys.
  - **Expected result:** App auto-recovers by reloading if a chunk mismatch occurs.

- **2026-05-23 — `40a7a6b`**
  - **Files:** `frontend/src/pages/Upload.jsx`
  - **Purpose:** Fix missing `useEffect` import.
  - **Expected result:** Upload page no longer crashes at runtime.

- **2026-05-23 — `2d793e3`, `3550409`**
  - **Files:** `gemma.js`, root `.env.example`, backend ETL/analytics-related files, and some frontend dependencies
  - **Purpose:** Add a Gemini proxy server; improve analytics error handling + ETL pipeline code.
  - **Expected result:** Optional AI proxy available; analytics/ETL flows more resilient.


==================================================
DATABASE STATUS
==================================================

**Current Neon status:** **Unknown / Needs Verification**
- This repo contains the connection logic, schema definitions, and indexing scripts, but not the live Neon console state.
- To confirm live Neon status, log into Neon and inspect:
  - DB size/storage usage, compute tier, connection limits
  - table row counts (especially recruiters, companies, page_visits, upload_jobs, staging tables)

**Tables (from ORM `backend/app/models/models.py`)**
- `companies`
- `vendors`
- `recruiters`
- `candidates`
- `submissions`
- ETL/Uploads:
  - `upload_jobs`
  - `raw_uploads`
  - `staging_recruiters`
  - `staging_companies`
- Analytics/Admin:
  - `page_visits`
  - `action_logs`

**Important schema notes**
- `schema.sql` (root) is **not the full current schema**; it lacks the analytics + ETL tables above and newer recruiter/company fields.
- Ranked search uses Postgres trigram similarity:
  - `pg_trgm` extension is created (best-effort) during startup in `backend/app/main.py`.
  - Additional recommended indexes are created by `backend/app/create_indexes.py` (trigram GIN indexes).

**Data state / cleanup performed / deletions**
- **Live data state:** Unknown (cannot be inferred without DB access).
- **Cleanup performed:** No evidence of automated cleanup being run; a cleanup script exists:
  - `backend/app/scripts/cleanup_db.py` deletes old `page_visits` based on `PAGE_VISIT_RETENTION_DAYS` (default 30) and attempts `VACUUM`.
- **Anything deleted:** Unknown (DB access required).
- **Storage situation:** Unknown (Neon console required).
- **Remaining concerns**
  - Ensure trigram indexes exist on production DB for acceptable search latency.
  - Ensure migrations/DDL strategy is consistent (some DDL is startup-driven).
  - Remove/avoid committing `__pycache__/*.pyc` artifacts (they appear in Git history and are currently dirty in working tree).


==================================================
DEPLOYMENT STATUS
==================================================

Frontend (Vercel)
- **Vercel status:** **Unknown / Needs Verification** (requires Vercel dashboard access)
- **Current URL (from `README.md`):** `https://talent-ops-ai.vercel.app`
- **Backend URL selection logic**
  - `frontend/src/services/api.js` forces `https://talentopsai-1.onrender.com` **only** when the browser hostname is exactly `talent-ops-ai.vercel.app`.
  - Otherwise uses `import.meta.env.VITE_API_URL` (from `.env` / Vercel env vars).
- **Known issues**
  - If Vercel domain changes (preview domains/custom domains), the hardcoded override may not trigger, and the app may hit the wrong API.
  - SPA routing depends on `frontend/vercel.json` rewrite; confirm it is active in the deployed project.

Backend (Render)
- **Render status:** **Unknown / Needs Verification** (requires Render dashboard access)
- **Startup command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Last deployment state:** Unknown (requires Render logs)
- **Known issues / watchouts**
  - Ensure env vars set on Render: `ENV=production`, `DATABASE_URL`, `JWT_SECRET`, `ADMIN_PASSWORD`, `CORS_ORIGINS`.
  - Backend attempts DB-side actions at import/startup time (`pg_trgm`, `admin.migrate_page_visits`); DB connectivity must be available during boot.


==================================================
AI SEARCH STATUS
==================================================

How search currently works
- **Frontend UI:** `frontend/src/pages/AISearch.jsx`
  - Debounced query (260ms) calls `GET {API}/recruiters/search?q=...&limit=...` plus optional filters.
  - Client-side secondary sorting:
    - “Exact” matches first (by name/email/company equality or prefix), then “Fuzzy”.
    - Within group, sorts by backend-provided `relevance_score` descending.

- **Backend endpoint:** `backend/app/routes/recruiters.py` → `GET /recruiters/search`
  - Returns rows with a computed integer `relevance_score`.
  - Uses weighted scoring:
    - Strong boosts for exact/prefix matches on recruiter name and email.
    - Medium boosts for contains matches (name/email/company/specialization).
    - Adds trigram similarity components:
      - `ROUND(similarity(r.recruiter_name, :q) * 30)`
      - `ROUND(similarity(r.email, :q) * 15)`
  - Filters include:
    - `company` (ILIKE on company name)
    - `specialization` (ILIKE)
    - `location` is treated as **state** if `normalize_state(location)` succeeds.

Ranking logic (summary)
- “Hard” match signals (exact/prefix/contains) dominate ranking.
- Trigram similarity provides fuzzy ranking and broad recall when ILIKE is insufficient.

Fuzzy matching logic
- Backend includes candidates if:
  - ILIKE contains hits on key fields OR
  - trigram similarity above threshold: `similarity(name, q) > 0.3` OR `similarity(email, q) > 0.3`
- Production performance depends heavily on `pg_trgm` and trigram indexes.

Recruiter popup / detail panel logic
- The recruiter detail panel is a **split pane** on the AI Search page.
- It stays empty until the user clicks a row:
  - `selectedId` is only set on explicit row click.
  - When results refresh, selection is cleared if the selected recruiter is no longer in the current result set.

Known limitations
- Search is “smart ranked” but not semantic/LLM-based; it is string similarity + heuristics.
- Location filter currently behaves like a state filter when it can normalize input; city-level fuzzy location matching is not implemented in AI search.
- Without `pg_trgm` + GIN trigram indexes, the query can become slow on large recruiter datasets.


==================================================
UI REDESIGN STATUS
==================================================

Dashboard redesign direction
- Goal: “Recruiter intelligence / editorial ops” dashboard shell with cards, clean typography, and dark-first presentation.
- Implemented in:
  - `frontend/src/App.jsx` (global CSS variables, layout shell, sidebar + footer)
  - `frontend/src/pages/Dashboard.jsx` (KPIs, map/visuals, UI composition)

Recruiter intelligence redesign direction
- Implemented partially via:
  - Shell/sidebar style system in `frontend/src/App.jsx` and `frontend/src/components/Sidebar.jsx`
  - Recruiter-related pages exist (`/recruiters`, `/ai-search`), but “intelligence” metrics depend on data quality fields + analytics.

AI search redesign direction
- Implemented split-pane “Smart Search” with:
  - Search input + optional filters (company/location/specialization)
  - Ranked list with match-type tags
  - Detail panel (explicit selection)
  - Clear empty/loading/error states

Completed work
- Global shell + theme tokens + sidebar redesign
- AI Search split-pane UI
- Production API host override logic
- Analytics page refactor to React Query

Pending work (high-value)
- Verify AI Search performance and correctness on production DB
- Remove obvious UI bug in AI Search header style (`fontSize: 52? 0: 18`)
- Consolidate and document the “current” production backend URL (`talentopsai` vs `talentopsai-1`)
- Validate ETL end-to-end and add operational guardrails (limits, retries, visibility)


==================================================
CRITICAL FILES
==================================================

Frontend
- **Entry points**
  - `frontend/src/main.jsx`
  - `frontend/src/App.jsx`
- **Routes/pages**
  - `frontend/src/pages/Dashboard.jsx`
  - `frontend/src/pages/Recruiters.jsx`
  - `frontend/src/pages/AISearch.jsx`
  - `frontend/src/pages/Analytics.jsx`
  - `frontend/src/pages/StateDirectory.jsx`
  - `frontend/src/pages/CompanyDirectory.jsx`
  - `frontend/src/pages/Upload.jsx`
  - `frontend/src/pages/AdminTerminal.jsx`
- **API client**
  - `frontend/src/services/api.js`
- **Shell component**
  - `frontend/src/components/Sidebar.jsx`

Backend
- **App entry points**
  - `backend/app/main.py`
  - `backend/app/config.py`
  - `backend/app/database.py`
- **ORM models**
  - `backend/app/models/models.py`
- **Core routes**
  - `backend/app/routes/recruiters.py` (includes `/recruiters/search`)
  - `backend/app/routes/companies.py`
  - `backend/app/routes/upload.py`
  - `backend/app/routes/analytics.py`
  - `backend/app/routes/admin.py`
  - `backend/app/routes/auth.py`
- **ETL**
  - `backend/app/services/etl_pipeline.py`
  - `backend/app/services/etl_worker.py`
- **Indexing / perf**
  - `backend/app/create_indexes.py`

Root/ops
- `README.md` (deploy + env var overview; may contain older hostnames)
- `schema.sql` (baseline schema; not fully current vs ORM)
- `check_site.py` (quick health checks, references older Render URL)


==================================================
KNOWN BUGS
==================================================

1) **Severity: High (UI bug / likely runtime issue)**
- **Location:** `frontend/src/pages/AISearch.jsx`
- **Issue:** Invalid/accidental ternary in inline style: `fontSize: 52? 0: 18`
- **Impact:** Could break rendering or produce unintended styles.
- **Suggested fix:** Replace with a valid number (e.g. `fontSize: 18`) or a real conditional expression.

2) **Severity: Medium (environment/config correctness risk)**
- **Location:** `frontend/src/services/api.js`, `frontend/.env.production`, `README.md`, `check_site.py`
- **Issue:** Two Render hostnames referenced (`talentopsai.onrender.com` vs `talentopsai-1.onrender.com`).
- **Impact:** UI may hit the wrong backend depending on hostname and env vars; monitoring scripts may check the wrong service.
- **Suggested fix:** Choose the canonical backend URL, update README + scripts, and remove hostname-specific overrides if possible.

3) **Severity: Medium (portability/ops risk)**
- **Location:** `backend/app/create_indexes.py`
- **Issue:** Hardcoded Windows path to `.env` (`C:\\TalentOpsAI\\backend\\.env`).
- **Impact:** Script won’t work in Linux/Render environment and may mislead operators.
- **Suggested fix:** Read `DATABASE_URL` from process env by default; accept a path argument for local use.

4) **Severity: Medium (deployment instability risk)**
- **Location:** `backend/app/main.py`
- **Issue:** DB DDL actions at import/startup time (`CREATE EXTENSION`, migration helper calls).
- **Impact:** If DB unavailable during boot, app may partially start or log warnings; cold starts can be slower.
- **Suggested fix:** Move DDL/migrations to explicit migration step; guard with env flag and robust retries.

5) **Severity: Low (repo hygiene)**
- **Location:** `git status` currently shows modified `backend/app/**/__pycache__/*.pyc` and untracked local files.
- **Impact:** Dirty working tree; risk of committing binary artifacts.
- **Suggested fix:** Delete `__pycache__` and ensure `.gitignore` covers them; avoid committing `*.pyc`.


==================================================
NEXT PRIORITY TASKS
==================================================

Top 20 recommended next tasks (ordered)

1) **P0 — Verify production backend URL and standardize**
   - **Reason:** Conflicting hostnames; prod override logic is fragile.
   - **Affected files:** `frontend/src/services/api.js`, `frontend/.env.production`, `README.md`, `check_site.py`
   - **Effort:** 1–2 hours

2) **P0 — Fix AI Search UI style bug**
   - **Reason:** `fontSize: 52? 0: 18` is incorrect.
   - **Affected files:** `frontend/src/pages/AISearch.jsx`
   - **Effort:** 10–30 minutes

3) **P0 — Confirm Neon schema matches ORM (tables + columns)**
   - **Reason:** `schema.sql` is incomplete vs current models; prevent runtime failures.
   - **Affected files:** `backend/app/models/models.py`, (Neon console), any migration scripts
   - **Effort:** 1–3 hours

4) **P0 — Ensure `pg_trgm` + trigram indexes exist in prod**
   - **Reason:** AI Search performance depends on it.
   - **Affected files:** `backend/app/main.py`, `backend/app/create_indexes.py`
   - **Effort:** 1 hour

5) **P0 — Run end-to-end smoke test against deployed stack**
   - **Reason:** Many areas are “Needs Testing”.
   - **Affected files:** (operational), all key pages and APIs
   - **Effort:** 2–4 hours

6) **P1 — Document/implement migrations strategy**
   - **Reason:** Avoid startup-time DDL and schema drift.
   - **Affected files:** `backend/app/main.py`, `backend/app/models/models.py`, migration scripts
   - **Effort:** 4–8 hours

7) **P1 — Harden ETL job processing and visibility**
   - **Reason:** ETL has multiple moving parts; needs clear failure handling.
   - **Affected files:** `backend/app/routes/upload.py`, `backend/app/services/etl_pipeline.py`, `backend/app/services/etl_worker.py`, `frontend/src/pages/Upload.jsx`
   - **Effort:** 6–12 hours

8) **P1 — Verify State Directory API response shapes**
   - **Reason:** Past crashes due to paginated object responses.
   - **Affected files:** `frontend/src/pages/StateDirectory.jsx`, backend directory endpoints (likely `backend/app/routes/admin.py` or `backend/app/routes/analytics.py`)
   - **Effort:** 2–4 hours

9) **P1 — Normalize CORS configuration for current frontend URLs**
   - **Reason:** Vercel previews/custom domains can break auth/requests.
   - **Affected files:** `backend/app/config.py`, Render env vars
   - **Effort:** 1–2 hours

10) **P1 — Add a single “API base URL” source of truth**
   - **Reason:** Remove hostname-based override branching.
   - **Affected files:** `frontend/src/services/api.js`
   - **Effort:** 1–2 hours

11) **P2 — Add basic API contract tests (or Postman collection)**
   - **Reason:** Prevent regressions while iterating in a new IDE.
   - **Affected files:** new docs/tests folder
   - **Effort:** 3–6 hours

12) **P2 — Remove/ignore `__pycache__` artifacts**
   - **Reason:** Repo hygiene, avoid accidental commits.
   - **Affected files:** `.gitignore`, local filesystem cleanup
   - **Effort:** 15–30 minutes

13) **P2 — Verify analytics “visit tracking” ingestion**
   - **Reason:** Analytics depends on `page_visits` and logging endpoints.
   - **Affected files:** `backend/app/routes/analytics.py`, `backend/app/models/models.py`, frontend analytics/dashboard pages
   - **Effort:** 2–4 hours

14) **P2 — Add DB constraints/indexes for ETL staging tables**
   - **Reason:** Prevent duplicates, improve job processing speed.
   - **Affected files:** `backend/app/models/models.py`, DB migration/index scripts
   - **Effort:** 2–6 hours

15) **P2 — Validate recruiter/company “normalized_*” columns exist**
   - **Reason:** Recruiter listing filters use normalized fields.
   - **Affected files:** `backend/app/routes/recruiters.py`, `backend/app/models/models.py`, DB schema
   - **Effort:** 1–2 hours

16) **P3 — Reconcile and update `schema.sql` (or deprecate it)**
   - **Reason:** Prevent confusion for new environment setups.
   - **Affected files:** `schema.sql`, `README.md`
   - **Effort:** 2–4 hours

17) **P3 — Add operational docs for cleanup and retention**
   - **Reason:** `page_visits` growth can affect storage.
   - **Affected files:** `backend/app/scripts/cleanup_db.py`, `README.md`
   - **Effort:** 1–2 hours

18) **P3 — Confirm authentication flow in production**
   - **Reason:** `/auth` endpoints + cookies/CORS can behave differently on Vercel/Render.
   - **Affected files:** `backend/app/routes/auth.py`, `frontend/src/services/api.js`, Render/Vercel env
   - **Effort:** 2–4 hours

19) **P3 — Review and remove unused Gemini proxy if not needed**
   - **Reason:** Reduce surface area if AI proxy isn’t used.
   - **Affected files:** `gemma.js`, root `package.json`, `.env.example`
   - **Effort:** 1–2 hours

20) **P3 — Add “About / Version” stamp in UI**
   - **Reason:** Helps debug chunk/deploy mismatches and support.
   - **Affected files:** `frontend/src/App.jsx` or footer component
   - **Effort:** 1–2 hours


==================================================
FOR NEXT IDE
==================================================

Concise briefing (copy/paste for another AI IDE)

- You are taking over **TalentOps AI**, a React (Vite) + FastAPI + Postgres app for recruitment ops intelligence.
- Frontend routes live in `frontend/src/App.jsx` and pages under `frontend/src/pages/*`.
- Backend entry is `backend/app/main.py` with routers under `backend/app/routes/*` and ORM models in `backend/app/models/models.py`.
- Production URLs are inconsistent in repo:
  - README/scripts reference `https://talentopsai.onrender.com`
  - Frontend production override points to `https://talentopsai-1.onrender.com`
  - First task is to confirm the **canonical** backend URL and update config/docs accordingly.
- “AI Search” is not LLM-based: it’s Postgres `pg_trgm` similarity + weighted scoring implemented in `backend/app/routes/recruiters.py` (`GET /recruiters/search`) and rendered as a split-pane UI in `frontend/src/pages/AISearch.jsx`.
- DB schema in `schema.sql` is a baseline only; the real current schema includes analytics + ETL tables (page visits, upload jobs, staging tables) defined in ORM.
- ETL upload system exists but needs end-to-end verification: upload routes + staging tables + worker/pipeline + Upload UI tabs.
- Immediate fixes:
  1) Fix AI Search header style bug in `frontend/src/pages/AISearch.jsx`
  2) Standardize backend URL config (remove fragile hostname override)
  3) Verify Neon schema + indexes (`pg_trgm`, trigram GIN) and run a full smoke test across all major pages.

