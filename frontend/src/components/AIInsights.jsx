import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { ShellCard, SectionHeader, Badge } from './CommandCenter';
import { SkeletonRow } from './ui/Skeleton';
import { Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export default function AIInsights() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-insights'],
    queryFn: async () => (await api.get('/analytics/insights')).data,
    staleTime: 60000,
  });

  return (
    <ShellCard style={{ padding: 18, marginBottom: 16, background: 'linear-gradient(135deg, var(--bg-surface), var(--card-bg))', border: '1px solid var(--card-border)', boxShadow: '0 8px 32px rgba(14, 165, 233, 0.05)' }}>
      <SectionHeader
        eyebrow="Intelligence"
        title="Smart Insights"
        subtitle="AI-driven analysis of your operational data."
        action={
          <Badge tone="success" style={{ background: 'rgba(14, 165, 233, 0.1)', color: 'var(--accent)', borderColor: 'rgba(14, 165, 233, 0.2)' }}>
            <Sparkles size={12} style={{ marginRight: 4 }} /> AI Active
          </Badge>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 16 }}>
        {isLoading ? (
          <>
            <SkeletonRow height={80} />
            <SkeletonRow height={80} />
            <SkeletonRow height={80} />
          </>
        ) : (
          data?.insights?.map((insight, idx) => (
            <motion.div 
              key={insight.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 14,
                padding: 16, borderRadius: 12,
                background: 'rgba(14, 165, 233, 0.03)',
                border: '1px solid rgba(14, 165, 233, 0.1)',
              }}
            >
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--bg-surface)', display: 'grid', placeItems: 'center', color: 'var(--accent)', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
                <i className={insight.icon} style={{ fontSize: 18 }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.4 }}>
                  {insight.text}
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </ShellCard>
  );
}
