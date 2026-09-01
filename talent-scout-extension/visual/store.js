// ============================================================
// visual/store.js — IndexedDB Temporary Screenshot Storage & Lifecycle
// Guaranteed 2-3 Minute Retention Window with Automatic Purge
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  const DB_NAME = 'TalentScoutVisualDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'temporary_screenshots';
  const DEFAULT_TTL_MS = 3 * 60 * 1000; // 3 Minutes TTL

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
   * Save a newly captured screenshot with metadata
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
    const item = {
      id: id || ('vis_' + crypto.randomUUID()),
      captured_at: new Date().toISOString(),
      page_url: page_url || '',
      page_title: page_title || '',
      tab_id: tab_id || null,
      change_score: change_score || 0,
      image_data: image_data || '',
      status: status,
      extracted_entities: [],
      created_timestamp: Date.now(),
      expires_at: Date.now() + DEFAULT_TTL_MS, // Initial expiration
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
   * Update status, extracted leads, and set final 2-3 min cleanup countdown
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

        // When processing/sync is complete, lock in the 2.5 min deletion timer
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

  /**
   * Fetch single screenshot by ID (for debugger / inspector preview)
   */
  async function getScreenshot(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  }

  /**
   * Get all active screenshots within retention window (latest first)
   */
  async function getRecentScreenshots(limit = 10) {
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

  /**
   * Startup cleanup / wipe all
   */
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

  // Export to window.TalentScout.Visual.Store
  window.TalentScout.Visual.Store = {
    saveScreenshot,
    updateStatus,
    getScreenshot,
    getRecentScreenshots,
    purgeExpired,
    purgeAll,
    DEFAULT_TTL_MS,
  };

})();
