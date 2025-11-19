import Dashboard from './components/Dashboard.jsx'

export default function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1>🛡️ SPG Semantic Firewall - Executive Dashboard</h1>
          <p className="header-subtitle">Real-time monitoring of security analysis and performance</p>
        </div>
      </header>
      <Dashboard />
    </div>
  )
}