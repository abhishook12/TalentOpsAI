export default function Badge({ children, color = '#38bdf8' }) {
  return <span style={{ background: `${color}22`, color, fontSize: 10.5, fontWeight: 600, padding: '2px 8px', borderRadius: 99, display: 'inline-block' }}>{children}</span>
}
