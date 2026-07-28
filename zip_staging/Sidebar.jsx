import { Link, useLocation } from 'react-router-dom'

const links = [
  { path: '/', label: '📊 Dashboard' },
  { path: '/recruiters', label: '👥 Recruiters' },
  { path: '/candidates', label: '🧑‍💼 Candidates' },
  { path: '/submissions', label: '📋 Submissions' },
  { path: '/analytics', label: '📈 Analytics' },
  { path: '/ai-search', label: '⚡ AI Search' },
]

function Sidebar() {
  const location = useLocation()

  return (
    <div style={{
      width: '220px',
      background: '#1e293b',
      padding: '24px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      minHeight: '100vh'
    }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ color: '#38bdf8', fontSize: '18px', fontWeight: 'bold' }}>⚡ TalentOps AI</h1>
        <p style={{ color: '#64748b', fontSize: '12px' }}>Recruitment Intelligence</p>
      </div>
      {links.map(link => (
        <Link
          key={link.path}
          to={link.path}
          style={{
            padding: '10px 14px',
            borderRadius: '8px',
            textDecoration: 'none',
            color: location.pathname === link.path ? '#38bdf8' : '#94a3b8',
            background: location.pathname === link.path ? '#0f172a' : 'transparent',
            fontWeight: location.pathname === link.path ? '600' : '400',
            fontSize: '14px'
          }}
        >
          {link.label}
        </Link>
      ))}
    </div>
  )
}

export default Sidebar
