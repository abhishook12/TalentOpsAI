function cx(...values) {
  return values.filter(Boolean).join(' ')
}

export function ShellCard({ children, className = '', style = {} }) {
  return (
    <div className={cx('cc-card', className)} style={style}>
      {children}
    </div>
  )
}

export function SectionHeader({ title, subtitle, action, eyebrow, icon }) {
  return (
    <div className="cc-section-header">
      <div style={{ minWidth: 0 }}>
        {eyebrow && <div className="cc-eyebrow">{eyebrow}</div>}
        <div className="cc-title-row">
          {icon && <i className={`ti ${icon} cc-title-icon`} />}
          <div style={{ minWidth: 0 }}>
            <h2 className="cc-section-title">{title}</h2>
            {subtitle && <p className="cc-section-subtitle">{subtitle}</p>}
          </div>
        </div>
      </div>
      {action && <div className="cc-section-action">{action}</div>}
    </div>
  )
}

export function MetricCard({ label, value, sublabel, tone = 'neutral', icon, contrast = false }) {
  return (
    <div className={cx('cc-metric', contrast && 'cc-metric-contrast', tone && `cc-tone-${tone}`)}>
      <div className="cc-metric-top">
        <div className="cc-metric-label">{label}</div>
        {icon && <i className={`ti ${icon} cc-metric-icon`} />}
      </div>
      <div className="cc-metric-value">{value ?? 'Not available'}</div>
      {sublabel && <div className="cc-metric-sub">{sublabel}</div>}
    </div>
  )
}

export function Badge({ children, tone = 'neutral', className = '' }) {
  return <span className={cx('cc-badge', `cc-badge-${tone}`, className)}>{children}</span>
}

export function GhostButton({ children, className = '', ...props }) {
  return (
    <button className={cx('cc-ghost-button', className)} {...props}>
      {children}
    </button>
  )
}

export function PrimaryButton({ children, className = '', ...props }) {
  return (
    <button className={cx('cc-primary-button', className)} {...props}>
      {children}
    </button>
  )
}

export function ProgressBar({ value = 0, tone = 'accent' }) {
  return (
    <div className="cc-progress">
      <div className={cx('cc-progress-fill', `cc-progress-${tone}`)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="cc-empty">
      {icon && <i className={`ti ${icon} cc-empty-icon`} />}
      <div className="cc-empty-title">{title}</div>
      {description && <div className="cc-empty-desc">{description}</div>}
      {action && <div className="cc-empty-action">{action}</div>}
    </div>
  )
}

export function TimelineItem({ title, meta, description, tone = 'neutral', icon }) {
  return (
    <div className="cc-timeline-item">
      <div className={cx('cc-timeline-dot', `cc-tone-${tone}`)}>
        {icon ? <i className={`ti ${icon}`} /> : null}
      </div>
      <div style={{ minWidth: 0 }}>
        <div className="cc-timeline-title">{title}</div>
        {meta && <div className="cc-timeline-meta">{meta}</div>}
        {description && <div className="cc-timeline-desc">{description}</div>}
      </div>
    </div>
  )
}
