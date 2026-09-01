// ============================================================
// background.js — SILENT Service Worker (Full Rewrite)
// - No badge, no notifications to the installer
// - Every contact goes directly to production DB
// - Extension instance is identified by unique device_id
// - Full activity log sent to /recruiters/extension/batch
// ============================================================

const PRODUCTION_API = 'https://talentopsai-1.onrender.com';
const BATCH_ENDPOINT = '/recruiters/extension/batch';
const ACTIVATE_ENDPOINT = '/recruiters/extension/activate';
const REPORT_ENDPOINT = '/recruiters/extension/heartbeat';
const BATCH_SIZE = 25;

// In-memory queue
let contactQueue = [];
let sessionStats = { captured: 0, sent: 0, duplicates: 0, errors: 0 };
let deviceId = null;

// ── Init: generate or load persistent device_id ───────────────
chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get(['device_id']);
  if (!stored.device_id) {
    const id = 'ext-' + crypto.randomUUID();
    await chrome.storage.local.set({ device_id: id });
    deviceId = id;
  } else {
    deviceId = stored.device_id;
  }
});

// Load deviceId on startup
chrome.storage.local.get(['device_id'], (s) => {
  deviceId = s.device_id || 'ext-unknown';
});

// ── Alarms ────────────────────────────────────────────────────
// Send batch every 30 seconds
chrome.alarms.create('sendBatch', { periodInMinutes: 0.5 });
// Send daily heartbeat/report every hour
chrome.alarms.create('heartbeat', { periodInMinutes: 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'sendBatch') flushQueue();
  if (alarm.name === 'heartbeat') sendHeartbeat();
});

// ── Message Handler ───────────────────────────────────────────
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

          // Flush immediately if queue full
          if (contactQueue.length >= BATCH_SIZE) flushQueue();
          sendResponse({ ok: true });
          break;
        }

        // Popup asks for live stats & queue status
        case 'GET_STATS': {
          sendResponse({
            ok: true,
            stats: sessionStats,
            queueLength: contactQueue.length,
          });
          break;
        }

        // Popup forces immediate queue sync
        case 'FLUSH_NOW': {
          const count = await flushQueue();
          sendResponse({ ok: true, sent: count });
          break;
        }

        // Popup asks for auth state
        case 'GET_AUTH': {
          const s = await chrome.storage.sync.get(['authToken', 'activated']);
          sendResponse({ ok: true, authToken: s.authToken, activated: s.activated });
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

// ── Activation ────────────────────────────────────────────────
// User enters an activation code (e.g. "TALENTOPS-XXXXXX")
// We validate it with the backend and get back a JWT scoped to extension_source

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

    return { ok: true };
  } catch (e) {
    return { ok: false, error: 'Cannot reach TalentOps server. Check your connection.' };
  }
}

// ── Flush Queue ───────────────────────────────────────────────

async function flushQueue() {
  if (contactQueue.length === 0) return 0;

  const stored = await chrome.storage.sync.get(['authToken']);
  const token = stored.authToken;
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
      // Token expired — silently clear, user re-activates next time they open popup
      await chrome.storage.sync.remove(['authToken', 'activated']);
      return 0;
    }

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      sessionStats.sent += data.accepted || 0;
      sessionStats.duplicates += data.duplicates || 0;

      // Store last flush info locally (for admin reporting only)
      await chrome.storage.local.set({
        lastFlushAt: new Date().toISOString(),
        lastAccepted: data.accepted || 0,
        totalSent: (await getLocalInt('totalSent')) + (data.accepted || 0),
      });
      return data.accepted || 0;
    } else {
      // Server error — put batch back
      contactQueue.unshift(...batch);
      sessionStats.errors += 1;
      return 0;
    }
  } catch (e) {
    // Network error — put back
    contactQueue.unshift(...batch);
    return 0;
  }
}

// ── Heartbeat (Daily Report to Admin) ─────────────────────────
// Sends a silent status ping every hour so admin can see:
// - This device is alive
// - Session totals
// - OS + browser info

async function sendHeartbeat() {
  const stored = await chrome.storage.sync.get(['authToken']);
  if (!stored.authToken) return;

  const localData = await chrome.storage.local.get(['totalSent', 'device_id']);

  try {
    await fetch(`${PRODUCTION_API}${REPORT_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${stored.authToken}`,
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
  } catch (_) {
    // Silent fail — heartbeat is best-effort
  }
}

// ── Helpers ───────────────────────────────────────────────────

async function getLocalInt(key) {
  const s = await chrome.storage.local.get([key]);
  return parseInt(s[key] || 0, 10);
}
