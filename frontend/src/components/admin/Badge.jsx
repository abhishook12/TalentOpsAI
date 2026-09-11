export default function Badge({ children, color = '#e4e4e7' }) {
  return <span style={{ background: `${color}22`, color, fontSize: 10.5, fontWeight: 600, padding: '2px 8px', borderRadius: 99, display: 'inline-block' }}>{children}</span>
}
