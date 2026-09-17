import React from 'react'

export function Skeleton({ width, height, borderRadius, style, className = '' }) {
  const mergedStyle = {
    width: width || '100%',
    height: height || '20px',
    borderRadius: borderRadius || '6px',
    backgroundColor: 'var(--skeleton-bg, var(--color-surface-variant, rgba(160, 160, 160, 0.2)))', 
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
    <div style={{ padding: 20, border: '1px solid var(--card-border, #e4e4e7)', borderRadius: '8px', background: 'var(--card-bg)', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Skeleton height={24} width="40%" />
      <SkeletonRow rows={3} gap={10} height={14} />
    </div>
  )
}
