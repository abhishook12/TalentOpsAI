# Infrastructure Upgrade Plan: Phase 2

This plan outlines the remaining rapid infrastructure improvements requested to solidify TalentOps AI's architecture, observability, and performance.

## Proposed Changes

### Frontend: Health Dashboard & Observability
- **[NEW]** `src/pages/admin/HealthDashboard.jsx`: A real-time monitoring dashboard that consumes the newly created `/health/system` API. It will display the status of the Database, Outlook Bridge, and system resources (Disk/Memory) with visual warnings.
- **[MODIFY]** `src/App.jsx`: Add the `/admin/health` route so the dashboard is accessible.

### Frontend: Performance & Lazy Loading
- **[MODIFY]** `src/App.jsx`: Refactor heavy page components (`Campaigns`, `Analytics`, `Directory`, `AdminTerminal`) to use `React.lazy` and `Suspense`.
  - *Why:* This drastically reduces the initial JavaScript bundle size, speeding up the first-paint load time of the application.

### Backend: Analytics Caching Optimization
- **[MODIFY]** `app/routes/analytics.py`: Enhance the custom `SimpleCache` with a more robust decorator-based caching mechanism for expensive database queries (like `get_dashboard_kpis` and `get_data_quality`).
  - *Why:* Prevents the database from being hammered by repetitive heavy analytical queries.

## Verification Plan

### Automated Tests
- None required for this phase.

### Manual Verification
- **Health Dashboard:** Navigate to `/admin/health` in the UI and verify that live system metrics are displaying correctly without errors.
- **Lazy Loading:** Check the browser network tab to ensure chunked JS files are loading on-demand when navigating between routes.
- **Caching:** Hit the analytics endpoints multiple times and verify via the backend logs that the query processing time drops to near-zero for subsequent requests.
