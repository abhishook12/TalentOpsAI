// ============================================================
// background.js — High-Speed Service Worker Engine
// Continuous Background Listener + Instant Tab Navigation Tracker
// ============================================================

const PRODUCTION_API = 'https://talentopsai-1.onrender.com';
const BATCH_ENDPOINT = '/recruiters/extension/batch';
const ACTIVATE_ENDPOINT = '/recruiters/extension/activate';
const REPORT_ENDPOINT = '/recruiters/extension/heartbeat';
const BATCH_SIZE = 25;

// In-memory queue & fast flush timer
let contactQueue = [];
let sessionStats = { captured: 0, sent: 0, duplicates: 0, errors: 0 };
let deviceId = null;
let fastFlushTimer = null;

// ── 1. Init: Generate or Load Persistent Device ID ────────────
chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get(['device_id']);
  if (!stored.device_id) {
    const id = 'ext-' + crypto.randomUUID();
    await chrome.storage.local.set({ device_id: id });
    deviceId = id;
  } else {
    deviceId = stored.device_id;
  }

  // Retroactively inject into all open tabs
  try {
    const tabs = await chrome.tabs.query({ url: ['http://*/*', 'https://*/*'] });
    for (const tab of tabs) {
      chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        files: [
          'detector/patterns.js',
          'detector/linkedin.js',
          'detector/email.js',
          'detector/indeed.js',
          'detector/glassdoor.js',
          'detector/ziprecruiter.js',
          'detector/generic.js',
          'content.js'
        ]
      }).catch(() => {});
    }
  } catch (_) {}
});

// Load deviceId on startup
chrome.storage.local.get(['device_id'], (s) => {
  deviceId = s.device_id || 'ext-unknown';
});

// ── 2. Real-Time Tab Navigation & Pages Read Tracker ──────────
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab?.url && tab.url.startsWith('http')) {
    // Increment global pages scanned count in local storage
    const local = await chrome.storage.local.get(['pagesScanned']);
    const nextCount = (local.pagesScanned || 0) + 1;
    await chrome.storage.local.set({ pagesScanned: nextCount });

    // Ping content script to run scan on newly completed page
    try {
      chrome.tabs.sendMessage(tabId, { type: 'TRIGGER_SCAN' }).catch(() => {});
    } catch (_) {}
  }
});

// ── 3. Periodic Alarms (Fallback flush & Hourly Heartbeat) ────
chrome.alarms.create('sendBatch', { periodInMinutes: 0.5 });
chrome.alarms.create('heartbeat', { periodInMinutes: 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'sendBatch') flushQueue();
  if (alarm.name === 'heartbeat') sendHeartbeat();
});

// ── 4. Message Handler ─────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      switch (msg.type) {

        // Content script submits captured contacts
        case 'QUEUE_CONTACTS': {
          const contacts = (msg.contacts || []).map(c => ({
            ...c,
            device_id: deviceId,
            tab_url: sender.tab?.url || null,
          }));
          contactQueue.push(...contacts);
          sessionStats.captured += contacts.length;

          // Save recent captures and cumulative total in local storage
          const local = await chrome.storage.local.get(['recentCaptures', 'totalCollectedEver']);
          const existingRecent = local.recentCaptures || [];
          const updatedRecent = [...contacts.slice(0, 5), ...existingRecent].slice(0, 15);
          const totalEver = (local.totalCollectedEver || 0) + contacts.length;
          await chrome.storage.local.set({
            recentCaptures: updatedRecent,
            totalCollectedEver: totalEver,
          });

          // High-Speed Real-Time Sync: Flush queue in 1.2s or immediately if >= 10 items
          if (contactQueue.length >= 10) {
            flushQueue();
          } else {
            clearTimeout(fastFlushTimer);
            fastFlushTimer = setTimeout(() => flushQueue(), 1200);
          }
          sendResponse({ ok: true });
          break;
        }

        // Popup asks for live stats & queue status
        case 'GET_STATS': {
          const local = await chrome.storage.local.get(['pagesScanned', 'totalSent', 'totalCollectedEver']);
          sendResponse({
            ok: true,
            stats: sessionStats,
            queueLength: contactQueue.length,
            pagesScanned: local.pagesScanned || 0,
            totalSent: (local.totalSent || 0) + sessionStats.sent,
            totalCollected: (local.totalCollectedEver || 0) + sessionStats.captured,
          });
          break;
        }

        // Popup forces immediate queue sync
        case 'FLUSH_NOW': {
          const count = await flushQueue();
          sendResponse({ ok: true, sent: count });
          break;
        }

        // Popup asks for auth state (checks both local and sync)
        case 'GET_AUTH': {
          const l = await chrome.storage.local.get(['authToken', 'activated']);
          const s = await chrome.storage.sync.get(['authToken', 'activated']);
          const authToken = l.authToken || s.authToken || null;
          const activated = l.activated || s.activated || false;
          sendResponse({ ok: true, authToken, activated });
          break;
        }

        // Popup submits activation code
        case 'AUTH_ACTIVATE': {
          const result = await activateExtension(msg.activationCode);
          sendResponse(result);
          break;
        }

        // Popup logs out
        case 'AUTH_LOGOUT': {
          await chrome.storage.sync.clear();
          await chrome.storage.local.remove(['authToken', 'activated']);
          contactQueue = [];
          sessionStats = { captured: 0, sent: 0, duplicates: 0, errors: 0 };
          sendResponse({ ok: true });
          break;
        }

        default:
          sendResponse({ ok: false, error: 'Unknown message' });
      }
    } catch (e) {
      sendResponse({ ok: false, error: e.message });
    }
  })();
  return true;
});

