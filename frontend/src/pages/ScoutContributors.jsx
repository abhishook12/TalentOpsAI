import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Users, RefreshCw, Search, Sparkles, Activity, Zap, Laptop, Clock, UserCheck, ShieldAlert, Award
} from 'lucide-react'
import api from '../services/api'
import ScoutUserProfileDrawer from '../components/ScoutUserProfileDrawer'
import AddScoutModal from '../components/AddScoutModal'

export default function ScoutContributors() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [sortBy, setSortBy] = useState('most_active')
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['scout-contributors', statusFilter, searchQuery, sortBy],
    queryFn: async () => {
      const res = await api.get('/scout/users', {
        params: {
          status: statusFilter === 'ALL' ? undefined : statusFilter,
          search: searchQuery || undefined,
          sort: sortBy,
        }
      })
      return res.data
    },
    keepPreviousData: true,
  })

  const summary = data?.summary || {}
  const users = data?.users || []
  const versionDistribution = data?.version_distribution || {}
  const latestProdVer = data?.latest_production_version || ''

  const formatTimeAgo = (isoStr) => {
    if (!isoStr) return 'Never'
    try {
      const d = new Date(isoStr)
      if (isNaN(d.getTime())) return isoStr
      const diffMs = Date.now() - d.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours}h ago`
      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays}d ago`
    } catch {
      return isoStr || 'Unknown'
    }
  }

  const getStatusBadge = (status) => {
    const st = (status || '').toUpperCase()
    switch (st) {
      case 'CONTRIBUTING':
      case 'CONTRIBUTING_OFFLINE':
        return { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: 'rgba(16, 185, 129, 0.3)', icon: Sparkles }
      case 'ACTIVE':
        return { bg: 'rgba(255, 255, 255, 0.08)', text: '#f5f5f5', border: 'rgba(255, 255, 255, 0.2)', icon: Activity }
      case 'PAIRED':
      case 'PAIRED_IDLE':
        return { bg: 'rgba(212, 212, 216, 0.12)', text: '#d4d4d8', border: 'rgba(212, 212, 216, 0.25)', icon: Zap }
      case 'INSTALLED':
        return { bg: 'rgba(161, 161, 170, 0.12)', text: '#a1a1aa', border: 'rgba(161, 161, 170, 0.25)', icon: Laptop }
      case 'REGISTERED':
        return { bg: 'rgba(113, 113, 122, 0.12)', text: '#a1a1aa', border: 'rgba(113, 113, 122, 0.25)', icon: UserCheck }
      case 'REVOKED':
        return { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', border: 'rgba(239, 68, 68, 0.3)', icon: ShieldAlert }
      default:
        return { bg: 'rgba(255, 255, 255, 0.05)', text: '#a1a1aa', border: 'rgba(255, 255, 255, 0.1)', icon: Clock }
    }
  }

  const totalUsersCount = summary.total_scout_users || users.length || 0
  const activeUsersCount = summary.active_users || 0
  const activeDevicesCount = summary.active_devices || 0
  const totalDevicesCount = summary.total_devices || summary.active_devices || 0
  const contributingUsersCount = summary.contributing_users || 0
  const offlineUsersCount = summary.offline_users || 0
  const updateReqCount = summary.update_required_count ?? summary.update_required ?? 0
  const revokedCount = summary.revoked_count ?? summary.revoked ?? 0
  const canonicalCreated = summary.total_canonical_created ?? summary.total_people_contributed ?? 0
  const canonicalEnriched = summary.total_canonical_enriched ?? summary.total_contacts_contributed ?? 0
  const avgQualScore = summary.avg_quality_score ?? summary.average_quality_score ?? 0

  return (
    <div className="page-container page-enter" style={{ padding: '24px 32px 60px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
      {/* Top Breadcrumb */}
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>
        DASHBOARD
      </div>

      {/* Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em' }}>
            Scout users &amp; contributors
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0', lineHeight: 1.4 }}>
            Every registered Scout account, its paired devices, client version and the records it has contributed.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Status Indicators Tiles */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid #232326', background: '#141416' }} />
            <div style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid #232326', background: '#141416', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444' }} />
            </div>
            <div style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid #232326', background: '#141416' }} />
            <div style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid #232326', background: '#141416' }} />
          </div>

          <button
            onClick={() => refetch()}
            disabled={isFetching}
            style={{
              padding: '6px 14px',
              background: '#161618',
              border: '1px solid #28282c',
              color: '#f5f5f5',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              opacity: isFetching ? 0.6 : 1,
              transition: 'border-color 0.15s ease'
            }}
          >
            <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 7-Card Top Metric Strip (Neutral Charcoal) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 10,
        marginBottom: 16
      }}>
        {[
          { label: 'SCOUT USERS', value: totalUsersCount, sub: 'Registered accounts' },
          { label: 'ACTIVE USERS', value: activeUsersCount, sub: 'Seen in last 24h' },
          { label: 'ACTIVE DEVICES', value: activeDevicesCount, sub: `of ${totalDevicesCount} paired` },
          { label: 'CONTRIBUTING', value: contributingUsersCount, sub: 'Added or enriched data' },
          { label: 'OFFLINE', value: offlineUsersCount, sub: 'No signal over 7d' },
          { label: 'UPDATE REQUIRED', value: updateReqCount, sub: 'Behind current build' },
          { label: 'REVOKED', value: revokedCount, sub: 'Blocked or quarantined' },
        ].map((card, idx) => (
          <div
            key={idx}
            style={{
              background: '#121214',
              border: '1px solid #232326',
              borderRadius: 8,
              padding: '14px 16px',
              display: 'flex',
              flexDirection: 'column',
              minWidth: 0,
            }}
          >
            <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
              {card.label}
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)', margin: '6px 0 2px' }}>
              {card.value}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {card.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Middle Row: Database Contribution & Client Versions */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 1fr',
        gap: 12,
        marginBottom: 16
      }}>
        {/* Left: Contribution to the Database */}
        <div style={{
          background: '#121214',
          border: '1px solid #232326',
          borderRadius: 8,
          padding: '16px 20px',
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 14 }}>
            CONTRIBUTION TO THE DATABASE
          </div>
          <div style={{ display: 'flex', gap: 32, alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>People added</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', marginTop: 2 }}>
                {canonicalCreated}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Contacts enriched</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', marginTop: 2 }}>
                {canonicalEnriched}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Average quality</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)', marginTop: 2 }}>
                {avgQualScore} / 100
              </div>
            </div>
          </div>
        </div>

        {/* Right: Client Versions */}
        <div style={{
          background: '#121214',
          border: '1px solid #232326',
          borderRadius: 8,
          padding: '16px 20px',
        }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 14 }}>
            CLIENT VERSIONS
          </div>
          <div>
            {Object.entries(versionDistribution).length === 0 ? (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>No device versions reported</span>
            ) : (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {Object.entries(versionDistribution).map(([ver, count]) => {
                  const isLatest = ver === latestProdVer
                  return (
                    <span
                      key={ver}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        background: '#18181b',
                        color: isLatest ? '#f5f5f5' : 'var(--text-muted)',
                        border: '1px solid #27272a'
                      }}
                    >
                      v{ver}: <b>{count}</b> {isLatest ? '✓' : ''}
                    </span>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Container: Search, Filter Pills & Table/Empty State */}
      <div style={{
        background: '#121214',
        border: '1px solid #232326',
        borderRadius: 8,
        overflow: 'hidden'
      }}>
        {/* Controls Bar */}
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid #232326',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12
        }}>
          {/* Search */}
          <div style={{ position: 'relative', width: 320 }}>
            <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search name, email or company"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 12px 7px 34px',
                background: '#0b0b0c',
                border: '1px solid #232326',
                borderRadius: 6,
                color: '#f5f5f5',
                fontSize: 12,
                outline: 'none'
              }}
            />
          </div>

          {/* Filters & Sort */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {[
                { key: 'ALL', label: 'All' },
                { key: 'CONTRIBUTING', label: 'Contributing' },
                { key: 'ACTIVE', label: 'Active' },
                { key: 'PAIRED', label: 'Paired' },
                { key: 'REGISTERED', label: 'Registered' },
                { key: 'REVOKED', label: 'Revoked' },
              ].map((pill) => {
                const isActive = statusFilter === pill.key
                return (
                  <button
                    key={pill.key}
                    onClick={() => setStatusFilter(pill.key)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 6,
                      fontSize: 11,
                      fontWeight: isActive ? 700 : 500,
                      background: isActive ? '#f5f5f5' : 'transparent',
                      color: isActive ? '#0b0b0c' : 'var(--text-muted)',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {pill.label}
                  </button>
                )
              })}
            </div>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                background: '#161618',
                border: '1px solid #28282c',
                color: '#f5f5f5',
                borderRadius: 6,
                padding: '5px 10px',
                fontSize: 11,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="most_active">Most active</option>
              <option value="most_data">Most data</option>
              <option value="highest_quality">Highest quality</option>
              <option value="most_devices">Most devices</option>
            </select>
          </div>
        </div>

        {/* Content Area */}
        {isLoading ? (
          <div style={{ padding: 70, textAlign: 'center', color: 'var(--text-muted)' }}>
            <RefreshCw size={20} className="animate-spin" style={{ margin: '0 auto 10px' }} />
            <div style={{ fontSize: 13 }}>Loading Scout contributors...</div>
          </div>
        ) : users.length === 0 ? (
          /* Empty State Matching Screenshot */
          <div style={{ padding: '80px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.04)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 14,
              color: 'var(--text-muted)'
            }}>
              <Users size={22} />
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
              No Scout users match this query
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Clear the search or pick a different status.
            </div>
          </div>
        ) : (
          /* Data Table */
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#0e0e10', borderBottom: '1px solid #232326' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>USER &amp; ACCOUNT</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>STATUS</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>DEVICES</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>VERSION</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>LAST SEEN</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>DATA IMPACT</th>
                  <th style={{ padding: '12px 16px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>QUALITY</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const statusKey = u.lifecycle_status || u.scout_status || 'REGISTERED'
                  const badge = getStatusBadge(statusKey)
                  const userName = u.full_name || u.name || 'Unnamed User'
                  const deviceCount = u.device_count ?? u.devices_count ?? 0
                  const versionStr = u.primary_version || u.current_version || latestProdVer || '—'
                  const lastSeenDisplay = u.last_seen_at ? formatTimeAgo(u.last_seen_at) : (u.last_seen || '—')
                  const newPeople = u.contributions?.canonical_new ?? u.new_people_created ?? 0
                  const enrichedPeople = u.contributions?.canonical_enriched ?? u.people_enriched ?? 0
                  const qualityScore = u.quality?.overall_score ?? u.quality_score ?? 0

                  return (
                    <tr
                      key={u.user_id}
                      onClick={() => setSelectedUserId(u.user_id)}
                      style={{
                        borderBottom: '1px solid #232326',
                        cursor: 'pointer',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{userName}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.email}</div>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          background: badge.bg,
                          color: badge.text,
                          border: `1px solid ${badge.border}`
                        }}>
                          {statusKey}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>
                        {deviceCount}
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                        v{versionStr}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>
                        {lastSeenDisplay}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>
                        +{newPeople} new / +{enrichedPeople} enriched
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {qualityScore}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* User Detail Drawer */}
      {selectedUserId && (
        <ScoutUserProfileDrawer
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
        />
      )}

      {/* Add Scout Modal */}
      {isAddModalOpen && (
        <AddScoutModal
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
        />
      )}
    </div>
  )
}
