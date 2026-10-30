import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';
import { ShellCard, SectionHeader, Badge } from '../../components/CommandCenter';
import { SkeletonRow } from '../../components/ui/Skeleton';
import { MessageSquare, Eye, EyeOff, Activity, ShieldCheck, RefreshCw, Smartphone, Building, User, Clock, Terminal } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeamsHarvestAdmin() {
  const queryClient = useQueryClient();
  const [actionLoading, setActionLoading] = useState(false);

  // 1. Fetch Window & Supervisor Status
  const { data: winStatus, refetch: refetchStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['system-windows-status'],
    queryFn: async () => (await api.get('/system-windows/status')).data,
    refetchInterval: 5000,
  });

  // 2. Fetch Staging Stream
  const { data: stagingData, isLoading: stagingLoading } = useQuery({
    queryKey: ['teams-staging-stream'],
    queryFn: async () => {
      const res = await api.get('/staging/queue?limit=50');
      const items = Array.isArray(res.data) ? res.data : (res.data?.items || []);
      return items.filter(x => (x.source || '').toLowerCase().includes('teams') || (x.batch_id || '').includes('TEAMS'));
    },
    refetchInterval: 10000,
  });

  const handleShowWindow = async () => {
    setActionLoading(true);
    try {
      await api.post('/system-windows/teams/show');
      toast.success('Microsoft Teams window opened visibly on desktop');
      refetchStatus();
    } catch (err) {
      toast.error('Could not restore Teams window: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleHideWindow = async () => {
    setActionLoading(true);
    try {
      await api.post('/system-windows/teams/hide');
      toast.success('Teams window tucked off-screen to background (Zero desktop intrusion)');
      refetchStatus();
    } catch (err) {
      toast.error('Could not hide Teams window: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const supervisor = winStatus?.teams?.supervisor || {};
  const isVisible = winStatus?.teams?.is_visible_on_screen || false;
  const isRunning = supervisor?.status === 'RUNNING';

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <SectionHeader
        eyebrow="Autonomous Pipeline"
        title="Teams Harvester Live Stream"
        subtitle="Continuous 24/7 upward message scraper and phone intelligence engine."
      />

      {/* Control Panel */}
      <ShellCard style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, borderBottom: '1px solid var(--card-border)', paddingBottom: 16, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 44,
              height: 44,
              borderRadius: 10,
              background: 'rgba(184, 213, 160, 0.12)',
              border: '1px solid rgba(184, 213, 160, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--brand)'
            }}>
              <MessageSquare size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Perpetual Teams Extractor
                </h3>
                <Badge tone={isRunning ? 'success' : 'warning'}>
                  {isRunning ? '● ACTIVE & HARVESTING' : 'INITIALIZING'}
                </Badge>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  background: isVisible ? 'rgba(230, 184, 117, 0.15)' : 'rgba(184, 213, 160, 0.15)',
                  color: isVisible ? 'var(--warning)' : 'var(--brand)',
                  border: isVisible ? '1px solid rgba(230, 184, 117, 0.3)' : '1px solid rgba(184, 213, 160, 0.3)'
                }}>
                  {isVisible ? 'Window: Visible on Desktop' : 'Window: Tucked Off-Screen (Background)'}
                </span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
                Target Chat: <strong>{supervisor.chat || 'CTV- Phone numbers'}</strong> • Uptime: {supervisor.uptime_minutes || 0} min • PID: {supervisor.active_pid || 'Supervisor Managed'}
              </p>
            </div>
          </div>

          {/* Window Control Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={handleShowWindow}
              disabled={actionLoading || isVisible}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '9px 16px',
                borderRadius: 8,
                border: '1px solid var(--card-border)',
                background: isVisible ? 'var(--sidebar-active-bg)' : 'var(--bg-elevated)',
                color: isVisible ? 'var(--brand)' : 'var(--text-primary)',
                fontSize: 13,
                fontWeight: 600,
                cursor: (actionLoading || isVisible) ? 'default' : 'pointer',
                opacity: isVisible ? 0.6 : 1,
                transition: 'all 0.15s ease'
              }}
            >
              <Eye size={16} />
              <span>Open Teams Window</span>
            </button>

            <button
              onClick={handleHideWindow}
              disabled={actionLoading || !isVisible}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '9px 16px',
                borderRadius: 8,
                border: '1px solid var(--card-border)',
                background: !isVisible ? 'var(--sidebar-active-bg)' : 'var(--bg-elevated)',
                color: !isVisible ? 'var(--brand)' : 'var(--text-primary)',
                fontSize: 13,
                fontWeight: 600,
                cursor: (actionLoading || !isVisible) ? 'default' : 'pointer',
                opacity: !isVisible ? 0.6 : 1,
                transition: 'all 0.15s ease'
              }}
            >
              <EyeOff size={16} />
              <span>Keep Off-Screen (Background)</span>
            </button>
          </div>
        </div>

        {/* Live Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          <div style={{ padding: 14, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Execution Mode</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>Headless Background (Off-Screen)</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Zero desktop intrusion</div>
          </div>

          <div style={{ padding: 14, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Memory Usage</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>{supervisor.memory_mb || 180} MB</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>PyWinAuto Chromium UIA Pipe</div>
          </div>

          <div style={{ padding: 14, borderRadius: 8, background: 'var(--bg-elevated)', border: '1px solid var(--card-border)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Supervisor Watchdog</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--brand)', marginTop: 4 }}>Immortal 24/7/365</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Auto-revives on sleep or crash</div>
          </div>
        </div>
      </ShellCard>

      {/* Live Candidates Stream */}
      <ShellCard style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
              Recent Extracted Profiles (Teams Stream)
            </h3>
            <p style={{ margin: '2px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
              Live candidates auto-staged into the discovery pipeline
            </p>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries(['teams-staging-stream'])}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: 'transparent',
              border: '1px solid var(--card-border)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>

        {stagingLoading ? (
          <SkeletonRow rows={4} height={48} />
        ) : !stagingData || stagingData.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Continuous ingestion active. Extracted profiles will stream here as message history is parsed.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--card-border)', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  <th style={{ padding: '10px 12px' }}>Candidate Name</th>
                  <th style={{ padding: '10px 12px' }}>Phone Number</th>
                  <th style={{ padding: '10px 12px' }}>Company</th>
                  <th style={{ padding: '10px 12px' }}>Title / Role</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Staged Time</th>
                </tr>
              </thead>
              <tbody>
                {stagingData.slice(0, 15).map((row, idx) => (
                  <tr key={row.staging_id || idx} style={{ borderBottom: '1px solid var(--card-border)', color: 'var(--text-primary)' }}>
                    <td style={{ padding: '12px 12px', fontWeight: 600 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <User size={15} style={{ color: 'var(--text-muted)' }} />
                        <span>{row.name || 'Candidate Record'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px', color: 'var(--brand)', fontFamily: 'var(--mono)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Smartphone size={14} />
                        <span>{row.phone || row.phone_number || 'Extracted via UIA'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px', color: 'var(--text-secondary)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Building size={14} style={{ color: 'var(--text-muted)' }} />
                        <span>{row.company || 'Enterprise'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px', color: 'var(--text-muted)' }}>
                      {row.title || 'Recruiter'}
                    </td>
                    <td style={{ padding: '12px 12px', textAlign: 'right', color: 'var(--text-muted)', fontSize: 12 }}>
                      {row.created_at ? new Date(row.created_at).toLocaleTimeString() : 'Recent'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ShellCard>
    </div>
  );
}
