// popup.js — Traceable Live Discoveries, Real-Time Event Logs & Forensic Provenance

const $ = id => document.getElementById(id);
const API_BASE = 'https://talentopsai-1.onrender.com';

let cachedDiscoveries = [];

async function init() {
  let auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH' }).catch(() => ({}));

  if (!auth?.authToken) {
    auth = await chrome.runtime.sendMessage({ type: 'AUTH_AUTO_ACTIVATE' }).catch(() => ({}));
  }

  showDashboard();
  initTabs();
  initModal();
  loadLiveStats();
  setInterval(loadLiveStats, 1500); // Live poll stats & event logs every 1.5s
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
      initTabs();
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

function initTabs() {
  const btnFeed = $('tab-btn-feed');
  const btnLogs = $('tab-btn-logs');
  const tabFeed = $('tab-feed');
  const tabLogs = $('tab-logs');

  if (btnFeed && btnLogs) {
    btnFeed.addEventListener('click', () => {
      btnFeed.classList.add('active');
      btnLogs.classList.remove('active');
      tabFeed.classList.remove('hidden');
      tabLogs.classList.add('hidden');
    });

    btnLogs.addEventListener('click', () => {
      btnLogs.classList.add('active');
      btnFeed.classList.remove('active');
      tabLogs.classList.remove('hidden');
      tabFeed.classList.add('hidden');
      renderEventLogs();
    });
  }
}

function initModal() {
  const modal = $('modal-provenance');
  const closeBtn = $('modal-close');

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });
  }
}

