import React from 'react'
import { motion } from 'framer-motion'

export function EmptyState({ icon = 'ti-inbox', title = 'No data available', description, action }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        background: 'var(--main-bg)',
        border: '1px dashed var(--border)',
        borderRadius: 12,
        color: 'var(--text-muted)'
      }}
    >
      <div style={{
        width: 48,
        height: 48,
        borderRadius: '50%',
        background: 'rgba(120, 130, 145, 0.1)',
        display: 'grid',
        placeItems: 'center',
        marginBottom: 16
      }}>
        <i className={	i } style={{ fontSize: 24, color: 'var(--text-secondary)' }} />
      </div>
      <h3 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{title}</h3>
      {description && <p style={{ margin: '0 0 20px', fontSize: 13, maxWidth: 320, lineHeight: 1.5 }}>{description}</p>}
      {action && <div>{action}</div>}
    </motion.div>
  )
}
