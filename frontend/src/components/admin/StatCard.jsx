export default function StatCard({ icon, label, value, sub, color = '#185FA5', glow }) {
  return (
    <div style={{
      background: 'var(--card-bg)', border: `1px solid ${glow ? color : 'var(--card-border)'}`,
      borderRadius: 12, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 8,
      boxShadow: glow ? `0 0 20px ${color}33` : 'var(--shadow)',
      transition: 'all 0.2s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <i className={`ti ${icon}`} style={{ color, fontSize: 18 }} />
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}