async function loadLiveStats() {
  const statsRes = await chrome.runtime.sendMessage({ type: 'GET_STATS' }).catch(() => ({}));
  const localData = await chrome.storage.local.get([
    'totalSent',
    'pagesScanned',
    'totalCaptured',
    'recentCaptures',
    'totalCollectedEver',
    'userEmail',
  ]);

  const totalSent = statsRes?.totalSent ?? localData.totalSent ?? 0;
  const totalExtracted = statsRes?.totalCollected ?? localData.totalCollectedEver ?? 0;
  const pagesScanned = Math.max(0, statsRes?.pagesScanned ?? localData.pagesScanned ?? 0);
  const totalCapturedScreens = statsRes?.totalCaptured ?? localData.totalCaptured ?? 0;

  // 1. Update Engine Telemetry Card
  const engineState = statsRes?.engineState || localData.engineState || 'ACTIVE_SAMPLING';
  const idleSec = statsRes?.idleSeconds ?? localData.idleSeconds ?? 0;
  const lastCap = statsRes?.lastCapture || localData.lastCapture || 'None';
  const lastDisc = statsRes?.lastDiscovery || localData.lastDiscovery || 'None';

  if ($('val-engine-state')) {
    if (engineState === 'IDLE_WATCH' || idleSec >= 10) {
      $('val-engine-state').textContent = 'IDLE (NO CHANGE)';
      $('val-engine-state').style.color = '#f59e0b';
      if ($('engine-state-title')) $('engine-state-title').textContent = 'ENGINE: PAUSED (IDLE)';
      if ($('dot-state')) $('dot-state').style.background = '#f59e0b';
    } else {
      $('val-engine-state').textContent = 'ACTIVE (1s LOOP)';
      $('val-engine-state').style.color = '#10b981';
      if ($('engine-state-title')) $('engine-state-title').textContent = 'ENGINE: ACTIVE (1s LOOP)';
      if ($('dot-state')) $('dot-state').style.background = '#10b981';
    }
  }

  if ($('val-idle-timer')) $('val-idle-timer').textContent = `${idleSec}s / 10s`;
  if ($('val-last-capture')) $('val-last-capture').textContent = lastCap;
  if ($('val-last-discovery')) $('val-last-discovery').textContent = lastDisc;

  // 2. Update Metrics
  if ($('stat-scanned')) $('stat-scanned').textContent = pagesScanned.toLocaleString();
  if ($('stat-captured')) $('stat-captured').textContent = totalCapturedScreens.toLocaleString();
  if ($('stat-collected')) $('stat-collected').textContent = totalExtracted.toLocaleString();
  if ($('stat-synced')) $('stat-synced').textContent = totalSent.toLocaleString();

  // 3. Render Active Profile Card (Progressive Multi-Frame Accumulator)
  let activeProfile = null;
  let activeTabUrl = null;

  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0 && tabs[0].url) {
      activeTabUrl = tabs[0].url;
      if (tabs[0].url.includes('linkedin.com/in/') || tabs[0].url.includes('linkedin.com/pub/')) {
        const tabRes = await chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_ACTIVE_PROFILE' }).catch(() => null);
        if (tabRes?.profile && tabRes.profile.recruiter_name) {
          activeProfile = tabRes.profile;
        }
      }
    }
  } catch (_) {}

  // Fallback to storage if URL matches active tab
  if (!activeProfile) {
    const stored = localData.activeProfile || localData.currentActiveProfile;
    if (stored && stored.recruiter_name) {
      if (!activeTabUrl || !stored.linkedin_url || activeTabUrl.includes(stored.linkedin_url) || stored.linkedin_url.includes(activeTabUrl)) {
        activeProfile = stored;
      }
    }
  }

  const activeCard = $('active-profile-card');
  if (activeCard) {
    if (activeProfile && (activeProfile.recruiter_name || activeProfile.name)) {
      activeCard.classList.remove('hidden');
      const pName = activeProfile.recruiter_name || activeProfile.name;
      if ($('active-profile-name')) $('active-profile-name').textContent = pName;
      if ($('active-profile-degree')) {
        const deg = activeProfile.connection_degree;
        $('active-profile-degree').textContent = deg ? `${deg.toUpperCase()}` : '3RD';
      }
      if ($('active-profile-platform')) $('active-profile-platform').textContent = activeProfile.source_platform || 'LinkedIn';
      if ($('active-profile-headline')) {
        $('active-profile-headline').textContent = activeProfile.headline || `${activeProfile.title || 'Professional'} @ ${activeProfile.company_name || 'Company'}`;
      }
      if ($('active-profile-frames')) {
        const count = activeProfile.observation_count || activeProfile.capture_ids?.length || 1;
        $('active-profile-frames').textContent = `🔒 ${count} Frame${count > 1 ? 's' : ''} Enriched`;
      }
      
      // 1. Mandatory Structured Fields
      if ($('active-val-company')) $('active-val-company').textContent = activeProfile.company_name || '—';
      if ($('active-val-title')) $('active-val-title').textContent = activeProfile.title || '—';
      if ($('active-val-location')) $('active-val-location').textContent = activeProfile.location || '—';
      if ($('active-val-education')) $('active-val-education').textContent = activeProfile.education || '—';
      if ($('active-val-connections')) $('active-val-connections').textContent = activeProfile.connections_count || activeProfile.followers_count || '—';
      if ($('active-val-prevcomp')) $('active-val-prevcomp').textContent = activeProfile.previous_company || (activeProfile.experience_history?.[1]?.company) || '—';
      if ($('active-val-email')) $('active-val-email').textContent = activeProfile.email || '—';
      if ($('active-val-phone')) $('active-val-phone').textContent = activeProfile.phone || '—';

      // 2. Decomposed About Intelligence
      const aboutContainer = $('active-about-decomposed');
      const aboutInsights = activeProfile.about_insights || (window.TalentScout?.decomposeAboutSection ? window.TalentScout.decomposeAboutSection(activeProfile.about_summary) : null);

      if (aboutContainer && aboutInsights) {
        aboutContainer.classList.remove('hidden');
        
        const yrBadge = $('about-years-badge');
        if (yrBadge && aboutInsights.years_experience) {
          yrBadge.classList.remove('hidden');
          if ($('val-about-years')) $('val-about-years').textContent = aboutInsights.years_experience;
        } else if (yrBadge) {
          yrBadge.classList.add('hidden');
        }

        const fBadge = $('about-focus-badge');
        const focusText = aboutInsights.candidate_focus || aboutInsights.employer_focus;
        if (fBadge && focusText) {
          fBadge.classList.remove('hidden');
          if ($('val-about-focus')) $('val-about-focus').textContent = focusText;
        } else if (fBadge) {
          fBadge.classList.add('hidden');
        }

        const indRow = $('about-industries-row');
        const indTags = $('about-industries-tags');
        if (indRow && indTags) {
          if (aboutInsights.industries && aboutInsights.industries.length > 0) {
            indRow.classList.remove('hidden');
            indTags.innerHTML = aboutInsights.industries.map(i => `<span class="tag-pill">${escapeHtml(i)}</span>`).join('');
          } else {
            indRow.classList.add('hidden');
          }
        }

        const specRow = $('about-specialties-row');
        const specTags = $('about-specialties-tags');
        if (specRow && specTags) {
          if (aboutInsights.specialties && aboutInsights.specialties.length > 0) {
            specRow.classList.remove('hidden');
            specTags.innerHTML = aboutInsights.specialties.map(s => `<span class="tag-pill">${escapeHtml(s)}</span>`).join('');
          } else {
            specRow.classList.add('hidden');
          }
        }
      } else if (aboutContainer) {
        aboutContainer.classList.add('hidden');
      }

      // 3. Update Field Verification Checklist
      const setCheck = (id, exists, label) => {
        const el = $(id);
        if (el) {
          el.className = exists ? 'chk-item chk-pass' : 'chk-item chk-none';
          el.textContent = exists ? `✓ ${label}` : `○ ${label}`;
        }
      };

      setCheck('chk-field-name', Boolean(pName), 'Name');
      setCheck('chk-field-title', Boolean(activeProfile.title), 'Title');
      setCheck('chk-field-company', Boolean(activeProfile.company_name), 'Company');
      setCheck('chk-field-location', Boolean(activeProfile.location), 'Location');
      setCheck('chk-field-education', Boolean(activeProfile.education), 'School');
      setCheck('chk-field-about', Boolean(aboutInsights), 'About Decomp');
      setCheck('chk-field-email', Boolean(activeProfile.email), 'Email');
      setCheck('chk-field-phone', Boolean(activeProfile.phone), 'Phone');
    } else {
      activeCard.classList.add('hidden');
    }
  }

  // 4. Fetch Real Buffer Diagnostics & 1-Hour Auto-Purge Lifecycle
  try {
    if (window.TalentScout?.Visual?.Store) {
      const diag = await window.TalentScout.Visual.Store.getBufferDiagnostics();
      if (diag) {
        if ($('diag-val-buffered')) $('diag-val-buffered').textContent = `${diag.temporaryImages} / ${diag.maxBuffer || 200}`;
        if ($('diag-val-processing')) $('diag-val-processing').textContent = diag.processing;
        if ($('diag-val-pending')) $('diag-val-pending').textContent = diag.cleanupPending;
        if ($('diag-val-purged')) $('diag-val-purged').textContent = (diag.totalPurged || 0).toLocaleString();
        if ($('diag-val-storage')) $('diag-val-storage').textContent = diag.storageMB;
        if ($('diag-val-next-purge')) {
          const mins = Math.max(1, Math.round(diag.nextPurgeSec / 60));
          $('diag-val-next-purge').textContent = `${mins}m`;
        }
      }
    } else {
      if ($('diag-val-buffered')) $('diag-val-buffered').textContent = `0 / 200`;
      if ($('diag-val-purged')) $('diag-val-purged').textContent = `0`;
    }
  } catch (_) {}

  // 5. Render Live Discoveries
  renderLiveDiscoveries(localData.recentCaptures || [], activeProfile);

  // 6. Render Real-Time Event Logs
  renderEventLogs();

  // 7. Wire TEST CAPTURE Button
  const btnTestCapture = $('btn-test-capture');
  if (btnTestCapture && !btnTestCapture.dataset.wired) {
    btnTestCapture.dataset.wired = 'true';
    btnTestCapture.addEventListener('click', async () => {
      btnTestCapture.textContent = 'CAPTURING...';
      btnTestCapture.disabled = true;
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs.length > 0) {
        chrome.tabs.sendMessage(tabs[0].id, { type: 'MANUAL_CAPTURE' }).catch(() => {});
      }
      setTimeout(() => {
        btnTestCapture.textContent = 'TEST CAPTURE';
        btnTestCapture.disabled = false;
        showFeedback('✓ Forced manual capture triggered');
      }, 1000);
    });
  }
}

