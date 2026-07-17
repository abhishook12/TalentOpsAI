import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import { ShellCard, SectionHeader, Badge, EmptyState } from '../../components/CommandCenter';
import { SkeletonRow } from '../../components/ui/Skeleton';
import { ShieldAlert, Fingerprint, Activity, Terminal } from 'lucide-react';

export default function AuditLogs() {
  const [searchTerm, setSearchTerm] = useState('');
  
  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: async () => (await api.get('/admin/audit-logs')).data,
    refetchInterval: 15000,
  });

  const filtered = data?.filter(log => 
    log.action_type.toLowerCase().includes(searchTerm.toLowerCase()) || 
    log.ip_address?.includes(searchTerm)
  );

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <SectionHeader
        eyebrow="Security & Compliance"
        title="Comprehensive Audit Logs"
        subtitle="Immutable record of system actions, authentication events, and data exports."
        action={
          <div style={{ position: 'relative', width: 250 }}>
            <i className="ti ti-search" style={{ position: 'absolute', left: 12, top: 10, color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="Search logs (action, IP)..." 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{
                width: '100%', padding: '8px 12px 8px 36px',
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 8, color: 'var(--text-primary)', outline: 'none'
              }}
            />
          </div>
        }
      />

      <ShellCard style={{ padding: 18 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {isLoading ? (
            <SkeletonRow rows={10} height={45} />
          ) : filtered?.length === 0 ? (
            <EmptyState icon="ti-shield-lock" title="No logs found" description="No audit records match your search." />
          ) : (
            filtered?.map((log, index) => (
              <div 
                key={log.id} 
                style={{ 
                  display: 'grid', gridTemplateColumns: '40px 1fr 120px 200px', alignItems: 'center', gap: 16, 
                  padding: '12px 16px', 
                  borderBottom: index < filtered.length - 1 ? '1px solid var(--card-border)' : 'none',
                  background: index % 2 === 0 ? 'transparent' : 'rgba(14, 165, 233, 0.02)',
                  borderRadius: index === 0 ? '8px 8px 0 0' : index === filtered.length - 1 ? '0 0 8px 8px' : 0
                }}
              >
                <div style={{ color: 'var(--text-muted)' }}>
                  {log.action_type.includes('AUTH') || log.action_type.includes('LOGIN') ? <Fingerprint size={18} /> : 
                   log.action_type.includes('FAIL') || log.action_type.includes('ERROR') ? <ShieldAlert size={18} style={{ color: 'var(--danger)' }} /> : 
                   <Terminal size={18} />}
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{log.action_type}</div>
                  {log.details && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--mono)', marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.details}
                    </div>
                  )}
                </div>
                <div>
                  <Badge tone="neutral" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{log.ip_address || 'System'}</Badge>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>
                  {new Date(log.timestamp).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      </ShellCard>
    </div>
  );
}
