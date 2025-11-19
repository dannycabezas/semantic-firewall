import { useState, useEffect, useRef } from 'react'

export default function RecentRequestsTable({ requests, onSelectRequest }) {
  const [filter, setFilter] = useState('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const tableBodyRef = useRef(null)

  useEffect(() => {
    if (autoScroll && tableBodyRef.current) {
      tableBodyRef.current.scrollTop = tableBodyRef.current.scrollHeight
    }
  }, [requests, autoScroll])

  const filteredRequests = requests.filter(req => {
    if (filter === 'all') return true
    if (filter === 'blocked') return req.action === 'block'
    if (filter === 'suspicious') return req.risk_level === 'suspicious' || req.risk_level === 'malicious'
    return true
  })

  const getRiskBadgeClass = (level) => {
    return `risk-badge risk-${level}`
  }

  const getActionBadgeClass = (action) => {
    return `action-badge action-${action}`
  }

  const getCategoryBadgeClass = (category) => {
    return `category-badge category-${category}`
  }

  const formatTimeAgo = (timestamp) => {
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffSecs = Math.floor(diffMs / 1000)
      
      if (diffSecs < 5) return 'Now'
      if (diffSecs < 60) return `${diffSecs}s ago`
      const diffMins = Math.floor(diffSecs / 60)
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      return `${diffHours}h ago`
    } catch {
      return 'N/A'
    }
  }

  const truncateText = (text, maxLength = 50) => {
    if (!text) return 'N/A'
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  return (
    <div className="recent-requests-table">
      <div className="table-header">
        <h3>Recent Requests</h3>
        <div className="table-controls">
          <div className="filter-buttons">
            <button 
              className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({requests.length})
            </button>
            <button 
              className={`filter-btn ${filter === 'blocked' ? 'active' : ''}`}
              onClick={() => setFilter('blocked')}
            >
              Blocked ({requests.filter(r => r.action === 'block').length})
            </button>
            <button 
              className={`filter-btn ${filter === 'suspicious' ? 'active' : ''}`}
              onClick={() => setFilter('suspicious')}
            >
              Suspicious ({requests.filter(r => r.risk_level === 'suspicious' || r.risk_level === 'malicious').length})
            </button>
          </div>
          <label className="auto-scroll-toggle">
            <input 
              type="checkbox" 
              checked={autoScroll} 
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div className="table-container" ref={tableBodyRef}>
        {filteredRequests.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📭</div>
            <p>No requests to show</p>
            <small>Requests will appear here in real time</small>
          </div>
        ) : (
          <table className="requests-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Prompt</th>
                <th>Risk</th>
                <th>Category</th>
                <th>Action</th>
                <th>Latency</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredRequests.map((req) => (
                <tr 
                  key={req.id} 
                  className="request-row"
                  onClick={() => onSelectRequest && onSelectRequest(req)}
                >
                  <td className="timestamp-col">
                    {formatTimeAgo(req.timestamp)}
                  </td>
                  <td className="prompt-col">
                    <span className="prompt-text" title={req.prompt}>
                      {truncateText(req.prompt, 60)}
                    </span>
                  </td>
                  <td>
                    <span className={getRiskBadgeClass(req.risk_level)}>
                      {req.risk_level}
                    </span>
                  </td>
                  <td>
                    <span className={getCategoryBadgeClass(req.risk_category)}>
                      {req.risk_category}
                    </span>
                  </td>
                  <td>
                    <span className={getActionBadgeClass(req.action)}>
                      {req.action}
                    </span>
                  </td>
                  <td className="latency-col">
                    {req.latency_ms?.total ? `${req.latency_ms.total.toFixed(0)}ms` : 'N/A'}
                  </td>
                  <td className="expand-col">
                    <button 
                      className="expand-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectRequest && onSelectRequest(req)
                      }}
                      title="View details"
                    >
                      🔍
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="table-footer">
        <span className="row-count">
          Showing {filteredRequests.length} of {requests.length} requests
        </span>
      </div>
    </div>
  )
}

