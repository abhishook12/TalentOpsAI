import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Recruiters from './pages/Recruiters'
import Candidates from './pages/Candidates'
import Submissions from './pages/Submissions'
import Analytics from './pages/Analytics'
import AISearch from './pages/AISearch'

function App() {
  return (
    <Router>
      <div style={{ display: 'flex', minHeight: '100vh', background: '#0f172a' }}>
        <Sidebar />
        <main style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
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
