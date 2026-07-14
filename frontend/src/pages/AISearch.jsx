import { useEffect, useMemo, useState } from 'react'
import { exportToExcel } from '../services/export'
import api, { API, checkAuth, getErrorMessage, login, logAction } from '../services/api'
import { CompanyLogo } from '../components/CompanyLogo'
import { useSessionState } from '../hooks/useSessionState'

function initials(name) {
  const parts = (name || '').trim().split(' ').filter(Boolean)
  if (!parts.length) return 'NA'
  return ((parts[0][0] || '') + (parts[1]?.[0] || '')).toUpperCase()
}

function matchTypeFor(rec, q) {
  const s = (q || '').trim().toLowerCase()
  if (!s) return 'Fuzzy'
  const name = (rec?.recruiter_name || '').toLowerCase()
  const emailFields = (Array.isArray(rec?.all_emails) && rec.all_emails.length ? rec.all_emails : [rec?.email, rec?.email2, rec?.email3, rec?.email4, rec?.alternate_emails])
    .filter(Boolean)
    .map((value) => String(value).toLowerCase())
  const phoneFields = (Array.isArray(rec?.all_phones) && rec.all_phones.length ? rec.all_phones : [rec?.phone, rec?.phone2, rec?.phone3, rec?.phone4, rec?.alternate_phones])
    .filter(Boolean)
    .map((value) => String(value))
  const company = (rec?.company_name || '').toLowerCase()
  const normalizedQueryDigits = s.replace(/[^\d]/g, '')
  const exactEmail = emailFields.some((value) => value === s || value.includes(s))
  const exactPhone = normalizedQueryDigits
    ? phoneFields.some((value) => value.replace(/[^\d]/g, '').includes(normalizedQueryDigits))
    : false
  if (name === s || company === s || exactEmail || exactPhone) return 'Exact'
  if (name.startsWith(s) || company.startsWith(s) || emailFields.some((value) => value.startsWith(s))) return 'Exact'
  return 'Fuzzy'
}

function safe(v) {
  return v && String(v).trim() ? String(v).trim() : 'Not available'
}

const CONTACT_SLOT_COUNT = 3

function contactSlots(values, fallback) {
  const list = Array.isArray(values) && values.length
    ? values
    : fallback && String(fallback).trim()
      ? [String(fallback).trim()]
      : []
  return Array.from({ length: CONTACT_SLOT_COUNT }, (_, index) => list[index] || '')
}

function badgeForMatch(matchType) {
  const exact = matchType === 'Exact'
  return {
    label: exact ? 'EXACT' : 'FUZZY',
    bg: exact ? 'rgba(22, 163, 74, 0.14)' : 'rgba(245, 158, 11, 0.14)',
    fg: exact ? '#2f8f53' : '#b07843',
    border: exact ? 'rgba(22, 163, 74, 0.25)' : 'rgba(245, 158, 11, 0.28)',
  }
}

