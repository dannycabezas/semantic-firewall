import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './components/Dashboard.jsx'
import BenchmarkDashboard from './components/benchmarks/BenchmarkDashboard.jsx'

export default function App() {
  const location = useLocation()
  
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1>🛡️ SPG Semantic Firewall - Executive Dashboard</h1>
          <p className="header-subtitle">Real-time monitoring of security analysis and performance</p>
        </div>
        <nav className="header-nav">
          <Link 
            to="/" 
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link 
            to="/benchmarks" 
            className={`nav-link ${location.pathname === '/benchmarks' ? 'active' : ''}`}
          >
            Benchmarks
          </Link>
        </nav>
      </header>
      
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/benchmarks" element={<BenchmarkDashboard />} />
      </Routes>
    </div>
  )
}