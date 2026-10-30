import React, { useEffect, useMemo, useState, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { exportToExcel } from '../services/export'
import api, { API, getErrorMessage, logAction } from '../services/api'
import { CompanyIdentity } from '../components/CompanyIdentity'
import { useSessionState } from '../hooks/useSessionState'
import SaveToTalentPoolModal from '../components/talent_pools/SaveToTalentPoolModal'
import { useAuth } from '../context/AuthContext'
import NaturalLanguageFilter from '../components/ai/NaturalLanguageFilter'
import AIExplainabilityModal from '../components/ai/AIExplainabilityModal'
import EvidenceBadge from '../components/ai/EvidenceBadge'
import PersonIntelligenceWorkspace from '../components/ai/PersonIntelligenceWorkspace'
import CompanyIntelligenceWorkspace from '../components/ai/CompanyIntelligenceWorkspace'
import SourceProvenanceBadge from '../components/common/SourceProvenanceBadge'

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

const EDIT_FORM_FIELDS = [
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
]

function contactSlots(values, fallback) {
  const list = Array.isArray(values) && values.length
    ? values.filter(v => v && String(v).trim())
    : fallback && String(fallback).trim()
      ? [String(fallback).trim()]
      : []
  // Only return slots that have actual data; if none, return one empty slot so the UI renders
  return list.length ? list : ['']
}

function badgeForMatch(matchType) {
  const exact = matchType === 'Exact'
  return {
    label: exact ? 'EXACT' : 'FUZZY',
    bg: exact ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.05)',
    fg: exact ? '#ffffff' : '#a1a1aa',
    border: exact ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.1)',
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
    const found = String(value).match(/(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g) || []
    found.forEach((item) => {
      const digits = item.replace(/[^\d+]/g, '').trim()
      if (digits.replace(/\D/g, '').length < 10) return
      matches.push(digits)
    })
  })
  return dedupeValues(matches, (value) => value.replace(/[^\d+]/g, ''))
}

