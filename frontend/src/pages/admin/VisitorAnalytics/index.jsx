import React, { useState } from 'react'
import { Activity, Users, Globe, LayoutDashboard, Clock } from 'lucide-react'
import OverviewTab from './OverviewTab'
import LiveVisitorsTab from './LiveVisitorsTab'
import SessionsTab from './SessionsTab'

export default function VisitorAnalytics() {
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'live', label: 'Live Visitors', icon: Activity },
    { id: 'sessions', label: 'Sessions', icon: Clock },
  ]

  return (
    <div style={{ padding: '24px', height: '100dvh', overflowY: 'auto' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 900, color: '#f3f3f3', margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>Visitor Analytics</h1>
        <p style={{ color: 'rgba(255,255,255,0.6)', margin: 0, fontSize: 15 }}>Monitor real-time user intelligence, engagement, and session health.</p>
      </div>

      <div style={{ 
        display: 'flex', 
        gap: 8, 
        borderBottom: '1px solid var(--card-border)', 
        marginBottom: 24,
        paddingBottom: 2
      }}>
        {tabs.map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 16px',
                background: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: isActive ? '#fff' : 'rgba(255,255,255,0.6)',
                border: 'none',
                borderRadius: '8px 8px 0 0',
                borderBottom: isActive ? '2px solid #fff' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 600,
                transition: 'all 0.2s',
                marginBottom: -3
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          )
        })}
      </div>

      <div style={{ minHeight: 400 }}>
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'live' && <LiveVisitorsTab />}
        {activeTab === 'sessions' && <SessionsTab />}
      </div>
    </div>
  )
}
