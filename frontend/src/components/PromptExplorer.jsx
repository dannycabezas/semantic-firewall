export default function PromptExplorer({ request, onClose }) {
  if (!request) return null

  const getRiskColor = (level) => {
    const colors = {
      benign: '#10b981',
      suspicious: '#f59e0b',
      malicious: '#ef4444'
    }
    return colors[level] || '#6b7280'
  }

  const getActionColor = (action) => {
    return action === 'block' ? '#ef4444' : '#10b981'
  }

  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString('es-ES', {
        dateStyle: 'short',
        timeStyle: 'medium'
      })
    } catch {
      return timestamp
    }
  }

  const scores = request.scores || {}
  const latencies = request.latency_ms || {}
  const preprocessing = request.preprocessing_info || {}
  const detectorConfig = request.detector_config || {}
  
  // Map model names to display names
  const modelDisplayNames = {
    presidio: 'Presidio',
    onnx: 'ONNX',
    mock: 'Mock',
    detoxify: 'Detoxify',
    custom_onnx: 'Custom ONNX',
    deberta: 'DeBERTa'
  }
  
  // Get model name for each category
  const getModelName = (category) => {
    const modelKey = detectorConfig[category]
    return modelDisplayNames[modelKey] || modelKey || 'Default'
  }
  
  // Map score names to detector config keys
  const scoreToConfigKey = {
    prompt_injection: 'prompt_injection',
    pii: 'pii',
    toxicity: 'toxicity',
    heuristic: 'heuristic'
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content prompt-explorer" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🔍 Deep Prompt Inspection</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Basic Info */}
          <section className="explorer-section">
            <h3>General Information</h3>
            <div className="explorer-grid">
              <div className="explorer-item">
                <span className="explorer-label">ID:</span>
                <code className="explorer-value">{request.id}</code>
              </div>
              <div className="explorer-item">
                <span className="explorer-label">Timestamp:</span>
                <span className="explorer-value">{formatTimestamp(request.timestamp)}</span>
              </div>
              <div className="explorer-item">
                <span className="explorer-label">Risk Level:</span>
                <span 
                  className="badge" 
                  style={{ backgroundColor: getRiskColor(request.risk_level) }}
                >
                  {request.risk_level}
                </span>
              </div>
              <div className="explorer-item">
                <span className="explorer-label">Category:</span>
                <span className="badge badge-category">{request.risk_category}</span>
              </div>
              <div className="explorer-item">
                <span className="explorer-label">Action:</span>
                <span 
                  className="badge" 
                  style={{ backgroundColor: getActionColor(request.action) }}
                >
                  {request.action}
                </span>
              </div>
              {request.session_id && (
                <div className="explorer-item">
                  <span className="explorer-label">Session ID:</span>
                  <code className="explorer-value">{request.session_id}</code>
                </div>
              )}
            </div>
          </section>

          {/* Prompt and Response */}
          <section className="explorer-section">
            <h3>Prompt and Response</h3>
            <div className="explorer-text-box">
              <h4>Prompt:</h4>
              <div className="text-content">{request.prompt}</div>
            </div>
            <div className="explorer-text-box">
              <h4>Response:</h4>
              <div className="text-content">{request.response}</div>
            </div>
          </section>

          {/* ML Scores */}
          <section className="explorer-section">
            <h3>ML Model Scores</h3>
            <div className="scores-list">
              {Object.entries(scores).map(([name, score]) => {
                const configKey = scoreToConfigKey[name]
                const modelName = configKey ? getModelName(configKey) : (name === 'heuristic' ? 'Regex' : 'Default')
                return (
                  <div key={name} className="score-item">
                    <div className="score-header">
                      <div className="score-name-wrapper">
                        <span className="score-name">{name.replace(/_/g, ' ').toUpperCase()}</span>
                        {modelName && (
                          <span className="score-model-name">({modelName})</span>
                        )}
                      </div>
                      <span className="score-value">{(score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="score-bar-bg">
                      <div 
                        className="score-bar-fill"
                        style={{ 
                          width: `${score * 100}%`,
                          backgroundColor: score > 0.7 ? '#ef4444' : score > 0.4 ? '#f59e0b' : '#10b981'
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {/* Heuristics */}
          {request.heuristics && request.heuristics.length > 0 && (
            <section className="explorer-section">
              <h3>Triggered Heuristics</h3>
              <div className="heuristics-list">
                {request.heuristics.map((h, idx) => (
                  <span key={idx} className="badge badge-heuristic">{h}</span>
                ))}
              </div>
            </section>
          )}

          {/* Policy Decision */}
          {request.policy && (
            <section className="explorer-section">
              <h3>Policy Decision</h3>
              <div className="explorer-grid">
                {request.policy.matched_rule && (
                  <div className="explorer-item full-width">
                    <span className="explorer-label">Coincident Rule:</span>
                    <code className="explorer-value">{request.policy.matched_rule}</code>
                  </div>
                )}
                <div className="explorer-item">
                  <span className="explorer-label">Decision:</span>
                  <span 
                    className="badge"
                    style={{ backgroundColor: getActionColor(request.policy.decision) }}
                  >
                    {request.policy.decision}
                  </span>
                </div>
              </div>
            </section>
          )}

          {/* Latency Breakdown */}
          <section className="explorer-section">
            <h3>Latency Breakdown</h3>
            <div className="latency-breakdown">
              {Object.entries(latencies).map(([phase, ms]) => (
                <div key={phase} className="latency-item">
                  <div className="latency-header">
                    <span className="latency-name">{phase.replace(/_/g, ' ')}</span>
                    <span className="latency-value">{ms.toFixed(2)}ms</span>
                  </div>
                  <div className="latency-bar-bg">
                    <div 
                      className="latency-bar-fill"
                      style={{ 
                        width: `${(ms / Math.max(...Object.values(latencies))) * 100}%`
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Preprocessing Info */}
          {preprocessing && Object.keys(preprocessing).length > 0 && (
            <section className="explorer-section">
              <h3>Preprocessing Information</h3>
              <div className="explorer-grid">
                <div className="explorer-item">
                  <span className="explorer-label">Original Length:</span>
                  <span className="explorer-value">{preprocessing.original_length || 0} chars</span>
                </div>
                <div className="explorer-item">
                  <span className="explorer-label">Normalized Length:</span>
                  <span className="explorer-value">{preprocessing.normalized_length || 0} chars</span>
                </div>
                <div className="explorer-item">
                  <span className="explorer-label">Words:</span>
                  <span className="explorer-value">{preprocessing.word_count || 0}</span>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

