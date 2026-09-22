const fs = require('fs');
const path = require('path');

console.log('='.repeat(65));
console.log('CHECK 2: FRONTEND POLLING THROTTLING & VISIBILITY AUDIT');
console.log('='.repeat(65));

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  [PASS] ${message}`);
    passed++;
  } else {
    console.error(`  [FAIL] ${message}`);
    failed++;
  }
}

// 1. Vercel.json check
const vercelConfig = JSON.parse(fs.readFileSync(path.join(__dirname, 'frontend/vercel.json'), 'utf8'));
const htmlHeaderRule = vercelConfig.headers.find(h => h.source.includes('(?!api/'));
assert(!!htmlHeaderRule, 'vercel.json: HTML cache-control correctly excludes /api/ routes to preserve edge caching');

// 2. main.jsx TanStack Query check
const mainContent = fs.readFileSync(path.join(__dirname, 'frontend/src/main.jsx'), 'utf8');
assert(mainContent.includes('refetchIntervalInBackground: false'), 'main.jsx: refetchIntervalInBackground: false is globally set on QueryClient');

// 3. api.js warmBackend check
const apiContent = fs.readFileSync(path.join(__dirname, 'frontend/src/services/api.js'), 'utf8');
assert(apiContent.includes('if (typeof document !== \'undefined\' && document.hidden) return'), 'api.js: warmBackend guards against document.hidden');
assert(apiContent.includes('9 * 60 * 1000'), 'api.js: warmBackend ping interval increased to 9 minutes');
assert(!apiContent.includes("cache: 'no-store'"), 'api.js: cache: no-store removed so edge/browser can cache pings');

// 4. AnalyticsProvider heartbeat check
const analyticsContent = fs.readFileSync(path.join(__dirname, 'frontend/src/context/AnalyticsProvider.jsx'), 'utf8');
assert(analyticsContent.includes('if (typeof document !== \'undefined\' && document.hidden) return;'), 'AnalyticsProvider: heartbeat guarded by document.hidden');
assert(analyticsContent.includes('60000);'), 'AnalyticsProvider: heartbeat interval relaxed to 60s');

// 5. Component Polling Audit
const pollerAudits = [
  { file: 'frontend/src/components/FleetUpdateCenter.jsx', pattern: /refetchInterval:\s*25000/, bg: true, desc: 'FleetUpdateCenter broadcast' },
  { file: 'frontend/src/components/FleetUpdateCenter.jsx', pattern: /refetchInterval:\s*30000/, bg: true, desc: 'FleetUpdateCenter stats' },
  { file: 'frontend/src/components/ScoutNodesPanel.jsx', pattern: /refetchInterval:\s*25000/, bg: true, desc: 'ScoutNodesPanel telemetry' },
  { file: 'frontend/src/pages/admin/BackgroundJobs.jsx', pattern: /refetchInterval:\s*20000/, bg: true, desc: 'BackgroundJobs queue' },
  { file: 'frontend/src/components/CampaignLogs.jsx', pattern: /refetchInterval:\s*15000/, bg: true, desc: 'CampaignLogs stream' },
  { file: 'frontend/src/components/LiveIngestionPipeline.jsx', pattern: /refetchInterval:\s*25000/, bg: true, desc: 'LiveIngestionPipeline summary' },
  { file: 'frontend/src/components/OperationsConsole.jsx', pattern: /refetchInterval:\s*30000/, bg: true, desc: 'OperationsConsole stats' },
  { file: 'frontend/src/pages/admin/AuditLogs.jsx', pattern: /refetchInterval:\s*30000/, bg: true, desc: 'AuditLogs query' },
  { file: 'frontend/src/pages/ActivityLog.jsx', pattern: /document\.hidden/, desc: 'ActivityLog hidden guard' },
  { file: 'frontend/src/pages/DatabaseIntelligenceCenter.jsx', pattern: /document\.hidden/, desc: 'DatabaseIntelligenceCenter hidden guard' },
  { file: 'frontend/src/pages/MailIntelDashboard.jsx', pattern: /document\.hidden/, desc: 'MailIntelDashboard hidden guard' },
  { file: 'frontend/src/pages/ExtensionHub.jsx', pattern: /document\.hidden/, desc: 'ExtensionHub hidden guard' },
  { file: 'frontend/src/pages/admin/SentinelDashboard.jsx', pattern: /document\.hidden/, desc: 'SentinelDashboard hidden guard' },
  { file: 'frontend/src/components/EnrichmentLiveFeed.jsx', pattern: /document\.hidden/, desc: 'EnrichmentLiveFeed hidden guard' },
  { file: 'frontend/src/components/EnricherControlPanel.jsx', pattern: /document\.hidden/, desc: 'EnricherControlPanel hidden guard' },
  { file: 'frontend/src/components/BridgeStatus.jsx', pattern: /document\.hidden/, desc: 'BridgeStatus hidden guard' },
  { file: 'frontend/src/components/WorkerDashboard.jsx', pattern: /document\.hidden/, desc: 'WorkerDashboard hidden guard' },
  { file: 'frontend/src/components/Sidebar.jsx', pattern: /document\.hidden/, desc: 'Sidebar pending count hidden guard' },
  { file: 'frontend/src/components/NotificationCenter.jsx', pattern: /document\.hidden/, desc: 'NotificationCenter hidden guard' },
];

for (const audit of pollerAudits) {
  const code = fs.readFileSync(path.join(__dirname, audit.file), 'utf8');
  assert(audit.pattern.test(code), `${audit.desc} in ${audit.file}`);
  if (audit.bg) {
    assert(code.includes('refetchIntervalInBackground: false'), `${audit.desc} sets refetchIntervalInBackground: false`);
  }
}

console.log('\n' + '='.repeat(65));
console.log(`CHECK 2 SUMMARY: ${passed} PASSED, ${failed} FAILED`);
console.log('='.repeat(65));

if (failed > 0) {
  process.exit(1);
}
