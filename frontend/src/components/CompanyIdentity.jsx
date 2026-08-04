import { useState } from 'react'
import { normalizeLogoDomain } from '../utils/domain'

const failedDomains = new Set()

export function CompanyIdentity({ 
  domain, 
  name, 
  subtitle, 
  metadata, 
  size = 44, 
  logoSize = 32,
  interactive = true,
  style = {}
}) {
  const [errorLevel, setErrorLevel] = useState(0)
  const [isHovered, setIsHovered] = useState(false)

  const cleanDomain = normalizeLogoDomain(domain, name)
  const formatDisplayName = (n) => {
    if (!n) return 'Unknown Company'
    const name = n.trim()
    // If it looks like a slug (e.g. spencer-ogden)
    if (name === name.toLowerCase()) {
      return name.split(/[-_]+/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    }
    return name
  }
  const displayName = formatDisplayName(name)
  
  // Extract initials for monogram
  const getInitials = (n) => {
    if (!n) return '?'
    const words = n.trim().split(' ')
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
    return n.substring(0, 2).toUpperCase()
  }
  const initials = getInitials(displayName)

  const getMonogramColor = (n) => {
    const colors = [
      { bg: 'var(--brand-bg)', text: 'var(--brand-strong)', border: 'var(--brand-bg)' }, // Gold
      { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' }, // Amber
      { bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' }, // Slate
      { bg: 'rgba(20, 184, 166, 0.15)', text: '#2dd4bf', border: 'rgba(20, 184, 166, 0.3)' }, // Teal
      { bg: 'rgba(168, 115, 68, 0.15)', text: '#d99c64', border: 'rgba(168, 115, 68, 0.3)' } // Warm Brown
    ]
    const index = n ? n.charCodeAt(0) % colors.length : 0
    return colors[index]
  }

  const monogramColor = getMonogramColor(displayName)

  // Determine Logo URL based on 4-tier cascade
  let logoUrl = null
  if (cleanDomain && !failedDomains.has(cleanDomain)) {
    if (errorLevel === 0) {
      logoUrl = `https://logo.clearbit.com/${cleanDomain}?size=${logoSize * 4}`
    } else if (errorLevel === 1) {
      logoUrl = `https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://${cleanDomain}&size=${logoSize * 4}`
    } else if (errorLevel === 2) {
      logoUrl = `https://icons.duckduckgo.com/ip3/${cleanDomain}.ico`
    } else if (errorLevel === 3) {
      logoUrl = `https://favicon.im/${cleanDomain}?larger=true`
    }
  }

  const containerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: interactive ? '8px 12px' : 0,
    borderRadius: 12,
    background: isHovered && interactive ? 'rgba(255,255,255,0.03)' : 'transparent',
    border: isHovered && interactive ? '1px solid var(--brand)' : '1px solid transparent',
    transform: isHovered && interactive ? 'translateY(-1px)' : 'translateY(0)',
    transition: 'all 200ms ease',
    cursor: interactive ? 'pointer' : 'default',
    ...style
  }

  const monogramContainerStyle = {
    width: size,
    height: size,
    minWidth: size,
    borderRadius: 12,
    background: monogramColor.bg,
    border: `1px solid ${monogramColor.border}`,
    color: monogramColor.text,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    fontSize: size * 0.4,
    fontWeight: 700,
    letterSpacing: '0.02em'
  }

  return (
    <div 
      style={containerStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Logo Render */}
      {logoUrl ? (
        <img 
          src={logoUrl} 
          alt={`${displayName} logo`}
          loading="lazy"
          style={{ 
            width: size, 
            height: size, 
            minWidth: size,
            borderRadius: 12, 
            objectFit: 'cover',
            background: 'var(--card-bg)',
            border: '1px solid var(--card-border)',
            flexShrink: 0
          }}
          onError={() => {
            if (cleanDomain && errorLevel >= 3) failedDomains.add(cleanDomain)
            setErrorLevel(prev => prev + 1)
          }}
        />
      ) : (
        <div style={monogramContainerStyle}>
          {initials}
        </div>
      )}

      {/* Typography */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
          {displayName}
        </div>
        
        {subtitle && (
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.2 }}>
            {subtitle}
          </div>
        )}
        
        {metadata && (
          <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.2 }}>
            {metadata}
          </div>
        )}
      </div>
    </div>
  )
}
