import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import { ShellCard, SectionHeader, Badge, ProgressBar, EmptyState } from '../../components/CommandCenter';
import { SkeletonRow } from '../../components/ui/Skeleton';
import { Server, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react';

export default function BackgroundJobs() {
  const { data, isLoading } = useQuery({
    queryKey: ['background-jobs'],
    queryFn: async () => (await api.get('/admin/jobs')).data,
    refetchInterval: 5000,
  });

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <SectionHeader
        eyebrow="System Operations"
        title="Background Jobs"
        subtitle="Live queue of asynchronous processing tasks and AI enrichments."
      />

      <ShellCard style={{ padding: 18 }}>
        <div style={{ display: 'grid', gap: 12 }}>
          {isLoading ? (
            <SkeletonRow rows={5} height={60} />
          ) : data?.length === 0 ? (
            <EmptyState icon="ti-check" title="Queue is empty" description="No background jobs are currently running." />
          ) : (
            data?.map(job => (
              <div key={job.job_id} style={{ display: 'grid', gap: 8, padding: 16, border: '1px solid var(--card-border)', borderRadius: 14, background: 'var(--bg-surface)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Server size={18} style={{ color: 'var(--text-muted)' }} />
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{job.filename || 'System Task'}</div>
                    <Badge tone={job.status.toLowerCase().includes('complete') ? 'success' : job.status.toLowerCase().includes('fail') ? 'danger' : 'warning'}>
                      {job.status}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-secondary)' }}>
                  <span>{job.progress}% Complete</span>
                  <span>{job.processed_rows} / {job.total_rows} records</span>
                </div>
                
                <ProgressBar 
                  value={job.progress} 
                  tone={job.status.toLowerCase().includes('complete') ? 'success' : job.status.toLowerCase().includes('fail') ? 'danger' : 'accent'} 
                />
              </div>
            ))
          )}
        </div>
      </ShellCard>
    </div>
  );
}