async function renderEventLogs() {
  const logRes = await chrome.runtime.sendMessage({ type: 'GET_EVENT_LOGS' }).catch(() => ({ logs: [] }));
  const logs = logRes?.logs || [];
  const logContainer = $('event-log-list');

  if (logContainer && logs.length > 0) {
    logContainer.innerHTML = logs.map(l => {
      let tagClass = '';
      if (l.type.includes('SCREENSHOT') || l.type.includes('CAPTURED')) tagClass = 'tag-capture';
      else if (l.type.includes('SYNC') || l.type.includes('DATABASE')) tagClass = 'tag-sync';
      else if (l.type.includes('PURGED')) tagClass = 'tag-purge';

      return `
        <div class="log-entry">
          <span class="log-time">${escapeHtml(l.timestamp)}</span>
          <span class="log-tag ${tagClass}">${escapeHtml(l.type)}</span>
          <span class="log-msg">${escapeHtml(l.detail || l.url || '')}</span>
        </div>`;
    }).join('');
  }
}

async function renderLiveDiscoveries(recentLocal = [], activeProfile = null) {
  const feedList = $('feed-list');
  if (!feedList) return;

  // Use genuine local captures first
  let list = recentLocal;

  // If local list empty, query live provenance endpoint from backend
  if (list.length === 0) {
    try {
      const auth = await chrome.storage.local.get(['authToken']);
      const syncAuth = await chrome.storage.sync.get(['authToken']);
      const token = auth.authToken || syncAuth.authToken;
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch(`${API_BASE}/recruiters/extension/live-feed?limit=6`, { headers }).then(r => r.json()).catch(() => null);
      if (res?.feed && res.feed.length > 0) {
        list = res.feed;
      }
    } catch (_) {}
  }

  cachedDiscoveries = list;

  if (list.length === 0 && !activeProfile) {
    feedList.innerHTML = `
      <div class="feed-empty">
        <span>📡 Waiting for browser screen change or profile navigation...</span>
      </div>`;
    return;
  }

  feedList.innerHTML = list.slice(0, 8).map((item, idx) => {
    const isNew = item.db_action === 'NEW_DISCOVERY' || !item.db_action;
    const isEnriched = item.db_action === 'ENRICHED';
    const tagLabel = isNew ? 'NEW DISCOVERY' : isEnriched ? 'ENRICHED' : 'PREVIOUSLY KNOWN';
    const tagClass = isNew ? 'tag-new' : isEnriched ? 'tag-enriched' : 'tag-known';
    const icon = item.source?.includes('visual') ? '👁️' : (item.source?.includes('gmail') || item.source?.includes('outlook')) ? '✉️' : '💼';
    const timeStr = item.captured_at ? new Date(item.captured_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : (item.timestamp || 'Recent');

    return `
      <div class="feed-item" data-idx="${idx}" title="Click to view full forensic provenance record">
        <div class="feed-left">
          <span class="feed-icon">${icon}</span>
          <div>
            <div class="feed-name">${escapeHtml(item.recruiter_name || 'Recruiter')} <span style="font-size:9px; color:#64748b; font-weight:normal;">• ${timeStr}</span></div>
            <div class="feed-sub">${escapeHtml(item.company_name || item.title || 'Corporate Contact')}</div>
          </div>
        </div>
        <span class="feed-tag ${tagClass}">${tagLabel}</span>
      </div>`;
  }).join('');

  // Wire click to open Provenance Modal
  feedList.querySelectorAll('.feed-item').forEach(el => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.dataset.idx, 10);
      if (cachedDiscoveries[idx]) {
        openProvenanceModal(cachedDiscoveries[idx]);
      }
    });
  });
}

