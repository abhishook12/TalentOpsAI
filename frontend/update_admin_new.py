import re

with open('src/pages/AdminTerminal.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix loadAll function to use safeGet
old_loadall = """  const loadAll = useCallback(async () => {
    if (!unlocked) return
    setLoading(true)
    log('Connecting to TalentOps AI backend…')
    try {
      const [s, ok, ts, ri, fa, tbl, sys, orp, dop, uop, si, ei, al, feed, cov] = await Promise.all([
        adminAxios.get('/admin/stats'),
        adminAxios.get('/admin/ops-kpis'),
        adminAxios.get('/admin/top-states'),
        adminAxios.get('/admin/recent-imports'),
        adminAxios.get('/admin/field-audit'),
        adminAxios.get('/admin/table-sizes'),
        adminAxios.get('/admin/system-info'),
        adminAxios.get('/admin/orphan-companies'),
        adminAxios.get('/admin/data-operations'),
        adminAxios.get('/admin/upload-operations'),
        adminAxios.get('/admin/search-activity'),
        adminAxios.get('/admin/export-analytics'),
        adminAxios.get('/admin/alerts'),
        adminAxios.get('/admin/activity-feed'),
        adminAxios.get('/admin/state-coverage'),
      ])
      setStats(s.data); setOpsKpis(ok.data); setTopStates(ts.data); setRecentImports(ri.data)
      setFieldAudit(fa.data); setTableSizes(tbl.data); setSysInfo(sys.data); setOrphans(orp.data)
      setDataOps(dop.data); setUploadOps(uop.data); setSearchIntel(si.data); setExportIntel(ei.data)
      setAlerts(al.data?.alerts || []); setActivityFeed(feed.data); setStateCoverage(cov.data)
      log(`✓ Stats loaded: ${s.data.total_recruiters?.toLocaleString()} recruiters, ${s.data.total_companies?.toLocaleString()} companies`, 'ok')
      log(`✓ DB size: ${sys.data.database_size} · Uptime: ${sys.data.uptime}`, 'ok')
    } catch (e) {
      log('✗ Failed to load admin data: ' + getErrorMessage(e, e.message || 'unknown error'), 'error')
    }
    setLoading(false)
  }, [unlocked])"""

new_loadall = """  const loadAll = useCallback(async () => {
    if (!unlocked) return
    setLoading(true)
    log('Connecting to TalentOps AI backend…')
    
    const safeGet = async (url) => {
      try { const res = await adminAxios.get(url); return res.data; }
      catch (e) { log(`✗ Failed to load ${url}`, 'warn'); return null; }
    }

    const [s, ok, ts, ri, fa, tbl, sys, orp, dop, uop, si, ei, al, feed, cov] = await Promise.all([
      safeGet('/admin/stats'),
      safeGet('/admin/ops-kpis'),
      safeGet('/admin/top-states'),
      safeGet('/admin/recent-imports'),
      safeGet('/admin/field-audit'),
      safeGet('/admin/table-sizes'),
      safeGet('/admin/system-info'),
      safeGet('/admin/orphan-companies'),
      safeGet('/admin/data-operations'),
      safeGet('/admin/upload-operations'),
      safeGet('/admin/search-activity'),
      safeGet('/admin/export-analytics'),
      safeGet('/admin/alerts'),
      safeGet('/admin/activity-feed'),
      safeGet('/admin/state-coverage'),
    ])

    if (s) setStats(s); if (ok) setOpsKpis(ok); if (ts) setTopStates(ts || []); if (ri) setRecentImports(ri || [])
    if (fa) setFieldAudit(fa); if (tbl) setTableSizes(tbl || []); if (sys) setSysInfo(sys); if (orp) setOrphans(orp)
    if (dop) setDataOps(dop); if (uop) setUploadOps(uop); if (si) setSearchIntel(si); if (ei) setExportIntel(ei)
    if (al) setAlerts(al.alerts || []); if (feed) setActivityFeed(feed); if (cov) setStateCoverage(cov)
    
    if (s && sys) {
      log(`✓ Stats loaded: ${s.total_recruiters?.toLocaleString()} recruiters, ${s.total_companies?.toLocaleString()} companies`, 'ok')
      log(`✓ DB size: ${sys.database_size} · Uptime: ${sys.uptime}`, 'ok')
    }
    
    setLoading(false)
  }, [unlocked])"""

content = content.replace(old_loadall, new_loadall)

# Replace hardcoded colors with CSS variables
# We do not want to replace colors in AdminLock, so we'll do this carefully or just blanket replace since they are exact codes.
replacements = {
    "'#020917'": "'var(--main-bg)'",
    "'#0b1525'": "'var(--panel-bg)'",
    "'#0d1829'": "'var(--card-bg)'",
    "'#1e3a5f'": "'var(--card-border)'",
    "'#1e2d45'": "'var(--card-border)'",
    "'#111c30'": "'var(--bg-hover)'",
    "'#e2e8f0'": "'var(--text-primary)'",
    "'#cbd5e1'": "'var(--text-primary)'",
    "'#94a3b8'": "'var(--text-secondary)'",
    "'#64748b'": "'var(--text-muted)'",
    "'#475569'": "'var(--text-muted)'"
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('src/pages/AdminTerminal.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated AdminTerminal.jsx")
