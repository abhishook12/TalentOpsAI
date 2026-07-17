import React from 'react'

export function Skeleton({ width, height, borderRadius, style, className = '' }) {
  const mergedStyle = {
    width: width || '100%',
    height: height || '20px',
    borderRadius: borderRadius || '4px',
    backgroundColor: 'var(--border)', // subtle background
    animation: 'ccPulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    ...style
  }

  return <div className={`skeleton ${className}`} style={mergedStyle} />
}

export function SkeletonRow({ rows = 3, gap = 12, height = 20 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={height} width={i === rows - 1 ? '60%' : '100%'} />
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="glass-card" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Skeleton height={24} width="40%" />
      <SkeletonRow rows={3} gap={10} height={14} />
    </div>
  )
}
