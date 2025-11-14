import { useState } from 'react'

export default function MetricsPanel({ data }) {
  const [expanded, setExpanded] = useState(true)
  
  if (!data || !data.ml_detectors) return null

  const getRiskColor = (level) => {
    const colors = {
      low: '#10b981',
      medium: '#f59e0b',
      high: '#ef4444',
      critical: '#dc2626'
    }
    return colors[level] || '#6b7280'
  }

  const getStatusColor = (status) => {
    const colors = {
      pass: '#10b981',
      warn: '#f59e0b',
      block: '#ef4444'
    }
    return colors[status] || '#6b7280'
  }

  const getStatusIcon = (status) => {
    const icons = {
      pass: '✓',
      warn: '⚠',
      block: '✕'
    }
    return icons[status] || '•'
  }

  return (
    <div className="metrics-panel">
      <div className="metrics-header" onClick={() => setExpanded(!expanded)}>
        <span className="metrics-title">
          📊 Analysis Details
        </span>
        <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
      </div>
      
      {expanded && (
        <div className="metrics-content">
          {/* Risk Level Badge */}
          {data.policy && (
            <div className="risk-badge-container">
              <div 
                className="risk-badge" 
                style={{ 
                  background: getRiskColor(data.policy.risk_level),
                  color: '#fff'
                }}
              >
                Risk Level: {data.policy.risk_level.toUpperCase()}
              </div>
              {data.policy.confidence !== undefined && (
                <div className="confidence-text">
                  Confidence: {(data.policy.confidence * 100).toFixed(0)}%
                </div>
              )}
            </div>
          )}

          {/* ML Detectors */}
          <div className="metrics-section">
            <div className="section-title">🤖 ML Detectors</div>
            <div className="detectors-grid">
              {data.ml_detectors.map((detector, idx) => (
                <div key={idx} className="detector-card">
                  <div className="detector-header">
                    <span className="detector-name">{detector.name}</span>
                    <span 
                      className="detector-status"
                      style={{ color: getStatusColor(detector.status) }}
                    >
                      {getStatusIcon(detector.status)}
                    </span>
                  </div>
                  <div className="detector-score">
                    <div className="score-bar-bg">
                      <div 
                        className="score-bar-fill" 
                        style={{ 
                          width: `${detector.score * 100}%`,
                          background: getStatusColor(detector.status)
                        }}
                      />
                      {detector.threshold !== null && detector.threshold !== undefined && (
                        <div 
                          className="threshold-marker"
                          style={{ left: `${detector.threshold * 100}%` }}
                        />
                      )}
                    </div>
                    <div className="score-text">
                      Score: <strong>{(detector.score * 100).toFixed(1)}%</strong>
                      {detector.threshold !== null && detector.threshold !== undefined && (
                        <span className="threshold-text">
                          / Threshold: {(detector.threshold * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="detector-latency">
                    ⏱ {detector.latency_ms.toFixed(1)}ms
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Preprocessing Info */}
          {data.preprocessing && (
            <div className="metrics-section">
              <div className="section-title">🔧 Preprocessing</div>
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Original Length:</span>
                  <span className="info-value">{data.preprocessing.original_length} chars</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Normalized Length:</span>
                  <span className="info-value">{data.preprocessing.normalized_length} chars</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Words:</span>
                  <span className="info-value">{data.preprocessing.word_count}</span>
                </div>
              </div>
            </div>
          )}

          {/* Latency Breakdown */}
          {data.latency_breakdown && (
            <div className="metrics-section">
              <div className="section-title">⏱️ Latency Breakdown</div>
              <div className="latency-chart">
                {Object.entries(data.latency_breakdown).map(([phase, ms]) => {
                  const percentage = (ms / data.total_latency_ms) * 100
                  return (
                    <div key={phase} className="latency-bar-item">
                      <div className="latency-label">
                        {phase.replace(/_/g, ' ')}
                      </div>
                      <div className="latency-bar-container">
                        <div 
                          className="latency-bar"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="latency-value">
                        {ms.toFixed(1)}ms
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="total-latency">
                <strong>Total:</strong> {data.total_latency_ms.toFixed(1)}ms
              </div>
            </div>
          )}

          {/* Policy Info */}
          {data.policy && data.policy.matched_rule && (
            <div className="metrics-section">
              <div className="section-title">📋 Policy Decision</div>
              <div className="policy-info">
                <div className="info-item">
                  <span className="info-label">Matched Rule:</span>
                  <code className="info-code">{data.policy.matched_rule}</code>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

