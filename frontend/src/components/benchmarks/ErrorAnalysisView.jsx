import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/websocket'

export default function ErrorAnalysisView({ runId }) {
  const [errors, setErrors] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('false_negatives') // Start with most critical
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (runId) {
      loadErrors()
    }
  }, [runId])

  const loadErrors = async () => {
    try {
      setLoading(true)
      const data = await fetchAPI(`/api/benchmarks/errors/${runId}`)
      setErrors(data)
      setError(null)
    } catch (err) {
      console.error('Error loading error analysis:', err)
      setError('Failed to load error analysis')
    } finally {
      setLoading(false)
    }
  }

  const filterErrors = (errorList) => {
    if (!searchTerm) return errorList
    return errorList.filter(err => 
      err.input_text.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }

  const exportToCSV = (data, filename) => {
    const headers = ['Sample Index', 'Input Text', 'Expected', 'Predicted', 'Reason', 'ML Scores']
    const rows = data.map(item => {
      const analysis = JSON.parse(item.analysis_details || '{}')
      const mlScores = analysis.ml_signals ? 
        `PI:${analysis.ml_signals.prompt_injection_score?.toFixed(2) || 0} ` +
        `TOX:${analysis.ml_signals.toxicity_score?.toFixed(2) || 0} ` +
        `PII:${analysis.ml_signals.pii_score?.toFixed(2) || 0}` : 'N/A'
      
      return [
        item.sample_index,
        `"${item.input_text.replace(/"/g, '""')}"`,
        item.expected_label,
        item.predicted_label,
        `"${(analysis.reason || 'N/A').replace(/"/g, '""')}"`,
        mlScores
      ]
    })

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (loading) {
    return <div className="loading">Loading error analysis...</div>
  }

  if (error) {
    return <div className="error-message">{error}</div>
  }

  if (!errors) {
    return <div className="empty-state">No error data available.</div>
  }

  const falseNegatives = errors.false_negatives || []
  const falsePositives = errors.false_positives || []
  const filteredFN = filterErrors(falseNegatives)
  const filteredFP = filterErrors(falsePositives)

  const renderErrorTable = (errorList, type) => {
    if (errorList.length === 0) {
      return (
        <div className="empty-state">
          ✅ No {type === 'FN' ? 'false negatives' : 'false positives'} in this benchmark
        </div>
      )
    }

    return (
      <div className="error-table-container">
        <div className="table-actions">
          <button
            className="btn-secondary"
            onClick={() => exportToCSV(
              type === 'FN' ? falseNegatives : falsePositives,
              `${type === 'FN' ? 'false_negatives' : 'false_positives'}_${runId}.csv`
            )}
          >
            📥 Export to CSV
          </button>
          <div className="search-box">
            <input
              type="text"
              placeholder="Search in prompts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <table className="error-analysis-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Prompt</th>
              <th>Scores ML</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {errorList.map((item) => {
              const analysis = JSON.parse(item.analysis_details || '{}')
              const mlSignals = analysis.ml_signals || {}
              
              return (
                <tr key={item.id}>
                  <td>{item.sample_index}</td>
                  <td className="prompt-cell">
                    <div className="prompt-text">{item.input_text}</div>
                  </td>
                  <td className="scores-cell">
                    {mlSignals && (
                      <div className="ml-scores">
                        <div className="score-item">
                          <span className="score-label">PI:</span>
                          <span className={`score-value ${mlSignals.prompt_injection_score > 0.7 ? 'high' : ''}`}>
                            {mlSignals.prompt_injection_score?.toFixed(3) || 0}
                          </span>
                        </div>
                        <div className="score-item">
                          <span className="score-label">TOX:</span>
                          <span className={`score-value ${mlSignals.toxicity_score > 0.7 ? 'high' : ''}`}>
                            {mlSignals.toxicity_score?.toFixed(3) || 0}
                          </span>
                        </div>
                        <div className="score-item">
                          <span className="score-label">PII:</span>
                          <span className={`score-value ${mlSignals.pii_score > 0.7 ? 'high' : ''}`}>
                            {mlSignals.pii_score?.toFixed(3) || 0}
                          </span>
                        </div>
                        {mlSignals.heuristic_blocked && (
                          <div className="score-item">
                            <span className="heuristic-badge">🔒 Heuristic</span>
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="reason-cell">
                    {analysis.reason || 'N/A'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="error-analysis-view">
      <h3>Error Analysis</h3>

      <div className="error-summary">
        <div className="error-summary-card critical">
          <div className="summary-icon">❌</div>
          <div className="summary-content">
            <div className="summary-label">False Negatives</div>
            <div className="summary-value">{falseNegatives.length}</div>
            <div className="summary-desc">Attacks that passed - CRITICAL</div>
          </div>
        </div>
        <div className="error-summary-card warning">
          <div className="summary-icon">⚠️</div>
          <div className="summary-content">
            <div className="summary-label">False Positives</div>
            <div className="summary-value">{falsePositives.length}</div>
            <div className="summary-desc">Legitimate users blocked</div>
          </div>
        </div>
      </div>

      <div className="error-tabs">
        <button
          className={`tab-button ${activeTab === 'false_negatives' ? 'active' : ''}`}
          onClick={() => setActiveTab('false_negatives')}
        >
          False Negatives ({falseNegatives.length})
        </button>
        <button
          className={`tab-button ${activeTab === 'false_positives' ? 'active' : ''}`}
          onClick={() => setActiveTab('false_positives')}
        >
          False Positives ({falsePositives.length})
        </button>
      </div>

      <div className="error-content">
        {activeTab === 'false_negatives' && renderErrorTable(filteredFN, 'FN')}
        {activeTab === 'false_positives' && renderErrorTable(filteredFP, 'FP')}
      </div>
    </div>
  )
}

