// ============================================================
// visual/store.js — IndexedDB Temporary Processing Buffer & Strict Lifecycle
// Algorithms 24, 25, 26: Temporary Buffer Queue, MAX_BUFFER limit, 2-3m Auto-Purge
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  const DB_NAME = 'TalentScoutVisualDB';
  const DB_VERSION = 2;
  const STORE_NAME = 'temporary_screenshots';
  const DEFAULT_TTL_MS = 2.5 * 60 * 1000; // 2.5 Minutes Processing TTL
  const MAX_BUFFER_SIZE = 15; // Algorithm 26: Hard ceiling on buffered frames

  let dbPromise = null;

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
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }
    return dbPromise;
  }

  /**
   * Save screenshot into temporary processing buffer (enforcing MAX_BUFFER_SIZE)
   */
  async function saveScreenshot({
    id,
    page_url,
    page_title,
    tab_id,
    change_score,
    image_data,
    status = 'PROCESSING',
  }) {
    const db = await openDB();

    // Check buffer size and prune oldest if exceeding limit
    try {
      const all = await getRecentScreenshots(50);
      if (all.length >= MAX_BUFFER_SIZE) {
        const toDelete = all.slice(MAX_BUFFER_SIZE - 1);
        const txDel = db.transaction(STORE_NAME, 'readwrite');
        const stDel = txDel.objectStore(STORE_NAME);
        toDelete.forEach(item => stDel.delete(item.id));
      }
    } catch (_) {}

    const item = {
      id: id || ('VC-' + Math.floor(10000 + Math.random() * 90000)),
      captured_at: new Date().toISOString(),
      page_url: page_url || '',
      page_title: page_title || '',
      tab_id: tab_id || null,
      change_score: change_score || 0,
      image_data: image_data || '',
      status: status,
      extracted_entities: [],
      created_timestamp: Date.now(),
      expires_at: Date.now() + DEFAULT_TTL_MS,
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
   * Discard non-useful frames immediately (Algorithm 24)
   */
  async function discardScreenshot(id) {
    if (!id) return;
    try {
      const db = await openDB();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).delete(id);
    } catch (_) {}
  }

  /**
   * Update status & lock in cleanup expiration
   */
  async function updateStatus(id, newStatus, extractedEntities = null) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const getReq = store.get(id);

      getReq.onsuccess = () => {
        const item = getReq.result;
        if (!item) return resolve(null);

        item.status = newStatus;
        if (extractedEntities) {
          item.extracted_entities = extractedEntities;
        }

        if (newStatus === 'SYNC_COMPLETE' || newStatus === 'EXTRACTED') {
          item.expires_at = Date.now() + (2.5 * 60 * 1000);
        }

        const putReq = store.put(item);
        putReq.onsuccess = () => resolve(item);
        putReq.onerror = () => reject(putReq.error);
      };
      getReq.onerror = () => reject(getReq.error);
    });
  }

  async function getRecentScreenshots(limit = 15) {
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

  /**
   * Purge all expired screenshots beyond TTL
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
          if (item.expires_at && item.expires_at <= now) {
            cursor.delete();
            deletedCount++;
          }
          cursor.continue();
        } else {
          resolve(deletedCount);
        }
      };
      req.onerror = () => reject(req.error);
    });
  }

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
        let minExpires = Infinity;

        items.forEach(item => {
          if (item.image_data) totalBytes += item.image_data.length;
          if (item.expires_at && item.expires_at < minExpires) {
            minExpires = item.expires_at;
          }
        });

        const nextPurgeSec = minExpires !== Infinity ? Math.max(0, Math.round((minExpires - now) / 1000)) : 150;
        const mb = (totalBytes / (1024 * 1024)).toFixed(2);

        resolve({
          capturedCount: items.length,
          maxBuffer: MAX_BUFFER_SIZE,
          storageMB: `${mb} MB`,
          storageBytes: totalBytes,
          nextPurgeSec: nextPurgeSec,
        });
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
      req.onsuccess = () => resolve(true);
      req.onerror = () => reject(req.error);
    });
  }

  window.TalentScout.Visual.Store = {
    saveScreenshot,
    discardScreenshot,
    updateStatus,
    getRecentScreenshots,
    purgeExpired,
    purgeAll,
    getBufferDiagnostics,
    MAX_BUFFER_SIZE,
    DEFAULT_TTL_MS,
  };

})();
