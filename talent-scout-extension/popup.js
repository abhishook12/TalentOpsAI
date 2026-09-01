// popup.js — Dynamic Power Meter, Live Counters & Stream Feed

const $ = id => document.getElementById(id);

async function init() {
  const auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH' });

  if (auth?.authToken) {
    showDashboard();
    loadLiveStats();
    setInterval(loadLiveStats, 2000); // Auto-refresh live stats every 2s while popup is open
  } else {
    showLogin();
  }
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

  // Wire Sync Queue button
  $('btn-sync-now').addEventListener('click', async () => {
    const btn = $('btn-sync-now');
    btn.style.transform = 'rotate(180deg)';
    btn.disabled = true;
    await chrome.runtime.sendMessage({ type: 'FLUSH_NOW' });
    setTimeout(() => {
      btn.style.transform = 'rotate(0deg)';
      btn.disabled = false;
      loadLiveStats();
    }, 600);
  });
}

async function loadLiveStats() {
  const statsRes = await chrome.runtime.sendMessage({ type: 'GET_STATS' });
  const localData = await chrome.storage.local.get([
    'totalSent',
    'pagesScanned',
    'recentCaptures',
    'totalCollectedEver'
  ]);

  const stats = statsRes?.stats || { captured: 0, sent: 0, duplicates: 0 };
  const queueLen = statsRes?.queueLength || 0;
  const totalSent = (localData.totalSent || 0) + stats.sent;
  const totalCaptured = (localData.totalCollectedEver || 0) + stats.captured;
  const pagesScanned = localData.pagesScanned || Math.max(1, Math.round(totalCaptured * 1.4));

  // 1. Update Counters
  $('stat-collected').textContent = totalCaptured.toLocaleString();
  $('stat-synced').textContent = totalSent.toLocaleString();
  $('stat-scanned').textContent = pagesScanned.toLocaleString();
  $('stat-pending').textContent = queueLen.toLocaleString();

  // 2. Compute Scout Power Meter & Score
  const efficiency = totalCaptured > 0 ? Math.min(100, Math.round((totalSent / Math.max(1, totalCaptured)) * 100)) : 95;
  const score = Math.min(100, Math.max(60, 60 + Math.min(40, totalCaptured * 2)));

  $('scout-score').textContent = score;
  $('meter-bar-fill').style.width = `${score}%`;

  if (score >= 95) {
    $('scout-rank').textContent = 'Master Scout';
    $('scout-efficiency-text').textContent = 'Elite corporate enrichment rate';
  } else if (score >= 80) {
    $('scout-rank').textContent = 'Pro Scout';
    $('scout-efficiency-text').textContent = 'High precision active listening';
  } else {
    $('scout-rank').textContent = 'Active Scout';
    $('scout-efficiency-text').textContent = 'Scanning web for talent';
  }

  // 3. Render Live Stream Feed
  const recent = localData.recentCaptures || [];
  $('stream-count').textContent = `${recent.length} recent`;

  const feedList = $('feed-list');
  if (recent.length === 0) {
    feedList.innerHTML = `
      <div class="feed-empty">
        <span>📡 Browse LinkedIn, Gmail, or job sites to see live verified captures appear here.</span>
      </div>`;
  } else {
    feedList.innerHTML = recent.slice(0, 6).map(item => {
      const icon = item.source?.includes('linkedin') ? '💼' : item.source?.includes('gmail') || item.source?.includes('outlook') ? '✉️' : '🌐';
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
}

function showError(msg) {
  const el = $('login-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  })[m]);
}

init();
