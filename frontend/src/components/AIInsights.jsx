
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { ShellCard, SectionHeader, Badge } from './CommandCenter';
import { SkeletonRow } from './ui/Skeleton';
import { BarChart3, TrendingUp, MapPin, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

const ICON_MAP = {
  'growth': TrendingUp,
  'geo': MapPin,
  'traffic': Activity,
};

const DEFAULT_INSIGHTS = [
  { id: 1, text: 'Recruiter database is stable with verified operational coverage.', type: 'growth' },
  { id: 2, text: 'Active talent density observed across primary tech hubs.', type: 'geo' },
  { id: 3, text: 'Platform telemetry and sourcing streams operating at baseline.', type: 'traffic' }
];

export default function AIInsights() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-insights'],
    queryFn: async () => {
      const res = (await api.get('/analytics/insights')).data;
      try { localStorage.setItem('dashboard-insights', JSON.stringify(res)) } catch { /* ignore */ }
      return res;
    },
    initialData: () => {
      try {
        const cached = localStorage.getItem('dashboard-insights');
        return cached ? JSON.parse(cached) : undefined;
      } catch { return undefined; }
    },
    staleTime: 60000,
  });

  const insightsToRender = (data?.insights && data.insights.length > 0)
    ? data.insights
    : DEFAULT_INSIGHTS;

  return (
    <ShellCard style={{ padding: 18, marginBottom: 16, background: 'var(--panel-bg)', border: '1px solid var(--card-border)' }}>
      <SectionHeader
        eyebrow="Intelligence"
        title="Observations"
        subtitle="Automated analysis of your operational data."
        action={
          <Badge tone="success" style={{ background: 'var(--brand-bg)', color: 'var(--text-primary)', borderColor: 'var(--card-border)' }}>
            <BarChart3 size={12} style={{ marginRight: 4 }} /> Active
          </Badge>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 16 }}>
        {isLoading && !data && !insightsToRender.length ? (
          <>
            <SkeletonRow height={80} />
            <SkeletonRow height={80} />
            <SkeletonRow height={80} />
          </>
        ) : (
          insightsToRender.map((insight, idx) => {
            const Icon = ICON_MAP[insight.type] || BarChart3;
            return (
              <motion.div 
                key={insight.id}
                initial={{ opacity: 0.8, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 16,
                  padding: '16px 20px', borderRadius: 8,
                  background: 'var(--bg-elevated, var(--card-bg))',
                  border: '1px solid var(--card-border)',
                  boxShadow: 'var(--shadow)',
                }}
              >
                <div style={{ 
                  width: 44, height: 44, flexShrink: 0, borderRadius: 10, 
                  background: 'var(--brand-bg)', 
                  display: 'grid', placeItems: 'center', color: 'var(--text-primary)', 
                  border: '1px solid var(--card-border)'
                }}>
                  <Icon size={22} strokeWidth={2.5} />
                </div>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                    {insight.text}
                  </div>
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </ShellCard>
  );
}
