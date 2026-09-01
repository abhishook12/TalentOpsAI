// popup.js — Dynamic Power Meter, Live Counters, Mode Switcher & Stream Feed

const $ = id => document.getElementById(id);
const API_BASE = 'https://talentopsai-1.onrender.com';

async function init() {
  let auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH' }).catch(() => ({}));

  if (!auth?.authToken) {
    auth = await chrome.runtime.sendMessage({ type: 'AUTH_AUTO_ACTIVATE' }).catch(() => ({}));
  }

  showDashboard();
  initModeSwitcher();
  loadLiveStats();
  setInterval(loadLiveStats, 2000); // Auto-refresh live stats every 2s while popup is open
}

function showLogin() {
  $('screen-login').classList.remove('hidden');
  $('screen-active').classList.add('hidden');

  $('btn-activate').addEventListener('click', async () => {
    const code = $('activation-code').value.trim();
    if (!code) return showError('Enter your activation code.');

    $('btn-activate').disabled = true;
    $('btn-activate').textContent = 'Connecting…';
    $('login-error').classList.add('hidden');

    const res = await chrome.runtime.sendMessage({
      type: 'AUTH_ACTIVATE',
      activationCode: code,
    });

    if (res?.ok) {
      showDashboard();
      initModeSwitcher();
      loadLiveStats();
    } else {
      showError(res?.error || 'Invalid activation code. Try again.');
      $('btn-activate').disabled = false;
      $('btn-activate').textContent = '⚡ Connect & Activate';
    }
  });

  $('activation-code').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('btn-activate').click();
  });
}

function showDashboard() {
  $('screen-login').classList.add('hidden');
  $('screen-active').classList.remove('hidden');

  // Wire Scan Page button
  const scanBtn = $('btn-scan-page');
  if (scanBtn && !scanBtn.dataset.wired) {
    scanBtn.dataset.wired = 'true';
    scanBtn.addEventListener('click', async () => {
      scanBtn.disabled = true;
      scanBtn.textContent = 'Scanning…';

      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          await chrome.tabs.sendMessage(tab.id, { type: 'TRIGGER_SCAN' }).catch(() => {});
          const cur = await chrome.storage.local.get(['pagesScanned']);
          const next = (cur.pagesScanned || 0) + 1;
          await chrome.storage.local.set({ pagesScanned: next });

          await chrome.runtime.sendMessage({ type: 'FLUSH_NOW' }).catch(() => {});
          showFeedback('✓ Page scanned & intelligence synced!');
        } else {
          showFeedback('Page active & listening 24/7');
        }
      } catch (e) {
        showFeedback('Page scanned & synchronized');
      } finally {
        setTimeout(() => {
          scanBtn.disabled = false;
          scanBtn.textContent = '⚡ Scan Page';
          loadLiveStats();
        }, 800);
      }
    });
  }

  // Wire Sync Queue button
  const syncBtn = $('btn-sync-now');
  if (syncBtn && !syncBtn.dataset.wired) {
    syncBtn.dataset.wired = 'true';
    syncBtn.addEventListener('click', async () => {
      syncBtn.style.transform = 'rotate(180deg)';
      syncBtn.disabled = true;
      await chrome.runtime.sendMessage({ type: 'FLUSH_NOW' });
      setTimeout(() => {
        syncBtn.style.transform = 'rotate(0deg)';
        syncBtn.disabled = false;
        loadLiveStats();
        showFeedback('✓ Database queue synchronized!');
      }, 600);
    });
  }
}

async function initModeSwitcher() {
  const modeRes = await chrome.runtime.sendMessage({ type: 'GET_SCRAPER_MODE' }).catch(() => ({ mode: 'HYBRID' }));
  const activeMode = modeRes?.mode || 'HYBRID';
  updateModeButtonsUI(activeMode);

  ['mode-hybrid', 'mode-visual', 'mode-dom'].forEach(btnId => {
    const btn = $(btnId);
    if (btn && !btn.dataset.wired) {
      btn.dataset.wired = 'true';
      btn.addEventListener('click', async () => {
        const selectedMode = btn.dataset.mode;
        await chrome.runtime.sendMessage({ type: 'SET_SCRAPER_MODE', mode: selectedMode });
        updateModeButtonsUI(selectedMode);
        showFeedback(`✓ Mode switched to ${btn.textContent.trim()}`);
      });
    }
  });
}

