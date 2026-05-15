import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Recruiters from './pages/Recruiters'
import Candidates from './pages/Candidates'
import Submissions from './pages/Submissions'
import Analytics from './pages/Analytics'
import AISearch from './pages/AISearch'

const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
  @import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.0.0/dist/tabler-icons.min.css');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --sidebar-bg: #0b1120;
    --sidebar-border: #172033;
    --sidebar-width: 220px;
    --accent: #185FA5;
    --accent-light: #7dd3fc;
    --main-bg: #f8fafc;
    --card-bg: #ffffff;
    --card-border: #e8edf4;
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --font: 'DM Sans', sans-serif;
    --mono: 'DM Mono', monospace;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
  }

  html, body, #root {
    height: 100%;
    font-family: var(--font);
    background: var(--main-bg);
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
  }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

  table { border-collapse: collapse; width: 100%; }
  th {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 10px 16px;
    background: #f8fafc;
    border-bottom: 1px solid var(--card-border);
    text-align: left;
  }
  td {
    padding: 11px 16px;
    font-size: 13.5px;
    color: var(--text-primary);
    border-bottom: 1px solid #f1f5f9;
    vertical-align: middle;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f8fafc; }

  input, select, textarea {
    font-family: var(--font);
    font-size: 13.5px;
    color: var(--text-primary);
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 9px 13px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  input:focus, select:focus, textarea:focus {
    border-color: #185FA5;
    box-shadow: 0 0 0 3px rgba(24,95,165,0.1);
  }

  button {
    font-family: var(--font);
    cursor: pointer;
    border: none;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 500;
    transition: all 0.15s ease;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .page-enter { animation: fadeUp 0.25s ease forwards; }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }

  .btn-primary {
    background: #185FA5;
    color: #fff;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: background 0.15s;
  }
  .btn-primary:hover { background: #1a6ab8; }

  .badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
  }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-green { background: #dcfce7; color: #166534; }
  .badge-gray { background: #f1f5f9; color: #475569; }
  .badge-red { background: #fee2e2; color: #991b1b; }
  .badge-amber { background: #fef3c7; color: #92400e; }
`

function App() {
  useEffect(() => {
    const style = document.createElement('style')
    style.textContent = globalStyles
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <main style={{
          flex: 1,
          padding: '28px 32px',
          overflowY: 'auto',
          background: 'var(--main-bg)',
          minHeight: '100vh',
        }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/recruiters" element={<Recruiters />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/submissions" element={<Submissions />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/ai-search" element={<AISearch />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