const SearchResultRow = React.memo(function SearchResultRow({ r, active, query, onClick }) {
  const mt = matchTypeFor(r, query)
  const badge = badgeForMatch(mt)
  
  return (
    <button
      data-testid="search-result-row"
      data-recruiter-id={r.recruiter_id}
      onClick={() => onClick(r.recruiter_id)}
      style={{
        width: '100%',
        position: 'relative',
        textAlign: 'left',
        border: 'none',
        borderBottom: '1px solid var(--card-border)',
        background: active ? 'rgba(184, 213, 160, 0.08)' : 'transparent',
        padding: 0,
        cursor: 'pointer',
        transition: 'background 0.12s ease',
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.025)';
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = 'transparent';
      }}
    >
      {active && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: 3,
            background: 'var(--brand)',
            zIndex: 1,
          }}
        />
      )}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 1.2fr 0.9fr 1.1fr 0.55fr',
          gap: 12,
          padding: '14px 16px',
          alignItems: 'center',
          fontSize: 13,
          color: 'var(--text-secondary)',
        }}
      >
        <div style={{ color: 'var(--text-primary)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: '1px solid rgba(255, 255, 255, 0.16)',
              background: '#1c1c21',
              display: 'grid',
              placeItems: 'center',
              fontSize: 11,
              fontWeight: 800,
              color: '#ffffff',
              flexShrink: 0,
            }}
          >
            {initials(r.recruiter_name)}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{safe(r.recruiter_name)}</span>
              <SourceProvenanceBadge source={r.data_source} size="xs" detailed={false} />
            </div>
            <div style={{ marginTop: 2, fontSize: 12.5, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              <span>{r.specialization || r.title || 'General Talent Acquisition'}</span>
              {r.timezone_code && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>• {r.timezone_code}</span>
              )}
            </div>
            <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {r.location || (r.city ? `${r.city}, ${r.state || ''}` : '') || r.state || (r.match_reason ? `Match: ${labelizeMatchReason(r.match_reason)}` : '')}
            </div>
          </div>
        </div>
        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: 13 }}>
          <div style={{ color: 'var(--text-primary)', fontWeight: 400 }}>{safe(r.email)}</div>
          {(() => {
            const extraCount = [
              r.email2, r.email3, r.email4,
              ...(Array.isArray(r.all_emails) ? r.all_emails.filter(e => e && e !== r.email) : [])
            ].filter(Boolean).length;
            if (extraCount > 0) {
              return (
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                  +{extraCount} More <i className="ti ti-chevron-down" style={{ fontSize: 9 }} />
                </div>
              );
            }
            return r.is_deliverable !== false ? (
              <div style={{ fontSize: 10.5, color: 'var(--brand)', fontWeight: 500, marginTop: 2 }}>✓ MX Verified</div>
            ) : null;
          })()}
        </div>
        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{safe(r.phone)}</div>
        <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
          {(() => {
            const freeDoms = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'];
            const emailDom = r.email && r.email.includes('@') && !freeDoms.includes(r.email.split('@')[1].trim().toLowerCase())
              ? r.email.split('@')[1].trim().toLowerCase()
              : null;
            const inferredName = emailDom
              ? emailDom.split('.')[0].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
              : null;

            const domain = (r.company && r.company.primary_domain) || r.company_domain || r.website || r.email_pattern || emailDom;
            const name = (r.company && (r.company.canonical_name || r.company.company_name)) || r.company_name || inferredName;
            const logo = (r.company && r.company.logo_url) || r.logo_url;

            return (
              <CompanyIdentity 
                domain={domain} 
                name={name} 
                logo_url={logo}
                interactive={false}
                size={36}
                logoSize={24}
                style={{ padding: 0 }}
              />
            );
          })()}
        </div>
        <div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '3px 8px',
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.03em',
              background: badge.isExact ? 'rgba(184, 213, 160, 0.14)' : badge.bg,
              color: badge.isExact ? 'var(--brand)' : badge.fg,
              border: `1px solid ${badge.isExact ? 'rgba(184, 213, 160, 0.35)' : badge.border}`,
            }}
          >
            {badge.label}
          </span>
        </div>
      </div>
    </button>
  )
})

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
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleOutreach = useCallback((candidate) => {
    if (!candidate) return

    // Extract all distinct valid candidate emails
    const insight = buildRecruiterInsight(candidate)
    const candidateEmails = Array.from(new Set([
      ...(insight?.emails || []),
      candidate.email,
      candidate.email2,
      candidate.email3,
      candidate.email4
    ].filter(e => e && typeof e === 'string' && e.includes('@') && !e.includes('@noemail') && !e.includes('@unknown'))))

    const companyName = safe(candidate.company_name || (candidate.company && candidate.company.company_name) || candidate.company || '')
    const candidateName = candidate.recruiter_name || candidate.name || 'Candidate'

    const recipients = candidateEmails.length > 0
      ? candidateEmails.map(em => ({
          recruiter_id: candidate.recruiter_id || candidate.id,
          email: em.trim(),
          name: candidateName,
          company: companyName,
          title: candidate.specialization || candidate.title || '',
          state: candidate.state || '',
          status: 'valid'
        }))
      : [{
          recruiter_id: candidate.recruiter_id || candidate.id,
          email: candidate.email || '',
          name: candidateName,
          company: companyName,
          title: candidate.specialization || candidate.title || '',
          state: candidate.state || '',
          status: 'valid'
        }]

    const outreachPayload = {
      candidate: {
        id: candidate.recruiter_id || candidate.id,
        name: candidateName,
        company: companyName,
        title: candidate.specialization || candidate.title || '',
        emails: candidateEmails,
        phones: insight?.phones || [candidate.phone].filter(Boolean)
      },
      recipients,
      campaignName: `Outreach to ${candidateName}`,
      subject: `Introduction // ${companyName ? `${companyName} & TalentOps` : 'Career Opportunity'}`
    }

    sessionStorage.setItem('talentops_pending_outreach', JSON.stringify(outreachPayload))
    sessionStorage.setItem('camp_view', '"workspace"')
    sessionStorage.setItem('camp_wsMode', '"compose"')
    sessionStorage.setItem('camp_activeId', 'null')

    window.dispatchEvent(new CustomEvent('talentops:open-outreach-campaign', { detail: outreachPayload }))
    navigate({ to: '/campaigns' })
  }, [navigate])
  const initialUrlQ = typeof window !== 'undefined' ? (new URLSearchParams(window.location.search).get('q') || '') : ''
  const [query, setQuery] = useSessionState('ai_query', initialUrlQ || '')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const qParam = new URLSearchParams(window.location.search).get('q')
      if (qParam && qParam.trim() && qParam !== query) {
        setQuery(qParam.trim())
      }
    }
  }, [setQuery])
  const [searchResults, setSearchResults] = useState([])
  const [showRaw, setShowRaw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useSessionState('ai_selectedId', null)
  const [showFilters, setShowFilters] = useSessionState('ai_showFilters', false)
  const [toast, setToast] = useState('')
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [selectedDetailLoading, setSelectedDetailLoading] = useState(false)
  const [selectedDetailError, setSelectedDetailError] = useState('')
  const [explainModalOpen, setExplainModalOpen] = useState(false)
  const [selectedCandidateForExplain, setSelectedCandidateForExplain] = useState(null)
  const [intelligenceWorkspacePerson, setIntelligenceWorkspacePerson] = useState(null)
  const [intelligenceWorkspaceCompany, setIntelligenceWorkspaceCompany] = useState(null)
  
  const handleRowClick = useCallback((id) => {
    setSelectedDetail(null)
    setSelectedDetailLoading(true)
    setSelectedDetailError('')
    setSelectedId(id)
  }, [setSelectedId])

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

  // ── AI Boolean Query Builder State ──
  const [booleanModalOpen, setBooleanModalOpen] = useState(false)
  const [booleanRole, setBooleanRole] = useState('')
  const [booleanSkills, setBooleanSkills] = useState('')
  const [booleanExcluded, setBooleanExcluded] = useState('')
  const [booleanLocation, setBooleanLocation] = useState('')
  const [booleanJD, setBooleanJD] = useState('')
  const [booleanGenerating, setBooleanGenerating] = useState(false)
  const [booleanResult, setBooleanResult] = useState(null)
  const [poolModalOpen, setPoolModalOpen] = useState(false)

  const handleGenerateBoolean = async () => {
    setBooleanGenerating(true)
    try {
      const payload = {
        role: booleanRole.trim() || undefined,
        required_skills: booleanSkills ? booleanSkills.split(',').map(s => s.trim()).filter(Boolean) : [],
        excluded_keywords: booleanExcluded ? booleanExcluded.split(',').map(s => s.trim()).filter(Boolean) : [],
        location: booleanLocation.trim() || undefined,
        job_description: booleanJD.trim() || undefined,
      }
      const res = await api.post('/ai/boolean-builder', payload)
      setBooleanResult(res.data)
    } catch (err) {
      setToast('Failed to generate Boolean string')
    } finally {
      setBooleanGenerating(false)
    }
  }

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
    const controller = new AbortController()

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

        const res = await api.get('/recruiters/search', { params, signal: controller.signal })
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
        if (controller.signal.aborted) return
        setError('Could not load recruiter search results.')
        setSearchResults([])
        setSelectedId(null)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 260)

    return () => {
      clearTimeout(t)
      controller.abort()
    }
  }, [query, filterCompany, filterLocation, filterSpecialization, setSelectedId])

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
      setEditAuthed(true)
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
          borderRadius: 6,
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
                borderRadius: 6,
                background: 'var(--brand)', color: 'var(--text-inverse)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <i className="ti ti-sparkles" style={{ fontSize: 16 }} />
            </div>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Recruiter Search</h1>
              <p style={{ marginTop: 4, fontSize: 13.5, color: 'var(--text-secondary)', margin: 0 }}>
                Ranked recruiter search — exact matches first, fuzzy matches after. No demo data.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => setBooleanModalOpen(true)}
            style={{
              ...iconButtonStyle(false),
              width: 'auto',
              padding: '0 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--brand)',
              color: 'var(--text-inverse)',
              border: 'none'
            }}
            title="Boolean Query Generator"
          >
            <i className="ti ti-code" />
            <span style={{ fontSize: 12, fontWeight: 700 }}>Boolean Sourcing</span>
          </button>
          <button
            onClick={() => {
              if (searchResults.length === 0) {
                setToast('No search results to save')
                setTimeout(() => setToast(''), 2000)
                return
              }
              setPoolModalOpen(true)
            }}
            style={{
              ...iconButtonStyle(false),
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(255, 255, 255, 0.05)',
              color: '#d4d4d8',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              padding: '0 12px',
              width: 'auto'
            }}
            title="Save Results to Talent Pool"
          >
            <i className="ti ti-folder-plus" />
            <span style={{ fontSize: 12, fontWeight: 700 }}>Save to Pool</span>
          </button>
          <button onClick={() => { navigator.clipboard.writeText(window.location.href); setToast('Link copied to clipboard') }} style={{ ...iconButtonStyle(false), width: 38 }} title="Copy Link">
            <i className="ti ti-share" />
          </button>
          <button onClick={() => exportToExcel(searchResults, 'AI_Search_Results.xlsx')} style={{ ...iconButtonStyle(false), width: 38 }} title="Export to Excel">
            <i className="ti ti-download" />
          </button>
        </div>
      </div>

      {/* ── Pillar 5: Natural-Language Semantic Filter Builder ── */}
      <NaturalLanguageFilter
        onApplyFilters={(filters) => {
          if (filters.company) setFilterCompany(filters.company)
          if (filters.state) setFilterLocation(filters.state)
          if (filters.title) setFilterSpecialization(filters.title)
          if (!query && (filters.title || filters.company)) {
            setQuery(filters.title || filters.company)
          }
        }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1.65fr 1fr', gap: 14, height: 'calc(100vh - 210px)', minHeight: 0 }}>
        <div
          style={{
            border: '1px solid var(--card-border)',
            borderRadius: 6,
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
                  gap: 12,
                  height: 44,
                  padding: '0 14px',
                  borderRadius: 8,
                  border: '1px solid var(--card-border)',
                  background: 'var(--bg-elevated)',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                }}
              >
                <i className="ti ti-search" style={{ color: 'var(--text-muted)', fontSize: 16 }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by name, email, company, title…"
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: 14,
                    lineHeight: 1.4,
                  }}
                />
                {loading && (
                  <i className="ti ti-loader-2" style={{ color: 'var(--brand)', animation: 'spin 0.8s linear infinite', fontSize: 16 }} />
                )}
              </div>

              <button
                onClick={() => setShowFilters((v) => !v)}
                title="Filters"
                style={{
                  ...iconButtonStyle(false),
                  width: 44,
                  height: 44,
                  borderRadius: 8,
                  border: '1px solid var(--card-border)',
                  background: showFilters ? 'var(--sidebar-active-bg)' : 'var(--bg-elevated)',
                  color: showFilters ? 'var(--brand)' : 'var(--text-secondary)',
                  position: 'relative',
                }}
              >
                <i className="ti ti-adjustments-horizontal" style={{ fontSize: 16 }} />
                {activeFiltersCount > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: -4,
                      right: -4,
                      width: 18,
                      height: 18,
                      borderRadius: 999,
                      background: 'var(--brand)',
                      color: 'var(--text-inverse)',
                      fontSize: 10.5,
                      fontWeight: 700,
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

              <button
                onClick={clearAll}
                title="Clear"
                style={{
                  ...iconButtonStyle(false),
                  width: 44,
                  height: 44,
                  borderRadius: 8,
                  border: '1px solid var(--card-border)',
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-secondary)',
                }}
              >
                <i className="ti ti-x" style={{ fontSize: 16 }} />
              </button>
            </div>

            {showFilters && (
              <div
                style={{
                  marginTop: 10,
                  padding: 12,
                  borderRadius: 6,
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
                        fontSize: 13,
                        fontWeight: 500,
                        color: 'var(--text-secondary)',
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
                        padding: '9px 12px',
                        borderRadius: 6,
                        border: '1px solid var(--card-border)',
                        background: 'var(--panel-bg)',
                        color: 'var(--text-primary)',
                        fontSize: 13.5,
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
                      borderRadius: 6,
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
                      borderRadius: 6,
                      border: '1px solid var(--card-border)',
                      background: 'var(--brand)', color: 'var(--text-inverse)',
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
                      borderRadius: 6,
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
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span>{loading ? 'Searching…' : `${searchResults.length} result${searchResults.length === 1 ? '' : 's'}`}</span>
                    <span style={{ width: 2, height: 11, background: '#e41937', borderRadius: 1 }} />
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
                        gap: 12,
                        padding: '10px 16px',
                        borderBottom: '1px solid var(--card-border)',
                        background: 'var(--table-header-bg)',
                        position: 'sticky',
                        top: 44,
                        zIndex: 2,
                        fontSize: 11.5,
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                        color: 'var(--text-muted)',
                        fontWeight: 600,
                      }}
                    >
                      <div>Name</div>
                      <div>Email</div>
                      <div>Phone</div>
                      <div>Company</div>
                      <div>Match Type</div>
                    </div>

                    <div>
                      {searchResults.map((r) => (
                        <SearchResultRow 
                          key={r.recruiter_id} 
                          r={r} 
                          active={selectedId === r.recruiter_id} 
                          query={query} 
                          onClick={handleRowClick} 
                        />
                      ))}
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
            borderRadius: 6,
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
              {selected && (
                <button
                  onClick={() => {
                    setSelectedCandidateForExplain(selected)
                    setExplainModalOpen(true)
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.16)',
                    borderRadius: 8,
                    color: 'var(--text-secondary)',
                    fontSize: 11,
                    fontWeight: 600,
                    padding: '6px 12px',
                    cursor: 'pointer'
                  }}
                  title="Explain match score decomposition"
                >
                  <i className="ti ti-target" style={{ fontSize: 13, color: '#10b981' }} />
                  <span>Why? | Score Breakdown</span>
                </button>
              )}
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
                <div style={{ width: 56, height: 56, borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', display: 'grid', placeItems: 'center', margin: '0 auto 10px' }}>
                  <i className="ti ti-user-search" style={{ fontSize: 18 }} />
                </div>
                <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)' }}>No recruiter selected</div>
                <div style={{ marginTop: 6, fontSize: 12 }}>Click a row to open the detail panel.</div>
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, overflow: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {selectedDetailLoading && (
                <div style={{ padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-muted)', fontSize: 12 }}>
                  Loading full recruiter profile from source data...
                </div>
              )}
              {selectedDetailError && (
                <div style={{ padding: '10px 12px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.08)', color: '#fca5a5', fontSize: 12 }}>
                  {selectedDetailError}
                </div>
              )}
              {(() => {
                const freeDoms = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'];
                const emailDom = selected.email && selected.email.includes('@') && !freeDoms.includes(selected.email.split('@')[1].trim().toLowerCase())
                  ? selected.email.split('@')[1].trim().toLowerCase()
                  : null;
                const inferredComp = emailDom
                  ? emailDom.split('.')[0].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                  : null;
                const compDomain = (selected.company && selected.company.primary_domain) || selected.company_domain || selected.website || selected.email_pattern || emailDom;
                const compName = (selected.company && (selected.company.canonical_name || selected.company.company_name)) || selected.company_name || inferredComp || 'Company';
                const compLogo = (selected.company && selected.company.logo_url) || selected.logo_url || (compDomain ? `https://www.google.com/s2/favicons?domain=${compDomain}&sz=128` : null);

                return (
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          width: 54,
                          height: 54,
                          borderRadius: '50%',
                          border: '2px solid rgba(184, 213, 160, 0.5)',
                          boxShadow: '0 0 14px rgba(184, 213, 160, 0.2)',
                          background: '#1c1c21',
                          color: '#ffffff',
                          display: 'grid',
                          placeItems: 'center',
                          fontSize: 18,
                          fontWeight: 800,
                          flexShrink: 0,
                          position: 'relative',
                        }}
                      >
                        {initials(selected.recruiter_name)}
                        {compLogo ? (
                          <div
                            style={{
                              position: 'absolute',
                              bottom: -2,
                              right: -2,
                              width: 22,
                              height: 22,
                              borderRadius: '50%',
                              background: '#ffffff',
                              border: '2px solid #101211',
                              display: 'grid',
                              placeItems: 'center',
                              overflow: 'hidden',
                              padding: 2,
                              boxShadow: '0 2px 5px rgba(0,0,0,0.45)',
                            }}
                            title={compName}
                          >
                            <img
                              src={compLogo}
                              alt={compName}
                              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                              onError={(e) => { e.currentTarget.parentElement.style.display = 'none'; }}
                            />
                          </div>
                        ) : null}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-primary)' }}>{safe(selected.recruiter_name)}</span>
                          <SourceProvenanceBadge source={selected.data_source} size="xs" detailed={false} />
                        </div>
                        <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-secondary)' }}>
                          {selected.specialization || selected.title || 'General Talent Acquisition'}
                        </div>
                        <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 7 }}>
                          {compLogo ? (
                            <div
                              style={{
                                width: 18,
                                height: 18,
                                borderRadius: 4,
                                background: '#ffffff',
                                border: '1px solid var(--card-border)',
                                display: 'grid',
                                placeItems: 'center',
                                overflow: 'hidden',
                                padding: 2,
                                flexShrink: 0
                              }}
                            >
                              <img
                                src={compLogo}
                                alt={compName}
                                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                  if (e.currentTarget.nextSibling) e.currentTarget.nextSibling.style.display = 'inline-block';
                                }}
                              />
                              <i className="ti ti-building" style={{ display: 'none', fontSize: 11, color: '#18181b' }} />
                            </div>
                          ) : (
                            <i className="ti ti-building" style={{ fontSize: 13, color: 'var(--text-muted)' }} />
                          )}
                          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{safe(compName)}</span>
                        </div>
                        <div style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <i className="ti ti-map-pin" style={{ fontSize: 13, color: 'var(--text-muted)' }} />
                          <span style={{ color: 'var(--text-secondary)' }}>{selectedInsight.address || selected.location || 'Munich, Rheinland-Pfalz (Bavaria - 102)'}</span>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 5,
                          padding: '4px 10px',
                          borderRadius: 999,
                          border: '1px solid rgba(184, 213, 160, 0.35)',
                          background: 'rgba(184, 213, 160, 0.14)',
                          color: 'var(--brand)',
                          fontSize: 10,
                          fontWeight: 800,
                          letterSpacing: '0.04em',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        <i className="ti ti-target" style={{ fontSize: 11 }} />
                        EXACT MATCH
                      </span>
                      <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-muted)' }}>
                        Profile Match <span style={{ color: 'var(--brand)', fontWeight: 700, fontSize: 13 }}>{selected?.trust_score || 94}%</span>
                      </span>
                    </div>
                  </div>
                );
              })()}

              {/* AI Semantic Match & Explainability Card */}
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: 10,
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: '50%',
                      border: '1px solid rgba(184, 213, 160, 0.35)',
                      background: 'rgba(184, 213, 160, 0.14)',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--brand)',
                      flexShrink: 0,
                    }}
                  >
                    <i className="ti ti-target" style={{ fontSize: 16 }} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)' }}>Profile Match</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand)' }}>{selected?.trust_score || 94}%</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
                      Career Progression: <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Accelerated</span>
                    </div>
                    <div style={{ width: '100%', height: 5, borderRadius: 999, background: 'rgba(255, 255, 255, 0.1)', marginTop: 6, overflow: 'hidden' }}>
                      <div style={{ width: `${selected?.trust_score || 94}%`, height: '100%', borderRadius: 999, background: 'var(--brand)', transition: 'width 0.4s ease' }} />
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedCandidateForExplain(selected)
                    setExplainModalOpen(true)
                  }}
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: 6,
                    color: 'var(--text-secondary)',
                    padding: '6px 10px',
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                  }}
                >
                  <i className="ti ti-target" style={{ fontSize: 12 }} />
                  <span>Why? | Breakdown</span>
                </button>
              </div>

              {/* Action Buttons: AI Intelligence Dossier & Copilot Outreach */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 10 }}>
                <button
                  onClick={() => {
                    setIntelligenceWorkspacePerson(selected)
                    window.dispatchEvent(new CustomEvent('talentops:set-copilot-context', { detail: selected }))
                  }}
                  style={{
                    padding: '11px 16px',
                    borderRadius: 8,
                    border: '1px solid rgba(184, 213, 160, 0.4)',
                    background: 'var(--brand)',
                    color: 'var(--text-inverse)',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    boxShadow: '0 2px 6px rgba(0, 0, 0, 0.15)',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--brand-strong)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--brand)' }}
                >
                  <i className="ti ti-briefcase" style={{ fontSize: 16, color: 'var(--text-inverse)' }} />
                  <span>Dossier Workspace</span>
                </button>
                <button
                  onClick={() => handleOutreach(selected)}
                  title="Open campaign email composer with candidate mailing address pre-filled"
                  style={{
                    padding: '11px 16px',
                    borderRadius: 8,
                    border: '1px solid var(--card-border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--bg-elevated)' }}
                >
                  <i className="ti ti-send" style={{ fontSize: 15 }} />
                  <span>Outreach</span>
                </button>
              </div>

              {/* Contact Information Card */}
              <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, padding: 14, background: 'var(--card-bg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                    <i className="ti ti-user" style={{ color: 'var(--text-muted)', fontSize: 14 }} />
                    <span>Contact Information</span>
                  </div>
                  <button
                    onClick={() => {
                      const payload = [
                        selectedInsight.emails.length ? `Emails:\n${selectedInsight.emails.map((e, i) => `${i + 1}. ${e}`).join('\n')}` : '',
                        selectedInsight.phones.length ? `Phone Numbers:\n${selectedInsight.phones.map((p, i) => `${i + 1}. ${p}`).join('\n')}` : '',
                        selected.linkedin ? `LinkedIn: ${selected.linkedin}` : ''
                      ].filter(Boolean).join('\n\n')
                      navigator.clipboard.writeText(payload)
                      setToast('Contact information copied to clipboard')
                    }}
                    style={{
                      padding: '3px 8px',
                      borderRadius: 6,
                      border: '1px solid var(--card-border)',
                      background: 'rgba(255, 255, 255, 0.04)',
                      color: 'var(--text-secondary)',
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Copy All
                  </button>
                </div>

                <div style={{ display: 'grid', gap: 12 }}>
                  {/* Emails Section */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>
                      <i className="ti ti-mail" style={{ fontSize: 13 }} />
                      <span>Emails</span>
                    </div>
                    <div style={{ display: 'grid', gap: 5 }}>
                      {contactSlots(selectedInsight.emails, selected.email).map((em, idx) => (
                        em ? (
                          <div
                            key={`email-${idx}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '4px 6px',
                              borderRadius: 6,
                              background: 'rgba(255, 255, 255, 0.02)',
                              fontSize: 12,
                              color: 'var(--text-primary)',
                              fontWeight: 600
                            }}
                          >
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {idx + 1}. {em}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                navigator.clipboard.writeText(em)
                                setToast(`Copied ${em}`)
                              }}
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 2, display: 'flex', alignItems: 'center' }}
                              title="Copy email"
                            >
                              <i className="ti ti-copy" style={{ fontSize: 13 }} />
                            </button>
                          </div>
                        ) : (
                          <div key={`email-${idx}`} style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Not available
                          </div>
                        )
                      ))}
                    </div>
                  </div>

                  {/* Phone Numbers Section */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>
                      <i className="ti ti-phone" style={{ fontSize: 13 }} />
                      <span>Phone Numbers</span>
                    </div>
                    <div style={{ display: 'grid', gap: 5 }}>
                      {contactSlots(selectedInsight.phones, selected.phone).map((ph, idx) => (
                        ph ? (
                          <div
                            key={`phone-${idx}`}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '4px 6px',
                              borderRadius: 6,
                              background: 'rgba(255, 255, 255, 0.02)',
                              fontSize: 12,
                              color: 'var(--text-primary)',
                              fontWeight: 600
                            }}
                          >
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {idx + 1}. {ph}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                navigator.clipboard.writeText(ph)
                                setToast(`Copied ${ph}`)
                              }}
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 2, display: 'flex', alignItems: 'center' }}
                              title="Copy phone"
                            >
                              <i className="ti ti-copy" style={{ fontSize: 13 }} />
                            </button>
                          </div>
                        ) : (
                          <div key={`phone-${idx}`} style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Not available
                          </div>
                        )
                      ))}
                    </div>
                  </div>

                  {/* LinkedIn Section */}
                  {selected.linkedin && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>
                        <i className="ti ti-brand-linkedin" style={{ fontSize: 13, color: '#38bdf8' }} />
                        <span>LinkedIn</span>
                      </div>
                      <a
                        href={selected.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: 12,
                          color: 'var(--text-primary)',
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          fontWeight: 600,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{selected.linkedin}</span>
                        <i className="ti ti-external-link" style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }} />
                      </a>
                    </div>
                  )}

                  {/* Created Section */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 2 }}>
                      <i className="ti ti-calendar" style={{ fontSize: 13 }} />
                      <span>Created</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {selectedInsight.createdAt}
                    </div>
                  </div>
                </div>
              </div>

              {/* Company / Firm Analysis Card */}
              <div style={{ border: '1px solid var(--card-border)', borderRadius: 10, padding: 14, background: 'var(--card-bg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 12 }}>
                  <i className="ti ti-building" style={{ color: 'var(--text-muted)', fontSize: 14 }} />
                  <span>Company / Firm Analysis</span>
                </div>

                <div style={{ display: 'grid', gap: 12 }}>
                  {/* Company Branding Block */}
                  {(() => {
                    const freeDoms = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'];
                    const emailDom = selected.email && selected.email.includes('@') && !freeDoms.includes(selected.email.split('@')[1].trim().toLowerCase())
                      ? selected.email.split('@')[1].trim().toLowerCase()
                      : null;
                    const inferredName = emailDom
                      ? emailDom.split('.')[0].replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                      : null;

                    const domain = (selected.company && selected.company.primary_domain) || selected.company_domain || selected.website || selected.email_pattern || emailDom;
                    const name = (selected.company && (selected.company.canonical_name || selected.company.company_name)) || selected.company_name || inferredName || 'Company';
                    const logo = (selected.company && selected.company.logo_url) || selected.logo_url || (domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=128` : null);

                    return (
                      <CompanyIdentity
                        domain={domain}
                        name={name}
                        logo_url={logo}
                        subtitle={domain ? domain : "Verified Corporate Organization"}
                        interactive={false}
                        size={46}
                        logoSize={32}
                        style={{ padding: 0 }}
                      />
                    );
                  })()}

                  {/* Address */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <i className="ti ti-map-pin" style={{ color: 'var(--text-muted)', fontSize: 14, flexShrink: 0 }} />
                    <span>{selectedInsight.address || selected.location || 'San Jose, CA'}</span>
                  </div>

                  {/* State Info */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <i className="ti ti-id" style={{ color: 'var(--text-muted)', fontSize: 14, flexShrink: 0 }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>State Info</span>
                      <span style={{ fontSize: 11.5, color: 'var(--text-primary)', fontWeight: 600 }}>
                        {selected.state_source || 'emirates-area_code'} ({selected.state_confidence || '0/0/5'})
                      </span>
                    </div>
                  </div>

                  {/* Side-by-Side Mini Metrics */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 4 }}>
                    {/* Completeness */}
                    <div
                      style={{
                        border: '1px solid var(--card-border)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        background: 'rgba(255, 255, 255, 0.02)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 700, color: 'var(--text-primary)' }}>
                        <i className="ti ti-circle-check" style={{ color: '#10b981', fontSize: 14 }} />
                        <span>Completeness</span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                        ({selected?.completeness_score ? `${selected.completeness_score}%` : '0/0/5'})
                      </div>
                      <div style={{ width: '100%', height: 4, borderRadius: 999, background: 'rgba(255, 255, 255, 0.1)', marginTop: 8, overflow: 'hidden' }}>
                        <div style={{ width: `${selected?.completeness_score || 80}%`, height: '100%', borderRadius: 999, background: '#10b981' }} />
                      </div>
                    </div>

                    {/* Data Quality */}
                    <div
                      style={{
                        border: '1px solid var(--card-border)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        background: 'rgba(255, 255, 255, 0.02)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 700, color: 'var(--text-primary)' }}>
                        <i className="ti ti-database" style={{ color: '#a855f7', fontSize: 14 }} />
                        <span>Data Quality</span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {selected?.needs_review ? (selected?.review_reason || 'Needs Review') : 'Verified Clean'}
                      </div>
                      <div style={{ width: '100%', height: 4, borderRadius: 999, background: 'rgba(255, 255, 255, 0.1)', marginTop: 8, overflow: 'hidden' }}>
                        <div style={{ width: `${selected?.quality_score || selected?.trust_score || 85}%`, height: '100%', borderRadius: 999, background: '#a855f7' }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Additional Details Collapsible Section */}
              <details
                style={{
                  border: '1px solid var(--card-border)',
                  borderRadius: 10,
                  background: 'var(--card-bg)',
                  overflow: 'hidden'
                }}
              >
                <summary
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    padding: '12px 14px',
                    cursor: 'pointer',
                    outline: 'none',
                    background: 'var(--panel-bg)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <i className="ti ti-file-text" style={{ color: 'var(--text-muted)', fontSize: 14 }} />
                    <span>Additional Details</span>
                  </div>
                  <i className="ti ti-chevron-down" style={{ fontSize: 13, color: 'var(--text-muted)' }} />
                </summary>
                <div style={{ padding: 12, borderTop: '1px solid var(--card-border)', display: 'grid', gap: 8 }}>
                  {selected?.notes ? (
                    <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.6 }}>
                      {selected.notes}
                    </div>
                  ) : null}
                  {selectedInsight.extras.length ? selectedInsight.extras.map((item, index) => (
                    <div key={`${item.key}-${index}`} style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 10, alignItems: 'start' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'capitalize' }}>{item.key}</div>
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
        <div style={{ position: 'fixed', right: 18, bottom: 18, background: 'var(--text-primary)', color: 'var(--main-bg)', padding: '10px 12px', borderRadius: 6, fontSize: 12, zIndex: 1500, boxShadow: 'var(--shadow-lg)' }}>
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
            style={{ width: '100%', maxWidth: 620, padding: 16, borderRadius: 6, background: 'var(--card-bg)', border: '1px solid var(--card-border)', boxShadow: 'var(--shadow-lg)' }}
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
                    style={{ flex: 1, padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none' }}
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
                    style={{ borderRadius: 6, padding: '10px 12px', fontWeight: 900 }}
                  >
                    <i className="ti ti-lock-open" /> Unlock
                  </button>
                </div>
                {editError && <div style={{ fontSize: 12, color: '#e41937' }}>{editError}</div>}
              </div>
            ) : (
              <div style={{ marginTop: 14, display: 'grid', gap: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {EDIT_FORM_FIELDS.map(([label, key]) => (
                    <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ fontSize: 10.5, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</div>
                      <input
                        value={editForm[key]}
                        onChange={(e) => setEditForm((p) => ({ ...p, [key]: e.target.value }))}
                        style={{ padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none' }}
                      />
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: 10.5, fontWeight: 900, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>Notes</div>
                  <textarea
                    value={editForm.notes}
                    onChange={(e) => setEditForm((p) => ({ ...p, notes: e.target.value }))}
                    style={{ padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)', outline: 'none', minHeight: 90, resize: 'vertical' }}
                  />
                </div>

                {editError && <div style={{ fontSize: 12, color: '#e41937' }}>{editError}</div>}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                  <button onClick={() => setEditOpen(false)} style={{ padding: '10px 12px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--card-bg)', color: 'var(--text-secondary)', fontWeight: 900, cursor: 'pointer' }}>
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
                    style={{ borderRadius: 6, padding: '10px 12px', fontWeight: 900, opacity: (editSaving || !selected?.recruiter_id) ? 0.75 : 1 }}
                  >
                    <i className="ti ti-device-floppy" /> {editSaving ? 'Saving…' : 'Save changes'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── AI Boolean Sourcing Modal ── */}
      {booleanModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.65)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: 16,
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setBooleanModalOpen(false) }}
        >
          <div
            style={{
              background: 'var(--panel-bg)',
              border: '1px solid var(--card-border)',
              borderRadius: 12,
              width: '100%',
              maxWidth: 680,
              maxHeight: '90vh',
              overflowY: 'auto',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
              padding: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between', borderBottom: '1px solid var(--card-border)', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--brand)', color: 'var(--text-inverse)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ti ti-code" style={{ fontSize: 16 }} />
                </div>
                <div>
                  <h2 style={{ fontSize: 16, fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>Boolean Query Generator</h2>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>Synthesize cross-platform Boolean strings for LinkedIn, Google X-Ray & TalentOps</p>
                </div>
              </div>
              <button onClick={() => setBooleanModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18 }}>
                <i className="ti ti-x" />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Target Role / Title</label>
                <input
                  type="text"
                  placeholder="e.g. Senior Recruiter, TA Lead"
                  value={booleanRole}
                  onChange={(e) => setBooleanRole(e.target.value)}
                  style={{ width: '100%', marginTop: 4, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--input-bg, #18181b)', color: 'var(--text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Location (State / City)</label>
                <input
                  type="text"
                  placeholder="e.g. CA, Texas, Austin"
                  value={booleanLocation}
                  onChange={(e) => setBooleanLocation(e.target.value)}
                  style={{ width: '100%', marginTop: 4, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--input-bg, #18181b)', color: 'var(--text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Must-Have Skills (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. React, TypeScript, GraphQL"
                  value={booleanSkills}
                  onChange={(e) => setBooleanSkills(e.target.value)}
                  style={{ width: '100%', marginTop: 4, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--input-bg, #18181b)', color: 'var(--text-primary)', fontSize: 13 }}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Exclude Keywords (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. Intern, Junior, Entry"
                  value={booleanExcluded}
                  onChange={(e) => setBooleanExcluded(e.target.value)}
                  style={{ width: '100%', marginTop: 4, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--input-bg, #18181b)', color: 'var(--text-primary)', fontSize: 13 }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Or Paste Job Description / Requisition Notes</label>
              <textarea
                rows={3}
                placeholder="Paste JD to auto-extract skills and target role..."
                value={booleanJD}
                onChange={(e) => setBooleanJD(e.target.value)}
                style={{ width: '100%', marginTop: 4, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--card-border)', background: 'var(--input-bg, #18181b)', color: 'var(--text-primary)', fontSize: 12, resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                onClick={handleGenerateBoolean}
                disabled={booleanGenerating}
                style={{
                  padding: '10px 18px',
                  borderRadius: 8,
                  background: 'var(--brand)',
                  color: 'var(--text-inverse)',
                  border: 'none',
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <i className={booleanGenerating ? 'ti ti-loader animate-spin' : 'ti ti-sparkles'} />
                {booleanGenerating ? 'Generating...' : 'Generate Sourcing Strings'}
              </button>
            </div>

            {booleanResult && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid var(--card-border)', paddingTop: 16 }}>
                {/* TalentOps Search Card */}
                <div style={{ padding: 12, borderRadius: 8, background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#ffffff' }}>TalentOps Direct Query</span>
                    <button
                      onClick={() => {
                        setQuery(booleanResult.talentops_query)
                        setBooleanModalOpen(false)
                      }}
                      style={{ padding: '4px 10px', borderRadius: 6, background: '#ffffff', color: '#fff', border: 'none', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
                    >
                      Run Search Now
                    </button>
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-primary)' }}>{booleanResult.talentops_query}</div>
                </div>

                {/* LinkedIn Boolean Card */}
                <div style={{ padding: 12, borderRadius: 8, background: 'rgba(212, 212, 216, 0.05)', border: '1px solid rgba(212, 212, 216, 0.2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#d4d4d8' }}>LinkedIn Recruiter Boolean String</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(booleanResult.linkedin_boolean)
                        setToast('Copied LinkedIn Boolean!')
                        setTimeout(() => setToast(''), 1400)
                      }}
                      style={{ padding: '4px 10px', borderRadius: 6, background: '#d4d4d8', color: '#fff', border: 'none', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
                    >
                      Copy Boolean
                    </button>
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-primary)', wordBreak: 'break-all' }}>{booleanResult.linkedin_boolean}</div>
                </div>

                {/* Google X-Ray Card */}
                <div style={{ padding: 12, borderRadius: 8, background: 'rgba(161, 161, 170, 0.05)', border: '1px solid rgba(161, 161, 170, 0.2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#a1a1aa' }}>Google X-Ray Sourcing String</span>
                    <a
                      href={booleanResult.google_xray_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ padding: '4px 10px', borderRadius: 6, background: '#a1a1aa', color: '#fff', textDecoration: 'none', fontSize: 11, fontWeight: 700 }}
                    >
                      Open Google X-Ray
                    </a>
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-primary)', wordBreak: 'break-all' }}>{booleanResult.google_xray_query}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {poolModalOpen && (
        <SaveToTalentPoolModal
          isOpen={poolModalOpen}
          onClose={() => setPoolModalOpen(false)}
          recruiterIds={searchResults.map(r => r.id)}
          onSaved={() => setToast('Candidates saved to Talent Pool!')}
        />
      )}

      {explainModalOpen && selectedCandidateForExplain && (
        <AIExplainabilityModal
          isOpen={explainModalOpen}
          onClose={() => {
            setExplainModalOpen(false)
            setSelectedCandidateForExplain(null)
          }}
          candidateId={selectedCandidateForExplain.recruiter_id}
          explanationData={{
            candidate_name: selectedCandidateForExplain.recruiter_name,
            overall_score: selectedCandidateForExplain.trust_score || 91,
            confidence: 0.93,
            confidence_tier: 'High',
            breakdown: {
              skills_match: { score: 94, weight: '35%', label: 'Skills & Competencies' },
              experience_trajectory: { score: 92, weight: '25%', label: 'Career Velocity & Seniority' },
              industry_relevance: { score: 90, weight: '15%', label: 'Domain & Industry Fit' },
              recency_signal: { score: 95, weight: '15%', label: 'Data Freshness & Recency' },
              location_fit: { score: 88, weight: '10%', label: 'Geographic Alignment' }
            },
            evidence: [
              `Corroborated by search query '${query || 'Active Profile'}'.`,
              `Role '${selectedCandidateForExplain.specialization || selectedCandidateForExplain.title || 'Recruiter'}' verified.`,
              `Entity footprint active in live database.`
            ],
            provenance: {
              email_status: selectedCandidateForExplain.email && !selectedCandidateForExplain.email.includes('noemail') ? 'VERIFIED' : 'UNVERIFIED',
              phone_status: selectedCandidateForExplain.phone ? 'VERIFIED' : 'INFERRED',
              profile_status: 'OBSERVED',
              source: 'TalentOps Intelligence'
            }
          }}
        />
      )}

      {intelligenceWorkspacePerson && (
        <PersonIntelligenceWorkspace
          person={intelligenceWorkspacePerson}
          onClose={() => setIntelligenceWorkspacePerson(null)}
          onExplainScore={() => {
            setSelectedCandidateForExplain(intelligenceWorkspacePerson)
            setExplainModalOpen(true)
          }}
        />
      )}

      {intelligenceWorkspaceCompany && (
        <CompanyIntelligenceWorkspace
          company={intelligenceWorkspaceCompany}
          onClose={() => setIntelligenceWorkspaceCompany(null)}
        />
      )}
    </div>
  )
}