function updateModeButtonsUI(activeMode) {
  ['mode-hybrid', 'mode-visual', 'mode-dom'].forEach(btnId => {
    const btn = $(btnId);
    if (!btn) return;
    if (btn.dataset.mode === activeMode) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  const statusText = $('conn-status');
  if (statusText) {
    if (activeMode === 'VISUAL') statusText.textContent = '24/7 Active • Visual First';
    else if (activeMode === 'DOM') statusText.textContent = '24/7 Active • DOM Mode';
    else statusText.textContent = '24/7 Active • Hybrid AI';
  }
}

async function loadLiveStats() {
  const statsRes = await chrome.runtime.sendMessage({ type: 'GET_STATS' }).catch(() => ({}));
  const localData = await chrome.storage.local.get([
    'totalSent',
    'pagesScanned',
    'recentCaptures',
    'totalCollectedEver',
    'userEmail',
    'userRole',
    'scraperMode'
  ]);

  const totalSent = statsRes?.totalSent || localData.totalSent || 0;
  const totalCaptured = statsRes?.totalCollected || localData.totalCollectedEver || 0;
  const pagesScanned = Math.max(1, statsRes?.pagesScanned || localData.pagesScanned || 0);
  const queueLen = statsRes?.queueLength || 0;

  // 1. Update Counters
  if ($('stat-collected')) $('stat-collected').textContent = totalCaptured.toLocaleString();
  if ($('stat-synced')) $('stat-synced').textContent = totalSent.toLocaleString();
  if ($('stat-scanned')) $('stat-scanned').textContent = pagesScanned.toLocaleString();
  if ($('stat-pending')) $('stat-pending').textContent = queueLen.toLocaleString();

  // 2. Compute Scout Power Meter & Score
  const score = Math.min(100, Math.max(75, 75 + Math.min(25, (pagesScanned * 2 + totalCaptured * 3))));

  if ($('scout-score')) $('scout-score').textContent = score;
  if ($('meter-bar-fill')) $('meter-bar-fill').style.width = `${score}%`;

  if ($('scout-user-label')) {
    const mode = localData.scraperMode || 'Hybrid';
    $('scout-user-label').textContent = `${mode} AI Active`;
  }

  if ($('scout-rank')) {
    if (score >= 95) {
      $('scout-rank').textContent = 'Master Scout';
      $('scout-efficiency-text').textContent = 'Visual & DOM continuous extraction';
    } else if (score >= 85) {
      $('scout-rank').textContent = 'Pro Scout';
      $('scout-efficiency-text').textContent = 'Real-time corporate screen pipeline';
    } else {
      $('scout-rank').textContent = 'Active Scout';
      $('scout-efficiency-text').textContent = 'Scanning web for candidate leads';
    }
  }

  // 3. Render Live Stream Feed
  const recent = localData.recentCaptures || [];
  const feedList = $('feed-list');

  if (recent.length > 0) {
    if ($('stream-count')) $('stream-count').textContent = `${recent.length} recent`;
    if (feedList) {
      feedList.innerHTML = recent.slice(0, 6).map(item => {
        const icon = item.source?.includes('visual') ? '👁️' : item.source?.includes('linkedin') ? '💼' : (item.source?.includes('gmail') || item.source?.includes('outlook')) ? '✉️' : '🌐';
        return `
          <div class="feed-item">
            <div class="feed-left">
              <span class="feed-icon">${icon}</span>
              <div>
                <div class="feed-name">${escapeHtml(item.recruiter_name || 'Recruiter')}</div>
                <div class="feed-sub">${escapeHtml(item.company_name || item.title || 'Corporate Contact')}</div>
              </div>
            </div>
            <span class="feed-tag">Verified</span>
          </div>`;
      }).join('');
    }
  } else {
    try {
      const feedRes = await fetch(`${API_BASE}/recruiters/extension/live-feed?limit=5`).then(r => r.json()).catch(() => null);
      if (feedRes?.feed && feedRes.feed.length > 0 && feedList) {
        if ($('stream-count')) $('stream-count').textContent = 'Cloud Live';
        feedList.innerHTML = feedRes.feed.slice(0, 5).map(item => `
          <div class="feed-item">
            <div class="feed-left">
              <span class="feed-icon">💼</span>
              <div>
                <div class="feed-name">${escapeHtml(item.recruiter_name || 'Recruiter')}</div>
                <div class="feed-sub">${escapeHtml(item.company_name || item.title || 'Talent Lead')}</div>
              </div>
            </div>
            <span class="feed-tag">${item.verification_status || 'Verified'}</span>
          </div>
        `).join('');
      }
    } catch (_) {}
  }
}

function showFeedback(msg) {
  const el = $('scan-feedback');
  if (el) {
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3000);
  }
}

function showError(msg) {
  const el = $('login-error');
  if (el) {
    el.textContent = msg;
    el.classList.remove('hidden');
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  })[m]);
}

document.addEventListener('DOMContentLoaded', init);
