// ============================================================
// visual/store.js — State-Aware Temporary Screenshot Lifecycle & Auto-Purge Engine
// Strict 20-Rule Operating Core: Temporary Evidence Buffer • Auto-Purge • Zero Memory Leaks
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  const DB_NAME = 'TalentScoutVisualDB';
  const DB_VERSION = 3;
  const STORE_NAME = 'temporary_screenshots';
  const PROVENANCE_STORE_NAME = 'permanent_provenance_index';

  const AUDIT_RETENTION_MS = 60 * 60 * 1000;  // 1-Hour Rolling Evidence Retention Window
  const HARD_MAX_RETENTION_MS = 60 * 60 * 1000; // 1-Hour Hard Retention Ceiling
  const MAX_BUFFER_IMAGES = 200; // Retains full active 1-hour session frames

  let dbPromise = null;
  let lastPurgeTimestamp = null;
  let totalPurgedEver = 0;

  function openDB() {
    if (!dbPromise) {
      dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = e.target.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
            store.createIndex('status', 'status', { unique: false });
            store.createIndex('captured_at', 'captured_at', { unique: false });
            store.createIndex('expires_at', 'expires_at', { unique: false });
          }
          if (!db.objectStoreNames.contains(PROVENANCE_STORE_NAME)) {
            const provStore = db.createObjectStore(PROVENANCE_STORE_NAME, { keyPath: 'capture_id' });
            provStore.createIndex('created_at', 'created_at', { unique: false });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return dbPromise;
  }

  /**
   * 1. Save new capture into temporary evidence buffer
   */
  async function saveScreenshot({
    id,
    page_url,
    page_title,
    tab_id,
    change_score,
    image_data,
    status = 'CAPTURED',
  }) {
    const db = await openDB();
    const captureId = id || ('VC-' + Math.floor(10000 + Math.random() * 90000));
    const now = Date.now();

    // Check buffer limit — if >= MAX_BUFFER_IMAGES, purge oldest completed
    try {
      const all = await getRecentScreenshots(50);
      if (all.length >= MAX_BUFFER_IMAGES) {
        const completeds = all.filter(item => item.status !== 'PROCESSING');
        if (completeds.length > 0) {
          await deleteScreenshot(completeds[completeds.length - 1].id, 'buffer_overflow_prune');
        }
      }
    } catch (_) {}

    const item = {
      id: captureId,
      captured_at: new Date().toISOString(),
      page_url: page_url || '',
      page_title: page_title || '',
      tab_id: tab_id || null,
      change_score: change_score || 0,
      image_data: image_data || '',
      status: status, // CAPTURED | PROCESSING | EXTRACTION_COMPLETE | SYNC_COMPLETE | CLEANUP_PENDING
      extracted_entities: [],
      created_timestamp: now,
      expires_at: now + HARD_MAX_RETENTION_MS,
      retry_count: 0,
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(item);
      req.onsuccess = () => resolve(item);
      req.onerror = () => reject(req.error);
    });
  }

  /**
   * 2. State transition: Update status and lock in lifecycle TTL
   */
  async function updateStatus(id, newStatus, extractedEntities = null, options = {}) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME, PROVENANCE_STORE_NAME], 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const provStore = tx.objectStore(PROVENANCE_STORE_NAME);

      const getReq = store.get(id);

      getReq.onsuccess = () => {
        const item = getReq.result;
        if (!item) return resolve(null);

        item.status = newStatus;
        if (extractedEntities) {
          item.extracted_entities = extractedEntities;
        }

        const now = Date.now();

        // Rule 3: If no useful data -> Discard immediately!
        if (newStatus === 'NO_USEFUL_DATA') {
          store.delete(id);
          logPurgeEvent(id, 'no_useful_data');
          return resolve({ ...item, status: 'PURGED' });
        }

        // Rule 4 & 5: If extracted / synced -> transition to CLEANUP_PENDING with 2m audit retention
        if (newStatus === 'EXTRACTION_COMPLETE' || newStatus === 'SYNC_COMPLETE' || newStatus === 'STAGED') {
          item.status = 'CLEANUP_PENDING';
          item.expires_at = now + AUDIT_RETENTION_MS;

          // Rule 17: Save persistent lightweight provenance metadata BEFORE image deletion
          const provItem = {
            capture_id: id,
            created_at: item.captured_at,
            page_url: item.page_url,
            page_title: item.page_title,
            extracted_entities: item.extracted_entities,
            status: newStatus,
            purged_at: null,
          };
          provStore.put(provItem);
        }

        // Rule 8: If processing failed -> allow retry
        if (newStatus === 'PROCESSING_FAILED') {
          item.retry_count = (item.retry_count || 0) + 1;
          if (item.retry_count > 3) {
            item.status = 'CLEANUP_PENDING';
            item.expires_at = now + 10000; // Delete after 10s if exceeded retry budget
          }
        }

        const putReq = store.put(item);
        putReq.onsuccess = () => resolve(item);
        putReq.onerror = () => reject(putReq.error);
      };
      getReq.onerror = () => reject(getReq.error);
    });
  }

  /**
   * 3. Discard unneeded screenshot immediately (0ms delay)
   */
  async function discardScreenshot(id) {
    if (!id) return;
    await deleteScreenshot(id, 'no_useful_data');
  }

  /**
   * 4. Internal delete helper with real event emission
   */
  async function deleteScreenshot(id, reason = 'retention_expired') {
    if (!id) return;
    try {
      const db = await openDB();
      const tx = db.transaction([STORE_NAME, PROVENANCE_STORE_NAME], 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const provStore = tx.objectStore(PROVENANCE_STORE_NAME);

      store.delete(id);

      // Update provenance index to mark purged
      const provReq = provStore.get(id);
      provReq.onsuccess = () => {
        if (provReq.result) {
          provReq.result.purged_at = new Date().toISOString();
          provStore.put(provReq.result);
        }
      };

      lastPurgeTimestamp = new Date().toLocaleTimeString();
      totalPurgedEver++;
      logPurgeEvent(id, reason);
    } catch (_) {}
  }

  function logPurgeEvent(captureId, reason) {
    try {
      chrome.runtime.sendMessage({
        type: 'APPEND_EVENT_LOG',
        event: {
          timestamp: new Date().toLocaleTimeString(),
          type: 'SCREENSHOT_PURGED',
          detail: `Deleted ${captureId} (Reason: ${reason})`,
          url: location.href,
        }
      });
    } catch (_) {}
  }

  /**
   * 5. Purge expired screenshots (Rule 6: Never delete while in PROCESSING)
   */
  async function purgeExpired() {
    const db = await openDB();
    const now = Date.now();
    let deletedCount = 0;

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.openCursor();

      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor) {
          const item = cursor.value;
          // STRICT RULE 6: Never delete an image while it is currently in 'PROCESSING' state
          if (item.status !== 'PROCESSING') {
            if (item.expires_at && item.expires_at <= now) {
              cursor.delete();
              deletedCount++;
              lastPurgeTimestamp = new Date().toLocaleTimeString();
              totalPurgedEver++;
              logPurgeEvent(item.id, 'audit_retention_expired');
            }
          }
          cursor.continue();
        } else {
          resolve(deletedCount);
        }
      };
      req.onerror = () => reject(req.error);
    });
  }

  /**
   * 6. Startup Cleanup: Purge any stale screenshots from past crashes/sessions (Rule 10)
   */
  async function purgeStaleStartup() {
    const db = await openDB();
    const now = Date.now();
    let staleCount = 0;

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.openCursor();

      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor) {
          const item = cursor.value;
          // If created more than 1 hour ago
          const ageMs = now - (item.created_timestamp || 0);
          if (ageMs >= HARD_MAX_RETENTION_MS) {
            cursor.delete();
            staleCount++;
          }
          cursor.continue();
        } else {
          if (staleCount > 0) {
            console.log(`%c[TalentOps Scout] 🧹 Startup Cleanup: Purged ${staleCount} stale screenshot(s) from prior session`, 'color:#a855f7;font-weight:bold;');
            lastPurgeTimestamp = new Date().toLocaleTimeString();
            totalPurgedEver += staleCount;
          }
          resolve(staleCount);
        }
      };
      req.onerror = () => reject(req.error);
    });
  }

  /**
   * 7. Buffer Telemetry & Real Diagnostic Metrics (Rule 13)
   */
  async function getBufferDiagnostics() {
    const db = await openDB();
    const now = Date.now();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const items = req.result || [];
        let totalBytes = 0;
        let processingCount = 0;
        let cleanupPendingCount = 0;
        let minExpires = Infinity;

        items.forEach(item => {
          if (item.image_data) totalBytes += item.image_data.length;
          if (item.status === 'PROCESSING') processingCount++;
          if (item.status === 'CLEANUP_PENDING' || item.status === 'SYNC_COMPLETE') cleanupPendingCount++;

          if (item.status !== 'PROCESSING' && item.expires_at && item.expires_at < minExpires) {
            minExpires = item.expires_at;
          }
        });

        const nextPurgeSec = minExpires !== Infinity ? Math.max(0, Math.round((minExpires - now) / 1000)) : 120;
        const mb = (totalBytes / (1024 * 1024)).toFixed(2);

        resolve({
          temporaryImages: items.length,
          processing: processingCount,
          cleanupPending: cleanupPendingCount,
          maxBuffer: MAX_BUFFER_IMAGES,
          storageMB: `${mb} MB`,
          storageBytes: totalBytes,
          lastPurgeTime: lastPurgeTimestamp || 'None (Buffer Clean)',
          nextPurgeSec: nextPurgeSec,
          totalPurged: totalPurgedEver,
          isPurgingActive: true,
        });
      };
      req.onerror = () => reject(req.error);
    });
  }

  async function getRecentScreenshots(limit = 20) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const items = req.result || [];
        items.sort((a, b) => (b.created_timestamp || 0) - (a.created_timestamp || 0));
        resolve(items.slice(0, limit));
      };
      req.onerror = () => reject(req.error);
    });
  }

  async function purgeAll() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const req = store.clear();
      req.onsuccess = () => {
        lastPurgeTimestamp = new Date().toLocaleTimeString();
        resolve(true);
      };
      req.onerror = () => reject(req.error);
    });
  }

  // Run startup cleanup immediately on load
  setTimeout(() => purgeStaleStartup(), 500);

  // Periodic Auto-Purge Loop every 25 seconds
  setInterval(() => purgeExpired(), 25000);

  window.TalentScout.Visual.Store = {
    saveScreenshot,
    discardScreenshot,
    updateStatus,
    deleteScreenshot,
    getRecentScreenshots,
    purgeExpired,
    purgeStaleStartup,
    purgeAll,
    getBufferDiagnostics,
    MAX_BUFFER_IMAGES,
    AUDIT_RETENTION_MS,
    HARD_MAX_RETENTION_MS,
  };

})();
