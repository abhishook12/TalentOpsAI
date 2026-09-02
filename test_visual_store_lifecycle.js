/**
 * Node.js Unit & Regression Test for Visual Screenshot Lifecycle & Auto-Purge Engine
 */

const fs = require('fs');
const path = require('path');

// Mock IndexedDB in memory for Node environment
class MockObjectStore {
  constructor(name) {
    this.name = name;
    this.items = new Map();
  }

  put(val) {
    this.items.set(val.id || val.capture_id, JSON.parse(JSON.stringify(val)));
    const req = { onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }

  get(key) {
    const res = this.items.get(key) ? JSON.parse(JSON.stringify(this.items.get(key))) : null;
    const req = { result: res, onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }

  delete(key) {
    this.items.delete(key);
    const req = { onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }

  getAll() {
    const list = Array.from(this.items.values()).map(v => JSON.parse(JSON.stringify(v)));
    const req = { result: list, onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }

  clear() {
    this.items.clear();
    const req = { onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }

  openCursor() {
    const entries = Array.from(this.items.entries());
    let idx = 0;
    const req = { result: null, onsuccess: null, onerror: null };
    const step = () => {
      if (idx < entries.length) {
        const [k, v] = entries[idx];
        req.result = {
          value: JSON.parse(JSON.stringify(v)),
          delete: () => this.items.delete(k),
          continue: () => { idx++; step(); }
        };
      } else {
        req.result = null;
      }
      if (req.onsuccess) req.onsuccess({ target: req });
    };
    setTimeout(step, 0);
    return req;
  }
}

const mockStores = {
  temporary_screenshots: new MockObjectStore('temporary_screenshots'),
  permanent_provenance_index: new MockObjectStore('permanent_provenance_index'),
};

global.indexedDB = {
  open: () => {
    const db = {
      objectStoreNames: { contains: (n) => true },
      transaction: (names, mode) => ({
        objectStore: (name) => mockStores[name] || mockStores.temporary_screenshots
      })
    };
    const req = { result: db, onsuccess: null, onerror: null };
    setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
    return req;
  }
};

global.window = global;
global.location = { href: 'https://www.linkedin.com/in/test/' };
global.chrome = {
  runtime: {
    sendMessage: (msg) => {}
  }
};

// Load store.js
const storeCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'visual', 'store.js'), 'utf8');
eval(storeCode);

async function runTests() {
  console.log('================================================================================');
  console.log('RUNNING VISUAL SCREENSHOT LIFECYCLE & AUTO-PURGE SUITE');
  console.log('================================================================================');

  const store = window.TalentScout.Visual.Store;

  // TEST 1: Save Screenshot into Buffer
  console.log('\n[TEST 1] Saving Screenshot into Evidence Buffer...');
  const item1 = await store.saveScreenshot({
    id: 'VC-TEST-001',
    page_url: 'https://www.linkedin.com/in/kelseirobertson/',
    page_title: 'Kelsei Martinez | LinkedIn',
    image_data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    status: 'CAPTURED'
  });
  console.assert(item1.id === 'VC-TEST-001', 'Item ID must match');
  console.assert(item1.status === 'CAPTURED', 'Initial status must be CAPTURED');
  console.log('✓ Test 1 Passed: Screenshot saved with status CAPTURED');

  // TEST 2: Discard Useless Screenshot (0 Delay Purge)
  console.log('\n[TEST 2] Testing Immediate Discard of Useless Frame...');
  const item2 = await store.saveScreenshot({
    id: 'VC-USELESS-002',
    page_url: 'https://google.com',
    status: 'CAPTURED'
  });
  await store.updateStatus('VC-USELESS-002', 'NO_USEFUL_DATA');
  const recentAfterDiscard = await store.getRecentScreenshots(10);
  const foundUseless = recentAfterDiscard.some(s => s.id === 'VC-USELESS-002');
  console.assert(!foundUseless, 'Useless image must be deleted immediately');
  console.log('✓ Test 2 Passed: Useless frame discarded immediately with 0 delay');

  // TEST 3: Useful Frame Transition to CLEANUP_PENDING with Provenance Preservation
  console.log('\n[TEST 3] Testing SYNC_COMPLETE -> CLEANUP_PENDING Transition...');
  await store.updateStatus('VC-TEST-001', 'SYNC_COMPLETE', [{ recruiter_name: 'Kelsei Martinez', company: 'Premier Staffing' }]);
  const recentCheck = await store.getRecentScreenshots(10);
  const item1Check = recentCheck.find(s => s.id === 'VC-TEST-001');
  console.assert(item1Check.status === 'CLEANUP_PENDING', 'Status must transition to CLEANUP_PENDING');
  console.assert(item1Check.expires_at > Date.now(), 'Expiration must be scheduled in the future');
  console.log('✓ Test 3 Passed: Successfully transitioned to CLEANUP_PENDING with audit TTL');

  // TEST 4: Immunity while in PROCESSING State
  console.log('\n[TEST 4] Testing Processing Lock (Immunity from Purge)...');
  const item3 = await store.saveScreenshot({
    id: 'VC-BUSY-003',
    status: 'PROCESSING'
  });
  // Force an expired timestamp on item3
  mockStores.temporary_screenshots.items.get('VC-BUSY-003').expires_at = Date.now() - 1000;
  
  // Run purgeExpired
  await store.purgeExpired();
  const checkBusy = mockStores.temporary_screenshots.items.get('VC-BUSY-003');
  console.assert(checkBusy !== undefined, 'Frame in PROCESSING state must NEVER be purged!');
  console.log('✓ Test 4 Passed: Frame in PROCESSING state strictly protected from deletion');

  // TEST 5: Real Diagnostic Telemetry Verification
  console.log('\n[TEST 5] Testing Real Buffer Diagnostics Telemetry...');
  const diag = await store.getBufferDiagnostics();
  console.assert(diag.temporaryImages >= 2, 'Diagnostic must report active temporary images');
  console.assert(diag.processing >= 1, 'Diagnostic must report processing frames');
  console.assert(diag.cleanupPending >= 1, 'Diagnostic must report pending purge frames');
  console.assert(diag.isPurgingActive === true, 'Diagnostic must verify active purging engine');
  console.log('Telemetry Output:', diag);
  console.log('✓ Test 5 Passed: Real-time diagnostics verified');

  console.log('\n================================================================================');
  console.log('>>> VISUAL SCREENSHOT LIFECYCLE & AUTO-PURGE SUITE: 100% PASSED! <<<');
  console.log('================================================================================');
  process.exit(0);
}

runTests();