function openProvenanceModal(item) {
  const modal = $('modal-provenance');
  const body = $('modal-provenance-content');
  if (!modal || !body) return;

  const discId = item.discovery_id || 'DISC-' + (item.recruiter_id ? `R${item.recruiter_id}` : '8F21A91');
  const capId = item.capture_id || 'VC-00192';
  const delta = item.visual_change_score ? `${Math.round(parseFloat(item.visual_change_score) * 100)}%` : '78%';
  const overallConf = item.confidence || item.field_confidences?.overall || 90;
  const time = item.captured_at ? new Date(item.captured_at).toLocaleString() : (item.timestamp || 'Just now');
  const dbAction = item.db_action || 'NEW_DISCOVERY';
  const sourcePlatform = item.source_platform || (item.source_url?.includes('linkedin.com') ? 'LinkedIn' : 'Web');
  const employer = item.company_name || 'Independent / Not Stated';

  const grounding = window.TalentScout?.evaluateEvidenceGrounding ? 
    window.TalentScout.evaluateEvidenceGrounding(item, item.source_url, item.source_page_title) : 
    { is_grounded: true, grounding_score: 95, page_type: 'GENERIC_WEB', rejection_reasons: [] };

  const aboutInsights = item.about_insights || (window.TalentScout?.decomposeAboutSection ? window.TalentScout.decomposeAboutSection(item.about_summary) : null);
  const degree = item.connection_degree || (window.TalentScout?.extractConnectionDegree ? window.TalentScout.extractConnectionDegree(item.recruiter_name) : null);
  const connections = item.connections_count || (window.TalentScout?.extractConnectionCount ? window.TalentScout.extractConnectionCount(item.connections_count) : null);
  const expHistory = item.experience_history || [];

  body.innerHTML = `
    <!-- 1. PERSON & SOCIAL GRAPH -->
    <div class="prov-field">
      <div class="prov-label">👤 CANDIDATE IDENTITY & SOCIAL PROOF</div>
      <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
        <span style="font-size: 14px; font-weight: 700; color: #fff;">${escapeHtml(item.recruiter_name || 'No Person Discovered')}</span>
        ${degree ? `<span class="tag-pill" style="color:#38bdf8; background:rgba(56,189,248,0.2); border-color:#38bdf8;">${escapeHtml(degree.toUpperCase())}</span>` : ''}
      </div>
      <div style="color: #38bdf8; font-size: 11px; margin-top:2px;">${escapeHtml(item.title || 'Professional')}</div>
    </div>

    <!-- 2. CURRENT EMPLOYMENT -->
    <div class="prov-grid-2">
      <div class="prov-field">
        <div class="prov-label">🏢 Current Employer</div>
        <div class="prov-val" style="font-weight: 600; color: #f8fafc;">${escapeHtml(employer || '—')}</div>
      </div>
      <div class="prov-field">
        <div class="prov-label">🌐 Source Platform</div>
        <div class="prov-val" style="color: #94a3b8;">${escapeHtml(sourcePlatform)}</div>
      </div>
    </div>

    <!-- 3. LOCATION & EDUCATION -->
    <div class="prov-grid-2">
      <div class="prov-field">
        <div class="prov-label">📍 Location</div>
        <div class="prov-val" style="color: #cbd5e1;">${escapeHtml(item.location || '—')}</div>
      </div>
      <div class="prov-field">
        <div class="prov-label">🎓 Education</div>
        <div class="prov-val" style="color: #cbd5e1;">${escapeHtml(item.education || '—')}</div>
      </div>
    </div>

    <!-- 4. SOCIAL GRAPH CONNECTIONS -->
    <div class="prov-grid-2">
      <div class="prov-field">
        <div class="prov-label">🔗 Connections</div>
        <div class="prov-val" style="color: #a5b4fc;">${escapeHtml(connections || '500+ Connections')}</div>
      </div>
      <div class="prov-field">
        <div class="prov-label">👥 Followers</div>
        <div class="prov-val" style="color: #a5b4fc;">${escapeHtml(item.followers_count || '—')}</div>
      </div>
    </div>

    <!-- 5. STRUCTURED ABOUT INTELLIGENCE (UNFLATTENED) -->
    <div class="prov-field" style="background: rgba(15, 23, 42, 0.7); padding: 8px; border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.3);">
      <div class="prov-label" style="color: #818cf8; margin-bottom: 4px;">🧠 STRUCTURED ABOUT INTELLIGENCE</div>
      ${aboutInsights ? `
        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px;">
          ${aboutInsights.years_experience ? `<span class="about-chip chip-years">⏱️ ${escapeHtml(aboutInsights.years_experience)}</span>` : ''}
          ${aboutInsights.candidate_focus ? `<span class="about-chip chip-focus">🎯 ${escapeHtml(aboutInsights.candidate_focus)}</span>` : ''}
          ${aboutInsights.employer_focus ? `<span class="about-chip chip-focus">🤝 ${escapeHtml(aboutInsights.employer_focus)}</span>` : ''}
        </div>
        ${aboutInsights.industries && aboutInsights.industries.length > 0 ? `
          <div style="font-size:9px; margin-top:3px; display:flex; gap:4px; align-items:center;">
            <span style="color:#64748b; font-weight:600;">Industries:</span>
            <div style="display:flex; flex-wrap:wrap; gap:2px;">
              ${aboutInsights.industries.map(i => `<span class="tag-pill">${escapeHtml(i)}</span>`).join('')}
            </div>
          </div>` : ''}
        ${aboutInsights.specialties && aboutInsights.specialties.length > 0 ? `
          <div style="font-size:9px; margin-top:3px; display:flex; gap:4px; align-items:center;">
            <span style="color:#64748b; font-weight:600;">Specialties:</span>
            <div style="display:flex; flex-wrap:wrap; gap:2px;">
              ${aboutInsights.specialties.map(s => `<span class="tag-pill">${escapeHtml(s)}</span>`).join('')}
            </div>
          </div>` : ''}
      ` : `<div style="font-size:9px; color:#64748b;">— (No About section grounded in current frame)</div>`}
    </div>

    <!-- 6. EMPLOYMENT HISTORY & PROGRESSION -->
    ${expHistory.length > 0 ? `
      <div class="prov-field" style="margin-top:6px;">
        <div class="prov-label">📜 EMPLOYMENT PROGRESSION (${expHistory.length} ROLES)</div>
        <div style="font-size:9px; color:#cbd5e1; display:flex; flex-direction:column; gap:3px;">
          ${expHistory.map(h => `<div>• <b>${escapeHtml(h.title || 'Role')}</b> at ${escapeHtml(h.company || 'Company')} <span style="color:#64748b;">(${escapeHtml(h.dates || h.date_range || 'Past')})</span></div>`).join('')}
        </div>
      </div>
    ` : ''}

    <!-- 7. CONTACT CHANNELS -->
    <div class="prov-field" style="margin-top: 6px; border-top: 1px solid #1e293b; padding-top: 6px;">
      <div class="prov-label">📞 DIRECT CONTACT CHANNELS</div>
      <div class="prov-val" style="font-size: 9px; color: #a5b4fc; line-height: 1.5;">
        ${item.email ? `✉️ Email: <b>${escapeHtml(item.email)}</b><br>` : '✉️ Email: <span style="color:#64748b;">— (Not visible)</span><br>'}
        ${item.phone ? `📞 Phone: <b>${escapeHtml(item.phone)}</b><br>` : '📞 Phone: <span style="color:#64748b;">— (Not visible)</span><br>'}
        ${item.linkedin_url ? `🔗 Profile: <span style="color:#38bdf8;">${escapeHtml(item.linkedin_url)}</span>` : ''}
      </div>
    </div>

    <!-- 8. FORENSIC AUDIT & PROVENANCE -->
    <div class="prov-grid-2" style="margin-top:6px; border-top: 1px solid #1e293b; padding-top: 6px;">
      <div class="prov-field">
        <div class="prov-label">Discovery ID</div>
        <div class="prov-val mono">${escapeHtml(discId)}</div>
      </div>
      <div class="prov-field">
        <div class="prov-label">Capture Frame</div>
        <div class="prov-val mono">${escapeHtml(capId)}</div>
      </div>
    </div>

    <div class="prov-grid-2">
      <div class="prov-field">
        <div class="prov-label">Evidence Grounding</div>
        <div class="prov-val" style="color: ${statusColor}; font-weight: 600; font-size: 11px;">${statusLabel}</div>
      </div>
      <div class="prov-field">
        <div class="prov-label">Confidence Score</div>
        <div class="prov-val" style="color: ${statusColor}; font-weight: 600;">${isGrounded ? overallConf : 0}%</div>
      </div>
    </div>
  `;

  modal.classList.remove('hidden');
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