// ── 5. Activation ──────────────────────────────────────────────

async function activateExtension(code) {
  const local = await chrome.storage.local.get(['device_id']);
  const devId = local.device_id || deviceId;

  try {
    const res = await fetch(`${PRODUCTION_API}${ACTIVATE_ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        activation_code: code,
        device_id: devId,
        user_agent: navigator.userAgent,
      }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      return { ok: false, error: data?.detail || `Invalid code (${res.status})` };
    }

    const token = data.access_token || data.token;
    await chrome.storage.sync.set({
      authToken: token,
      activated: true,
      activatedAt: new Date().toISOString(),
    });
    await chrome.storage.local.set({
      authToken: token,
      activated: true,
    });

    return { ok: true };
  } catch (e) {
    return { ok: false, error: 'Cannot reach TalentOps server. Check your connection.' };
  }
}

// ── 6. Flush Queue to Database ────────────────────────────────

async function flushQueue() {
  if (contactQueue.length === 0) return 0;

  const l = await chrome.storage.local.get(['authToken']);
  const s = await chrome.storage.sync.get(['authToken']);
  const token = l.authToken || s.authToken;
  if (!token) return 0;

  const batch = contactQueue.splice(0, BATCH_SIZE);

  try {
    const res = await fetch(`${PRODUCTION_API}${BATCH_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Device-ID': deviceId || 'unknown',
        'X-Extension-Version': chrome.runtime.getManifest().version,
      },
      body: JSON.stringify({
        contacts: batch,
        device_id: deviceId,
        session_stats: sessionStats,
      }),
    });

    if (res.status === 401) {
      await chrome.storage.sync.remove(['authToken', 'activated']);
      await chrome.storage.local.remove(['authToken', 'activated']);
      return 0;
    }

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      sessionStats.sent += data.accepted || 0;
      sessionStats.duplicates += data.duplicates || 0;

      const cur = await chrome.storage.local.get(['totalSent']);
      await chrome.storage.local.set({
        lastFlushAt: new Date().toISOString(),
        lastAccepted: data.accepted || 0,
        totalSent: (cur.totalSent || 0) + (data.accepted || 0),
      });
      return data.accepted || 0;
    } else {
      contactQueue.unshift(...batch);
      sessionStats.errors += 1;
      return 0;
    }
  } catch (e) {
    contactQueue.unshift(...batch);
    return 0;
  }
}

// ── 7. Heartbeat Telemetry ────────────────────────────────────

async function sendHeartbeat() {
  const l = await chrome.storage.local.get(['authToken']);
  const s = await chrome.storage.sync.get(['authToken']);
  const token = l.authToken || s.authToken;
  if (!token) return;

  const localData = await chrome.storage.local.get(['totalSent', 'device_id']);

  try {
    await fetch(`${PRODUCTION_API}${REPORT_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Device-ID': deviceId,
      },
      body: JSON.stringify({
        device_id: deviceId,
        session_captured: sessionStats.captured,
        session_sent: sessionStats.sent,
        session_duplicates: sessionStats.duplicates,
        total_ever_sent: localData.totalSent || 0,
        queue_pending: contactQueue.length,
        extension_version: chrome.runtime.getManifest().version,
        timestamp: new Date().toISOString(),
      }),
    });
  } catch (_) {}
}
