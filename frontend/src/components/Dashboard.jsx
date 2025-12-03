import { useState, useEffect, useCallback } from 'react'
import { useWebSocket, fetchAPI } from '../services/websocket'
import SimplifiedChat from './SimplifiedChat'
import ExecutiveKPIs from './ExecutiveKPIs'
import PromptExplorer from './PromptExplorer'
import SecurityCharts from './SecurityCharts'
import PerformanceCharts from './PerformanceCharts'
import SessionAnalytics from './SessionAnalytics'
import RecentRequestsTable from './RecentRequestsTable'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [requests, setRequests] = useState([])
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [initialLoadComplete, setInitialLoadComplete] = useState(false)

  // WebSocket connection
  const handleWebSocketMessage = useCallback((data) => {
    // Add new request to the list
    if (data.id && data.timestamp) {
      console.log('[Dashboard] Received new request event:', data.id)
      setRequests(prev => {
        // Avoid duplicates by checking if the ID already exists
        const exists = prev.some(req => req.id === data.id)
        if (exists) {
          console.log('[Dashboard] Request already exists, skipping:', data.id)
          return prev
        }
        
        const newRequests = [...prev, data]
        // Keep only the last 100 requests in memory
        return newRequests.slice(-100)
      })

      // Update stats incrementally (will be synced with API periodically)
      loadStats()
    }
  }, [])

  const { connectionStatus, error } = useWebSocket('/ws/dashboard', handleWebSocketMessage)

  // Load initial data
  useEffect(() => {
    loadInitialData()
  }, [])

  // Periodic stats refresh
  useEffect(() => {
    const interval = setInterval(loadStats, 10000) // Every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const loadInitialData = async () => {
    try {
      await Promise.all([
        loadStats(),
        loadRecentRequests()
      ])
      setInitialLoadComplete(true)
    } catch (err) {
      console.error('Error loading initial data:', err)
    }
  }

  const loadStats = async () => {
    try {
      const data = await fetchAPI('/api/stats')
      setStats(data)
    } catch (err) {
      console.error('Error loading stats:', err)
    }
  }

  const loadRecentRequests = async () => {
    try {
      const data = await fetchAPI('/api/recent-requests?limit=50')
      setRequests(data.requests || [])
    } catch (err) {
      console.error('Error loading recent requests:', err)
    }
  }

  // Function to manually refresh requests (can be called from SimplifiedChat)
  const refreshRequests = useCallback(async () => {
    await loadRecentRequests()
  }, [])

  if (!initialLoadComplete) {
    return (
      <div className="dashboard loading-screen">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <h2>Loading Dashboard SPG...</h2>
          <p>Initializing connections and loading data</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      {/* Connection Status Bar */}
      <div className={`connection-status ${connectionStatus}`}>
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span className="status-text">
            {connectionStatus === 'connected' ? '🟢 Connected in real time' : 
             connectionStatus === 'connecting' ? '🟡 Connecting...' :
             connectionStatus === 'reconnecting' ? '🟡 Reconnecting...' :
             '🔴 Disconnected'}
          </span>
        </div>
        {error && <span className="error-text">⚠️ {error}</span>}
      </div>

      {/* Main Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Left Column - Main Content */}
        <div className="dashboard-main">
          {/* Executive KPIs Row */}
          <section className="dashboard-section kpis-section">
            <ExecutiveKPIs stats={stats} />
          </section>

          {/* Charts Row */}
          <div className="charts-row">
            <section className="dashboard-section security-section">
              <SecurityCharts 
                riskBreakdown={stats?.risk_breakdown} 
                requests={requests}
              />
            </section>

            <section className="dashboard-section performance-section">
              <PerformanceCharts 
                avgLatency={stats?.avg_latency_ms}
                requests={requests}
              />
            </section>
          </div>

          {/* Session Analytics */}
          <section className="dashboard-section session-section">
            <SessionAnalytics />
          </section>

          {/* Recent Requests Table */}
          <section className="dashboard-section table-section">
            <RecentRequestsTable 
              requests={requests}
              onSelectRequest={setSelectedRequest}
            />
          </section>
        </div>

        {/* Right Column - Chat Sidebar */}
        <div className="dashboard-sidebar">
          <SimplifiedChat onMessageSent={refreshRequests} />
        </div>
      </div>

      {/* Prompt Explorer Modal */}
      {selectedRequest && (
        <PromptExplorer 
          request={selectedRequest}
          onClose={() => setSelectedRequest(null)}
        />
      )}
    </div>
  )
}