function labelizeMatchReason(reason) {
  return String(reason || 'metadata_fuzzy')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function parseLooseJson(value) {
  if (!value) return null
  if (typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function flattenValue(value) {
  if (value == null) return []
  if (Array.isArray(value)) {
    return value.flatMap(flattenValue)
  }
  if (typeof value === 'object') {
    return [JSON.stringify(value)]
  }
  const text = String(value).trim()
  if (!text) return []
  return [text]
}

function dedupeValues(values, normalizer = (value) => value.toLowerCase()) {
  const seen = new Set()
  const deduped = []
  values.forEach((value) => {
    const normalized = normalizer(value)
    if (!normalized || seen.has(normalized)) return
    seen.add(normalized)
    deduped.push(value)
  })
  return deduped
}

function collectContactValues(record, matcher) {
  const raw = parseLooseJson(record?.raw_data) || {}
  const metadata = parseLooseJson(record?.metadata_json) || {}
  const buckets = [record || {}, raw, metadata]
  const values = []

  const visit = (value, path = []) => {
    if (value == null) return
    if (Array.isArray(value)) {
      value.forEach((item, index) => visit(item, [...path, String(index)]))
      return
    }
    if (typeof value === 'object') {
      Object.entries(value).forEach(([key, child]) => visit(child, [...path, key]))
      return
    }
    const joinedPath = path.join('.')
    if (!matcher(joinedPath, value)) return
    values.push(...flattenValue(value))
  }

  buckets.forEach((bucket) => {
    visit(bucket)
  })

  return values
}

function splitLooseList(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.flatMap(splitLooseList)
  return String(value)
    .split(/[,\n;|]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function collectTextValuesDeep(value) {
  if (value == null) return []
  if (Array.isArray(value)) return value.flatMap(collectTextValuesDeep)
  if (typeof value === 'object') return Object.values(value).flatMap(collectTextValuesDeep)
  const text = String(value).trim()
  return text ? [text] : []
}

function extractEmailsFromText(values) {
  const matches = []
  values.forEach((value) => {
    const found = String(value).match(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g) || []
    matches.push(...found)
  })
  return dedupeValues(matches.map((value) => value.trim().toLowerCase()))
}

function extractPhonesFromText(values) {
  const matches = []
  values.forEach((value) => {
    const found = String(value).match(/\+?\d[\d\s().-]{7,}\d/g) || []
    found.forEach((item) => {
      const digits = item.replace(/[^\d+]/g, '').trim()
      if (digits.replace(/\D/g, '').length < 10) return
      matches.push(digits)
    })
  })
  return dedupeValues(matches, (value) => value.replace(/[^\d+]/g, ''))
}

function looksLikeEmailKey(key) {
  const normalized = String(key || '').toLowerCase()
  return /(email|e-mail|mail)/.test(normalized) && !/(domain|pattern|status|verified|quality)/.test(normalized)
}

function looksLikePhoneKey(key) {
  const normalized = String(key || '').toLowerCase()
  return /(phone|mobile|cell|tel|telephone|contact_number|contactnumber|whatsapp)/.test(normalized)
}

function mergeSelectedRecord(summary, detail) {
  if (!summary && !detail) return null
  if (summary && detail && summary.recruiter_id !== detail.recruiter_id) {
    return summary
  }
  return { ...(summary || {}), ...(detail || {}) }
}

function buildRecruiterInsight(record) {
  if (!record) {
    return { emails: [], phones: [], extras: [], createdAt: 'Not available', address: 'Not available' }
  }

  const sourceTexts = collectTextValuesDeep(parseLooseJson(record.raw_data) || {}).concat(
    collectTextValuesDeep(parseLooseJson(record.metadata_json) || {})
  )
  const emailValues = [
    ...(Array.isArray(record.all_emails) ? record.all_emails : []),
    record.email,
    record.email2,
    record.email3,
    record.email4,
    ...splitLooseList(record.alternate_emails),
    ...collectContactValues(record, (key) => looksLikeEmailKey(key)),
    ...extractEmailsFromText(sourceTexts),
  ].filter(Boolean)
  const phoneValues = [
    ...(Array.isArray(record.all_phones) ? record.all_phones : []),
    record.phone,
    record.phone2,
    record.phone3,
    record.phone4,
    ...splitLooseList(record.alternate_phones),
    ...collectContactValues(record, (key) => looksLikePhoneKey(key)),
    ...extractPhonesFromText(sourceTexts),
  ].filter(Boolean)

  const emails = dedupeValues(
    emailValues
      .map((value) => String(value).trim())
      .filter(val => {
        if (!val || val.includes('missing.local')) return false
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)
      })
  )
  const phones = dedupeValues(
    phoneValues
      .map((value) => String(value).trim())
      .filter(val => {
        if (!val) return false
        const normalized = val.toLowerCase()
        if (normalized === 'false' || normalized === 'true' || normalized === 'null' || normalized === 'none') return false
        const digits = val.replace(/[^\d+]/g, '')
        return digits.length >= 7
      }),
    (value) => value.replace(/[^\d+]/g, '')
  )

  const raw = parseLooseJson(record.raw_data) || {}
  const metadata = parseLooseJson(record.metadata_json) || {}
  const ignoredKeys = new Set([
    'recruiter_name', 'name', 'full_name', 'email', 'email2', 'work_email', 'personal_email',
    'email3', 'email4', 'alternate_emails', 'all_emails',
    'phone', 'phone2', 'phone3', 'phone4', 'mobile', 'cell', 'contact', 'contact_number', 'telephone',
    'alternate_phones', 'all_phones', 'linkedin', 'specialization', 'title',
    'company', 'company_name', 'location', 'state', 'city', 'address', 'notes',
    'created_at', 'updated_at', 'recruiter_id', 'company_id',
  ])

  const extras = []
  const walkExtras = (value, path = []) => {
    if (value == null) return
    if (Array.isArray(value)) {
      value.forEach((item, index) => walkExtras(item, [...path, String(index + 1)]))
      return
    }
    if (typeof value === 'object') {
      Object.entries(value).forEach(([key, child]) => walkExtras(child, [...path, key]))
      return
    }

    const leafKey = String(path[path.length - 1] || '').toLowerCase()
    const fullPath = path.join('.').toLowerCase()
    if (!leafKey || ignoredKeys.has(leafKey) || looksLikeEmailKey(fullPath) || looksLikePhoneKey(fullPath)) return

    const flattened = String(value).trim()
    if (!flattened) return
    extras.push({
      key: path.join(' / ').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim(),
      value: flattened,
    })
  }

  ;[raw, metadata].forEach((bucket) => {
    if (!bucket || typeof bucket !== 'object') return
    if (Array.isArray(bucket)) {
      bucket.forEach((item, index) => walkExtras(item, [`Source row ${index + 1}`]))
      return
    }
    Object.entries(bucket).forEach(([key, value]) => {
      walkExtras(value, [key])
    })
  })

  const createdAt = record.created_at
    ? new Date(record.created_at).toLocaleString()
    : 'Not available'

  const addressCandidates = dedupeValues([
    record.location,
    record.address,
    ...collectContactValues(record, (key) => /(address|street|suite|city|state|zip|postal|location)/i.test(key)),
  ].filter(Boolean))
  const address = addressCandidates[0] || [record.location, record.state].filter((part) => part && String(part).trim()).join(', ') || 'Not available'

  return {
    emails,
    phones,
    extras: dedupeValues(extras.map((item) => `${item.key}::${item.value}`)).map((item) => {
      const [key, value] = item.split('::')
      return { key, value }
    }),
    createdAt,
    address,
  }
}

function iconButtonStyle(disabled = false) {
  return {
    width: 34,
    height: 34,
    borderRadius: 10,
    border: '1px solid var(--card-border)',
    background: 'var(--card-bg)',
    color: 'var(--text-secondary)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.15s ease',
  }
}

export default function AISearch() {
  const [query, setQuery] = useSessionState('ai_query', '')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useSessionState('ai_selectedId', null)
  const [showFilters, setShowFilters] = useState(false)
  const [toast, setToast] = useState('')
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [selectedDetailLoading, setSelectedDetailLoading] = useState(false)
  const [selectedDetailError, setSelectedDetailError] = useState('')

  const [filterCompany, setFilterCompany] = useSessionState('ai_filterCompany', '')
  const [filterLocation, setFilterLocation] = useSessionState('ai_filterLocation', '')
  const [filterSpecialization, setFilterSpecialization] = useSessionState('ai_filterSpecialization', '')

  const [editOpen, setEditOpen] = useState(false)
  const [editAuthed, setEditAuthed] = useState(false)
  const [editPin, setEditPin] = useState('')
  const [editError, setEditError] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editForm, setEditForm] = useState({
    recruiter_name: '',
    email: '',
    email2: '',
    email3: '',
    email4: '',
    phone: '',
    phone2: '',
    phone3: '',
    phone4: '',
    linkedin: '',
    location: '',
    specialization: '',
    notes: '',
  })

  const primeEditState = (record) => {
    setEditError('')
    setEditPin('')
    setEditSaving(false)
    setEditAuthed(false)
    setEditForm({
      recruiter_name: record?.recruiter_name || '',
      email: record?.email || '',
      email2: record?.email2 || '',
      email3: record?.email3 || '',
      email4: record?.email4 || '',
      phone: record?.phone || '',
      phone2: record?.phone2 || '',
      phone3: record?.phone3 || '',
      phone4: record?.phone4 || '',
      linkedin: record?.linkedin || '',
      location: record?.location || '',
      specialization: record?.specialization || '',
      notes: record?.notes || '',
    })
  }

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!query.trim()) {
        setSearchResults([])
        setSelectedId(null)
        setLoading(false)
        setError('')
        return
      }

      setLoading(true)
      setError('')
      try {
        const params = { q: query.trim(), limit: 100 }
        if (filterCompany.trim()) params.company = filterCompany.trim()
        if (filterLocation.trim()) params.location = filterLocation.trim()
        if (filterSpecialization.trim()) params.specialization = filterSpecialization.trim()

        const res = await api.get('/recruiters/search', { params })
        const sorted = [...(res.data || [])].sort((a, b) => {
          const ma = matchTypeFor(a, query) === 'Exact' ? 0 : 1
          const mb = matchTypeFor(b, query) === 'Exact' ? 0 : 1
          if (ma !== mb) return ma - mb
          return (b.relevance_score || 0) - (a.relevance_score || 0)
        })

        setSearchResults(sorted)
        setSelectedId((prev) => (prev && sorted.some((x) => x.recruiter_id === prev) ? prev : null))

        logAction('SEARCH_RECRUITERS', {
          q: query.trim(),
          company: filterCompany.trim() || null,
          location: filterLocation.trim() || null,
          specialization: filterSpecialization.trim() || null,
          results: Array.isArray(sorted) ? sorted.length : 0,
          context: 'ai_search',
        })
      } catch (err) {
        setError('Could not load recruiter search results.')
        setSearchResults([])
        setSelectedId(null)
      } finally {
        setLoading(false)
      }
    }, 260)

    return () => clearTimeout(t)
  }, [query, filterCompany, filterLocation, filterSpecialization])

  const selectedSummary = useMemo(
    () => searchResults.find((r) => r.recruiter_id === selectedId) || null,
    [searchResults, selectedId]
  )

  useEffect(() => {
    let cancelled = false

    if (!selectedId) {
      return
    }
    ;(async () => {
      try {
        const { data } = await api.get(`/recruiters/${selectedId}`)
        if (cancelled) return
        setSelectedDetail(data || null)
      } catch (err) {
        if (cancelled) return
        setSelectedDetail(null)
        setSelectedDetailError(getErrorMessage(err, 'Could not load recruiter details.'))
      } finally {
        if (!cancelled) setSelectedDetailLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [selectedId])

  const selected = useMemo(
    () => (selectedId ? mergeSelectedRecord(selectedSummary, selectedDetail) : null),
    [selectedId, selectedSummary, selectedDetail]
  )

  const selectedInsight = useMemo(() => buildRecruiterInsight(selected), [selected])

  useEffect(() => {
    if (!editOpen) return

    ;(async () => {
      const ok = await checkAuth()
      setEditAuthed(ok)
    })()
  }, [editOpen, selected])

  const activeFiltersCount = useMemo(() => {
    let n = 0
    if (filterCompany.trim()) n += 1
    if (filterLocation.trim()) n += 1
    if (filterSpecialization.trim()) n += 1
    return n
  }, [filterCompany, filterLocation, filterSpecialization])

  const fireSoon = (label) => {
    setToast(`${label}: Coming soon`)
    console.log(`[Coming soon] ${label}`)
    setTimeout(() => setToast(''), 1400)
  }

  const clearAll = () => {
    setQuery('')
    setSearchResults([])
      setSelectedId(null)
      setSelectedDetail(null)
      setSelectedDetailLoading(false)
      setSelectedDetailError('')
      setError('')
      setLoading(false)
      setFilterCompany('')
    setFilterLocation('')
    setFilterSpecialization('')
    setShowFilters(false)
  }

  const matchTypeForSelected = selected ? matchTypeFor(selected, query) : 'Fuzzy'
  const matchBadge = badgeForMatch(matchTypeForSelected)

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14, height: '100%' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 14,
          padding: '12px 14px',
          border: '1px solid var(--card-border)',
          borderRadius: 14,
          background: 'var(--panel-bg)',
          boxShadow: 'var(--shadow)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 12,
                background: 'var(--accent)',
                color: 'var(--text-inverse)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <i className="ti ti-sparkles" style={{ fontSize: 16 }} />
            </div>
            <div>
              <h1 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>Recruiter Intelligence Search</h1>
              <p style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)' }}>
                Ranked recruiter search — exact matches first, fuzzy matches after. No demo data.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={() => { navigator.clipboard.writeText(window.location.href); setToast('Link copied to clipboard') }} style={{ ...iconButtonStyle(false), width: 38 }} title="Copy Link">
            <i className="ti ti-share" />
          </button>
          <button onClick={() => exportToExcel(searchResults, 'AI_Search_Results.xlsx')} style={{ ...iconButtonStyle(false), width: 38 }} title="Export to Excel">
            <i className="ti ti-download" />
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.65fr 1fr', gap: 14, height: 'calc(100vh - 210px)', minHeight: 0 }}>
        <div
          style={{
            border: '1px solid var(--card-border)',
            borderRadius: 14,
            background: 'var(--panel-bg)',
            boxShadow: 'var(--shadow)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              padding: 14,
              borderBottom: '1px solid var(--card-border)',
              background: 'linear-gradient(180deg, var(--panel-bg) 0%, rgba(0,0,0,0.00) 100%)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  borderRadius: 12,
                  border: '1px solid var(--card-border)',
                  background: 'var(--card-bg)',
                }}
              >
                <i className="ti ti-search" style={{ color: 'var(--text-muted)' }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by name, email, company…"
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                  }}
                />
                {loading && (
                  <i className="ti ti-loader-2" style={{ color: 'var(--text-muted)', animation: 'spin 0.8s linear infinite' }} />
                )}
              </div>

              <button
                onClick={() => setShowFilters((v) => !v)}
                title="Filters"
                style={{ ...iconButtonStyle(false), width: 38, position: 'relative' }}
              >
                <i className="ti ti-adjustments-horizontal" />
                {activeFiltersCount > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: -6,
                      right: -6,
                      width: 18,
                      height: 18,
                      borderRadius: 999,
                      background: 'var(--accent)',
                      color: 'var(--text-inverse)',
                      fontSize: 10,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: '2px solid var(--panel-bg)',
                    }}
                  >
                    {activeFiltersCount}
                  </span>
                )}
              </button>

              <button onClick={clearAll} title="Clear" style={{ ...iconButtonStyle(false), width: 38 }}>
                <i className="ti ti-x" />
              </button>
            </div>

            {showFilters && (
              <div
                style={{
                  marginTop: 10,
                  padding: 12,
                  borderRadius: 14,
                  border: '1px solid var(--card-border)',
                  background: 'var(--card-bg)',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 10,
                }}
              >
                {[
                  { label: 'Company', value: filterCompany, onChange: setFilterCompany, placeholder: 'e.g. Acme Staffing' },
                  { label: 'Location', value: filterLocation, onChange: setFilterLocation, placeholder: 'State (e.g. TX) or name' },
                  { label: 'Specialization', value: filterSpecialization, onChange: setFilterSpecialization, placeholder: 'e.g. Java / Data' },
                ].map((f) => (
                  <div key={f.label}>
                    <div
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: 'var(--text-muted)',
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        marginBottom: 6,
                      }}
                    >
                      {f.label}
                    </div>
                    <input
                      value={f.value}
                      onChange={(e) => f.onChange(e.target.value)}
                      placeholder={f.placeholder}
                      style={{
                        width: '100%',
                        padding: '9px 10px',
                        borderRadius: 12,
                        border: '1px solid var(--card-border)',
                        background: 'var(--panel-bg)',
                        color: 'var(--text-primary)',
                        fontSize: 12,
                        outline: 'none',
                      }}
                    />
                  </div>
                ))}

                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                  <button
                    onClick={() => {
                      setFilterCompany('')
                      setFilterLocation('')
                      setFilterSpecialization('')
                    }}
                    style={{
                      padding: '9px 10px',
                      borderRadius: 12,
                      border: '1px solid var(--card-border)',
                      background: 'transparent',
                      color: 'var(--text-secondary)',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Reset filters
                  </button>
                  <button
                    onClick={() => setShowFilters(false)}
                    style={{
                      padding: '9px 12px',
                      borderRadius: 12,
                      border: '1px solid var(--card-border)',
                      background: 'var(--accent)',
                      color: 'var(--text-inverse)',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>

          <div style={{ flex: 1, overflow: 'auto' }}>
            {!query.trim() && !loading && !error && (
              <div style={{ height: '100%', display: 'grid', placeItems: 'center', padding: 22, textAlign: 'center', color: 'var(--text-muted)' }}>
                <div>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: 16,
                      background: 'var(--card-bg)',
                      border: '1px solid var(--card-border)',
                      display: 'grid',
                      placeItems: 'center',
                      margin: '0 auto 10px',
                    }}
                  >
                    <i className="ti ti-search" style={{ fontSize: 18 }} />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Search recruiters</div>
                  <div style={{ marginTop: 6, fontSize: 12 }}>Start typing a name, email, or company. Results come only from your database.</div>
                </div>
              </div>
            )}

            {!!error && (
              <div style={{ padding: 18, color: 'var(--text-muted)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <i className="ti ti-alert-triangle" style={{ color: 'var(--amber)', fontSize: 16 }} />
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Couldn’t load results</div>
                </div>
                <div style={{ marginTop: 6, fontSize: 12 }}>{error}</div>
                <div style={{ marginTop: 10, fontSize: 11 }}>
                  API: <span style={{ fontFamily: 'var(--mono)' }}>{API}</span>
                </div>
              </div>
            )}

            {query.trim() && !error && (
              <>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderBottom: '1px solid var(--card-border)',
                    background: 'var(--panel-bg)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 3,
                  }}
                >
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {loading ? 'Searching…' : `${searchResults.length} result${searchResults.length === 1 ? '' : 's'}`}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button onClick={() => fireSoon('Columns')} style={iconButtonStyle(false)} title="Columns (Coming soon)">
                      <i className="ti ti-columns-3" />
                    </button>
                    <button onClick={() => fireSoon('Sort')} style={iconButtonStyle(false)} title="Sort (Coming soon)">
                      <i className="ti ti-arrows-sort" />
                    </button>
                  </div>
                </div>

                {searchResults.length === 0 && !loading ? (
                  <div style={{ padding: 20, color: 'var(--text-muted)' }}>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>No matches found</div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>Try adjusting filters or refining the query.</div>
                  </div>
                ) : (
                  <div style={{ padding: 0 }}>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1.2fr 1.2fr 0.9fr 1.1fr 0.55fr',
                        gap: 10,
                        padding: '10px 14px',
                        borderBottom: '1px solid var(--card-border)',
                        background: 'var(--main-bg)',
                        position: 'sticky',
                        top: 44,
                        zIndex: 2,
                        fontSize: 10,
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        color: 'var(--text-muted)',
                        fontWeight: 800,
                      }}
                    >
                      <div>Name</div>
                      <div>Email</div>
                      <div>Phone</div>
                      <div>Company</div>
                      <div>Match Type</div>
                    </div>

                    <div>
                      {searchResults.map((r) => {
                        const active = selectedId === r.recruiter_id
                        const mt = matchTypeFor(r, query)
                        const badge = badgeForMatch(mt)
                        return (
                          <button
                            key={r.recruiter_id}
                            onClick={() => {
                              setSelectedDetail(null)
                              setSelectedDetailLoading(true)
                              setSelectedDetailError('')
                              setSelectedId(r.recruiter_id)
                            }}
                            style={{
                              width: '100%',
                              textAlign: 'left',
                              border: 'none',
                              borderBottom: '1px solid var(--card-border)',
                              background: active ? 'var(--accent-bg)' : 'transparent',
                              padding: 0,
                              cursor: 'pointer',
                            }}
                          >
                            <div
                              style={{
                                display: 'grid',
                                gridTemplateColumns: '1.2fr 1.2fr 0.9fr 1.1fr 0.55fr',
                                gap: 10,
                                padding: '12px 14px',
                                alignItems: 'center',
                                fontSize: 12,
                                color: 'var(--text-secondary)',
                              }}
                            >
                              <div style={{ color: 'var(--text-primary)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
                                <div
                                  style={{
                                    width: 28,
                                    height: 28,
                                    borderRadius: 10,
                                    border: '1px solid var(--card-border)',
                                    background: 'var(--card-bg)',
                                    display: 'grid',
                                    placeItems: 'center',
                                    fontSize: 11,
                                    fontWeight: 900,
                                    color: 'var(--text-primary)',
                                  }}
                                >
                                  {initials(r.recruiter_name)}
                                </div>
                                <div style={{ minWidth: 0 }}>
                                  <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.recruiter_name)}</div>
                                  <div style={{ marginTop: 2, fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {labelizeMatchReason(r.match_reason)} · Quality {String(r.quality_tier || 'unknown').toUpperCase()} · Score {r.relevance_score || 0}
                                  </div>
                                </div>
                              </div>
                              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.email)}</div>
                              <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.phone)}</div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
                                {r.company_name ? <CompanyLogo domain={r.website || r.email_pattern} name={r.company_name} size={24} style={{ flexShrink: 0, borderRadius: 4 }} /> : null}
                                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.company_name)}</span>
                              </div>
                              <div>
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    padding: '5px 8px',
                                    borderRadius: 999,
                                    border: `1px solid ${badge.border}`,
                                    background: badge.bg,
                                    color: badge.fg,
                                    fontSize: 10,
                                    fontWeight: 900,
                                    letterSpacing: '0.03em',
                                  }}
                                >
                                  {badge.label}
                                </span>
                              </div>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div
          style={{
            border: '1px solid var(--card-border)',
            borderRadius: 14,
            background: 'var(--panel-bg)',
            boxShadow: 'var(--shadow)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ padding: 14, borderBottom: '1px solid var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)' }}>Recruiter Details</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                onClick={() => {
                  primeEditState(selected)
                  setEditOpen(true)
                }}
                style={iconButtonStyle(!selected)}
                title={!selected ? 'Select a recruiter to edit' : 'Edit recruiter (locked)'}
                disabled={!selected}
              >
                <i className="ti ti-edit" />
              </button>
              <button
                onClick={() => {
                  if (!selected) return
                  const payload = [
                    selected.recruiter_name,
                    `Emails: ${selectedInsight.emails.join(', ') || safe(selected.email)}`,
                    `Phones: ${selectedInsight.phones.join(', ') || safe(selected.phone)}`,
                    `Company: ${safe(selected.company_name)}`,
                    `Address: ${selectedInsight.address}`,
                  ].join(' | ')
                  navigator.clipboard.writeText(payload)
                  setToast('Profile copied to clipboard')
                }}
                style={iconButtonStyle(!selected)}
                title="Copy Profile"
                disabled={!selected}
              >
                <i className="ti ti-copy" />
              </button>
              
              <button
                onClick={() => {
                  setSelectedId(null)
                  setSelectedDetail(null)
                  setSelectedDetailLoading(false)
                  setSelectedDetailError('')
                }}
                style={iconButtonStyle(!selected)}
                title="Close"
                disabled={!selected}
              >
                <i className="ti ti-x" />
              </button>
            </div>
          </div>

          {!selected ? (
            <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: 22, textAlign: 'center', color: 'var(--text-muted)' }}>
              <div>
                <div style={{ width: 56, height: 56, borderRadius: 18, border: '1px solid var(--card-border)', background: 'var(--card-bg)', display: 'grid', placeItems: 'center', margin: '0 auto 10px' }}>
                  <i className="ti ti-user-search" style={{ fontSize: 18 }} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)' }}>No recruiter selected</div>
                <div style={{ marginTop: 6, fontSize: 12 }}>Click a row to open the detail panel.</div>
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, overflow: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {selectedDetailLoading && (
                <div style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-muted)', fontSize: 12 }}>
                  Loading full recruiter profile from source data...
                </div>
              )}
              {selectedDetailError && (
                <div style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.08)', color: '#fca5a5', fontSize: 12 }}>
                  {selectedDetailError}
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                  <div style={{ width: 52, height: 52, borderRadius: 16, background: 'var(--text-primary)', color: 'var(--text-inverse)', display: 'grid', placeItems: 'center', fontSize: 18, fontWeight: 900 }}>
                    {initials(selected.recruiter_name)}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 16, fontWeight: 900, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {safe(selected.recruiter_name)}
                    </div>
                    <div style={{ marginTop: 3, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {selected.specialization && String(selected.specialization).trim() ? String(selected.specialization).trim() : ''}
                    </div>
                  </div>
                </div>

                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '6px 10px', borderRadius: 999, border: `1px solid ${matchBadge.border}`, background: matchBadge.bg, color: matchBadge.fg, fontSize: 10, fontWeight: 900, letterSpacing: '0.03em', whiteSpace: 'nowrap' }}>
                  {matchBadge.label} MATCH
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <button onClick={() => fireSoon('Share profile')} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--accent)', color: 'var(--text-inverse)', fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
                  <i className="ti ti-share-2" style={{ marginRight: 8 }} />
                  Share profile
                </button>
                <button onClick={() => fireSoon('Open timeline')} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
                  <i className="ti ti-activity" style={{ marginRight: 8 }} />
                  Activity (soon)
                </button>
              </div>

              <div style={{ border: '1px solid var(--card-border)', borderRadius: 14, padding: 12, background: 'var(--card-bg)' }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Contact info</div>
                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'start' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Emails</div>
                    <div style={{ display: 'grid', gap: 6 }}>
                      {contactSlots(selectedInsight.emails, selected.email).map((email, index) => (
                        <div
                          key={`email-slot-${index}`}
                          style={{
                            fontSize: 12,
                            color: email ? 'var(--text-primary)' : 'var(--text-muted)',
                            fontWeight: 700,
                            minHeight: 18,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {index + 1}. {email}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'start' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Phones</div>
                    <div style={{ display: 'grid', gap: 6 }}>
                      {contactSlots(selectedInsight.phones, selected.phone).map((phone, index) => (
                        <div
                          key={`phone-slot-${index}`}
                          style={{
                            fontSize: 12,
                            color: phone ? 'var(--text-primary)' : 'var(--text-muted)',
                            fontWeight: 700,
                            minHeight: 18,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {index + 1}. {phone}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>LinkedIn</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.linkedin)}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Created</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700 }}>{selectedInsight.createdAt}</div>
                  </div>
                </div>
              </div>

              <div style={{ border: '1px solid var(--card-border)', borderRadius: 14, padding: 12, background: 'var(--card-bg)' }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Company / firm analysis</div>

                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Company</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                      {selected.company_name ? <CompanyLogo domain={selected.website || selected.email_pattern} name={selected.company_name} size={32} style={{ flexShrink: 0, borderRadius: 4 }} /> : null}
                      <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 800, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(selected.company_name)}</span>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>Address</div>
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{selectedInsight.address}</div>
                  </div>
                  
                  {selected?.state_source && (
                    <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 10, alignItems: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>State Inf.</div>
                      <div style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 700 }}>
                        {selected.state_source} <span style={{ color: selected.state_confidence === 'high' ? 'var(--success)' : 'var(--warning)', marginLeft: 4 }}>({selected.state_confidence})</span>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 4 }}>
                    <div style={{ border: '1px dashed var(--card-border)', borderRadius: 12, padding: 10, background: 'var(--panel-bg)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Completeness</div>
                      <div style={{ marginTop: 8, fontSize: 14, fontWeight: 900, color: selected?.completeness_score >= 80 ? 'var(--success)' : selected?.completeness_score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                        {selected?.completeness_score ?? 0}%
                      </div>
                    </div>
                    <div style={{ border: '1px dashed var(--card-border)', borderRadius: 12, padding: 10, background: 'var(--panel-bg)', borderColor: selected?.needs_review ? 'rgba(245,158,11,0.4)' : 'var(--card-border)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 800, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Data Quality</div>
                      <div style={{ marginTop: 8, fontSize: 12, fontWeight: 700, color: selected?.needs_review ? '#d97706' : 'var(--success)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {selected?.needs_review ? (selected?.review_reason || 'Needs Review') : 'Verified Clean'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <details style={{ border: '1px solid var(--card-border)', borderRadius: 14, background: 'var(--card-bg)', overflow: 'hidden' }}>
                <summary style={{ fontSize: 10, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', padding: 12, cursor: 'pointer', outline: 'none', background: 'var(--panel-bg)' }}>
                  Raw source text / needs review
                </summary>
                <div style={{ padding: 12, borderTop: '1px solid var(--card-border)', display: 'grid', gap: 8 }}>
                  {selected?.notes ? (
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.6 }}>
                      {selected.notes}
                    </div>
                  ) : null}
                  {selectedInsight.extras.length ? selectedInsight.extras.map((item, index) => (
                    <div key={`${item.key}-${index}`} style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10, alignItems: 'start' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'capitalize' }}>{item.key}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.5, wordBreak: 'break-all' }}>{item.value}</div>
                    </div>
                  )) : null}
                  {!selected?.notes && !selectedInsight.extras.length ? (
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>No additional captured details available.</div>
                  ) : null}
                </div>
              </details>
            </div>
          )}
        </div>
      </div>

      {toast && (
        <div style={{ position: 'fixed', right: 18, bottom: 18, background: 'var(--text-primary)', color: 'var(--text-inverse)', padding: '10px 12px', borderRadius: 12, fontSize: 12, zIndex: 1500, boxShadow: 'var(--shadow-lg)' }}>
          {toast}
        </div>
      )}

      {editOpen && (
        <div
          onClick={() => setEditOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 2000, display: 'grid', placeItems: 'center', padding: 16 }}
        >
          <div
            className="card"
            onClick={(e) => e.stopPropagation()}
            style={{ width: '100%', maxWidth: 620, padding: 16, borderRadius: 18, background: 'var(--card-bg)', border: '1px solid var(--card-border)', boxShadow: 'var(--shadow-lg)' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 900, color: 'var(--text-primary)' }}>
                Edit Recruiter
              </div>
              <button onClick={() => setEditOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <i className="ti ti-x" />
              </button>
            </div>

            {!editAuthed ? (
              <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
                <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Editing is locked. Enter admin PIN to unlock editing.
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <input
                    value={editPin}
                    onChange={(e) => setEditPin(e.target.value)}
                    type="password"
                    placeholder="Admin PIN"
                    autoFocus
                    style={{ flex: 1, padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none' }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        ;(async () => {
                          setEditError('')
                          try {
                            await login(editPin, true)
                            setEditAuthed(true)
                          } catch (err) {
                            setEditError(getErrorMessage(err, 'Invalid PIN'))
                          }
                        })()
                      }
                    }}
                  />
                  <button
                    className="btn-primary"
                    onClick={async () => {
                      setEditError('')
                      try {
                        await login(editPin, true)
                        setEditAuthed(true)
                      } catch (err) {
                        setEditError(getErrorMessage(err, 'Invalid PIN'))
                      }
                    }}
                    style={{ borderRadius: 12, padding: '10px 12px', fontWeight: 900 }}
                  >
                    <i className="ti ti-lock-open" /> Unlock
                  </button>
                </div>
                {editError && <div style={{ fontSize: 12, color: '#f87171' }}>{editError}</div>}
              </div>
            ) : (
              <div style={{ marginTop: 14, display: 'grid', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {[
                    ['Full name', 'recruiter_name'],
                    ['Email', 'email'],
                    ['Email 2', 'email2'],
                    ['Email 3', 'email3'],
                    ['Email 4', 'email4'],
                    ['Phone', 'phone'],
                    ['Phone 2', 'phone2'],
                    ['Phone 3', 'phone3'],
                    ['Phone 4', 'phone4'],
                    ['LinkedIn', 'linkedin'],
                    ['Location', 'location'],
                    ['Specialization', 'specialization'],
                  ].map(([label, key]) => (
                    <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ fontSize: 10.5, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</div>
                      <input
                        value={editForm[key]}
                        onChange={(e) => setEditForm((p) => ({ ...p, [key]: e.target.value }))}
                        style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none' }}
                      />
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: 10.5, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Notes</div>
                  <textarea
                    value={editForm.notes}
                    onChange={(e) => setEditForm((p) => ({ ...p, notes: e.target.value }))}
                    style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none', minHeight: 90, resize: 'vertical' }}
                  />
                </div>

                {editError && <div style={{ fontSize: 12, color: '#f87171' }}>{editError}</div>}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                  <button onClick={() => setEditOpen(false)} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontWeight: 900, cursor: 'pointer' }}>
                    Cancel
                  </button>
                  <button
                    className="btn-primary"
                    disabled={editSaving || !selected?.recruiter_id}
                    onClick={async () => {
                      if (!selected?.recruiter_id) return
                      setEditSaving(true)
                      setEditError('')
                      try {
                        const payload = {
                          recruiter_name: editForm.recruiter_name || null,
                          email: editForm.email || null,
                          email2: editForm.email2 || null,
                          email3: editForm.email3 || null,
                          email4: editForm.email4 || null,
                          phone: editForm.phone || null,
                          phone2: editForm.phone2 || null,
                          phone3: editForm.phone3 || null,
                          phone4: editForm.phone4 || null,
                          linkedin: editForm.linkedin || null,
                          location: editForm.location || null,
                          specialization: editForm.specialization || null,
                          notes: editForm.notes || null,
                        }
                        const { data } = await api.put(`/recruiters/${selected.recruiter_id}`, payload)
                        // Update UI immediately
                        setSearchResults((prev) => prev.map((r) => (r.recruiter_id === selected.recruiter_id ? { ...r, ...data } : r)))
                        setSelectedDetail(data)
                        setToast('Recruiter updated')
                        setTimeout(() => setToast(''), 1400)
                        setEditOpen(false)
                      } catch (err) {
                        setEditError(getErrorMessage(err, 'Update failed'))
                      } finally {
                        setEditSaving(false)
                      }
                    }}
                    style={{ borderRadius: 12, padding: '10px 12px', fontWeight: 900, opacity: (editSaving || !selected?.recruiter_id) ? 0.75 : 1 }}
                  >
                    <i className="ti ti-device-floppy" /> {editSaving ? 'Saving…' : 'Save changes'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
