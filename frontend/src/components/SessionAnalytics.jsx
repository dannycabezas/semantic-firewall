import { useEffect, useState } from 'react'
import { fetchAPI } from '../services/websocket'

export default function SessionAnalytics() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSessionAnalytics()
    const interval = setInterval(loadSessionAnalytics, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const loadSessionAnalytics = async () => {
    try {
      const data = await fetchAPI('/api/session-analytics?top=5')
      setSessions(data.sessions || [])
      setLoading(false)
    } catch (err) {
      console.error('Error loading session analytics:', err)
      setLoading(false)
    }
  }

  const formatLastSeen = (timestamp) => {
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      
      if (diffMins < 1) return 'Now'
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      return `${diffHours}h ago`
    } catch {
      return 'N/A'
    }
  }

  if (loading) {
    return <div className="session-analytics loading">Loading...</div>
  }

  if (sessions.length === 0) {
    return (
      <div className="session-analytics empty">
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>No session activity</p>
          <small>Sessions will appear here when detected</small>
        </div>
        <div className="analytics-note">
          <small>⚠️ Session-based analysis without authentication</small>
        </div>
      </div>
    )
  }

  return (
    <div className="session-analytics">
      <h3>Behavior Analysis</h3>
      <div className="analytics-note">
        <small>⚠️ Session-based analysis without authentication</small>
      </div>
      
      <div className="sessions-table-container">
        <table className="sessions-table">
          <thead>
            <tr>
              <th>Session ID</th>
              <th>Total</th>
              <th>Malicious</th>
              <th>Suspicious</th>
              <th>Last activity</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.session_id}>
                <td>
                  <code className="session-id">
                    {session.session_id.substring(0, 8)}...
                  </code>
                </td>
                <td>{session.total_requests}</td>
                <td>
                  <span className={`count-badge malicious ${session.malicious_count > 0 ? 'active' : ''}`}>
                    {session.malicious_count}
                  </span>
                </td>
                <td>
                  <span className={`count-badge suspicious ${session.suspicious_count > 0 ? 'active' : ''}`}>
                    {session.suspicious_count}
                  </span>
                </td>
                <td className="last-seen">{formatLastSeen(session.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

