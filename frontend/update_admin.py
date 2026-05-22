import os

path = 'C:/TalentOpsAI/frontend/src/pages/AdminTerminal.jsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add dataQuality state
content = content.replace("const [tableSizes, setTableSizes] = useState([])", "const [tableSizes, setTableSizes] = useState([])\n  const [dataQuality, setDataQuality] = useState(null)")

# Fetch data-quality
content = content.replace("adminAxios.get('/admin/orphan-companies'),", "adminAxios.get('/admin/orphan-companies'),\n        adminAxios.get('/admin/data-quality'),")

content = content.replace("setFieldAudit(fa.data); setTableSizes(tbl.data); setSysInfo(sys.data); setOrphans(orp.data)", "setFieldAudit(fa.data); setTableSizes(tbl.data); setSysInfo(sys.data); setOrphans(orp.data); setDataQuality(arguments[0][7].data)")

# UI for data quality
ui_start = "{/* ── DATA HEALTH TAB ── */}"
ui_search = "        {activeTab === 'data' && ("
ui_idx = content.find(ui_search) + len(ui_search)

data_quality_ui = """
          <div style={{ animation: 'fadeUp 0.25s ease' }}>
            {dataQuality && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 24 }}>
                  <StatCard icon="ti-alert-triangle" label="Needs Review" value={fmt(dataQuality.needs_review)} color="#f59e0b" glow={dataQuality.needs_review > 0} />
                  <StatCard icon="ti-map-off" label="Low Conf. Locations" value={fmt(dataQuality.low_confidence_location)} color="#f43f5e" />
                  <StatCard icon="ti-user-off" label="Incomplete Profiles (<50%)" value={fmt(dataQuality.incomplete_profiles)} color="#8b5cf6" />
                </div>
            )}
"""

content = content.replace(ui_search, ui_search + data_quality_ui)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated AdminTerminal.jsx successfully.")
