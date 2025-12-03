import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { fetchAPI } from '../../services/websocket'

// Componente para mostrar texto truncado con opción de expandir
function TruncatedText({ text, maxLength = 120 }) {
  const [expanded, setExpanded] = useState(false)
  
  if (!text) return <span className="text-muted">N/A</span>
  
  const shouldTruncate = text.length > maxLength
  const displayText = expanded || !shouldTruncate 
    ? text 
    : text.substring(0, maxLength) + '...'
  
  return (
    <div className="truncated-text-container">
      <span className="truncated-text">{displayText}</span>
      {shouldTruncate && (
        <button 
          className="expand-text-btn"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

// Componente para mostrar un delta con color según polaridad
function DeltaValue({ delta, isPercentMetric = false }) {
  if (!delta || delta.value === null || delta.value === undefined) {
    return <span className="delta-neutral">—</span>
  }
  
  const sign = delta.value > 0 ? '+' : ''
  const value = typeof delta.value === 'number' 
    ? (isPercentMetric ? (delta.value * 100).toFixed(2) : delta.value.toFixed(2))
    : delta.value
  const percent = typeof delta.percent === 'number' 
    ? `${delta.percent > 0 ? '+' : ''}${delta.percent.toFixed(1)}%` 
    : ''
  
  const polarityClass = delta.polarity === 'positive' 
    ? 'delta-positive' 
    : delta.polarity === 'negative' 
      ? 'delta-negative' 
      : 'delta-neutral'
  
  const icon = delta.polarity === 'positive' ? '↑' : delta.polarity === 'negative' ? '↓' : '→'
  
  return (
    <span className={`delta-badge ${polarityClass}`}>
      <span className="delta-icon">{icon}</span>
      <span className="delta-value">{sign}{value}</span>
      {percent && <span className="delta-percent">({percent})</span>}
    </span>
  )
}

// Componente para sección colapsable
function CollapsibleSection({ title, subtitle, count, type, defaultOpen = false, children }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  const typeColors = {
    critical: 'section-critical',
    warning: 'section-warning', 
    success: 'section-success',
    info: 'section-info'
  }
  
  return (
    <div className={`collapsible-section ${typeColors[type] || ''}`}>
      <button 
        className="collapsible-header"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="collapsible-title-area">
          <span className="collapsible-arrow">{isOpen ? '▼' : '▶'}</span>
          <span className="collapsible-title">{title}</span>
          {count !== undefined && (
            <span className={`count-badge count-${type}`}>{count}</span>
          )}
        </div>
        {subtitle && <span className="collapsible-subtitle">{subtitle}</span>}
      </button>
      {isOpen && <div className="collapsible-content">{children}</div>}
    </div>
  )
}

// Componente para mostrar una muestra individual
function SampleCard({ sample, type }) {
  const [expanded, setExpanded] = useState(false)
  
  const typeStyles = {
    critical: { border: 'var(--accent-red)', bg: 'rgba(239, 68, 68, 0.1)', icon: '🚨' },
    warning: { border: 'var(--accent-yellow)', bg: 'rgba(245, 158, 11, 0.1)', icon: '⚠️' },
    success: { border: 'var(--accent-green)', bg: 'rgba(16, 185, 129, 0.1)', icon: '✅' }
  }
  
  const style = typeStyles[type] || typeStyles.warning
  
  return (
    <div 
      className="sample-card"
      style={{ borderLeftColor: style.border, backgroundColor: style.bg }}
    >
      <div className="sample-card-header">
        <div className="sample-card-badges">
          <span className="sample-icon">{style.icon}</span>
          <span className="sample-index-badge">#{sample.sample_index}</span>
          <span className={`sample-label-badge label-${sample.expected_label}`}>
            {sample.expected_label}
          </span>
        </div>
        <button 
          className="sample-expand-btn"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      
      <div className={`sample-card-body ${expanded ? 'expanded' : ''}`}>
        <div className="sample-prompt">
          {expanded 
            ? sample.input_text 
            : (sample.input_text?.length > 150 
                ? sample.input_text.substring(0, 150) + '...' 
                : sample.input_text)
          }
        </div>
      </div>
      
      {expanded && sample.ml_scores && (
        <div className="sample-card-details">
          <div className="sample-scores-grid">
            {sample.ml_scores.prompt_injection_score !== undefined && (
              <div className="sample-score-item">
                <span className="score-name">Injection</span>
                <span className={`score-val ${sample.ml_scores.prompt_injection_score > 0.5 ? 'high' : ''}`}>
                  {(sample.ml_scores.prompt_injection_score * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {sample.ml_scores.toxicity_score !== undefined && (
              <div className="sample-score-item">
                <span className="score-name">Toxicity</span>
                <span className={`score-val ${sample.ml_scores.toxicity_score > 0.5 ? 'high' : ''}`}>
                  {(sample.ml_scores.toxicity_score * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {sample.ml_scores.pii_score !== undefined && (
              <div className="sample-score-item">
                <span className="score-name">PII</span>
                <span className={`score-val ${sample.ml_scores.pii_score > 0.5 ? 'high' : ''}`}>
                  {(sample.ml_scores.pii_score * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function BenchmarkComparison({ baselineRunId, candidateRunIds, datasetInfo }) {
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!baselineRunId || !candidateRunIds || candidateRunIds.length < 1) return
    loadComparison()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baselineRunId, JSON.stringify(candidateRunIds)])

  const loadComparison = async () => {
    try {
      setLoading(true)
      const query = new URLSearchParams({
        baseline_run_id: baselineRunId,
        candidate_run_ids: candidateRunIds.join(',')
      }).toString()
      const data = await fetchAPI(`/api/benchmarks/compare?${query}`)
      setComparison(data)
      setError(null)
    } catch (err) {
      console.error('Error loading benchmark comparison:', err)
      setError('Failed to load benchmark comparison')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="comparison-loading">
        <div className="loading-spinner"></div>
        <p>Loading comparison data...</p>
      </div>
    )
  }

  if (error) {
    return <div className="error-message">{error}</div>
  }

  if (!comparison) {
    return <div className="empty-state">No comparison data available.</div>
  }

  const baseline = comparison.baseline
  const candidates = comparison.candidates || []
  const datasetLabel =
    datasetInfo?.dataset_name && datasetInfo?.dataset_split
      ? `${datasetInfo.dataset_name} (${datasetInfo.dataset_split})`
      : comparison.dataset_info
      ? `${comparison.dataset_info.dataset_name} (${comparison.dataset_info.dataset_split})`
      : 'N/A'

  const buildMetricBarData = (candidate) => {
    const cm = candidate.metrics
    const bm = baseline.metrics
    if (!cm || !bm) return []
    return [
      { metric: 'F1', baseline: (bm.f1_score || 0) * 100, candidate: (cm.f1_score || 0) * 100 },
      { metric: 'Precision', baseline: (bm.precision || 0) * 100, candidate: (cm.precision || 0) * 100 },
      { metric: 'Recall', baseline: (bm.recall || 0) * 100, candidate: (cm.recall || 0) * 100 },
      { metric: 'Accuracy', baseline: (bm.accuracy || 0) * 100, candidate: (cm.accuracy || 0) * 100 }
    ]
  }

  const buildLatencyBarData = (candidate) => {
    const cm = candidate.metrics
    const bm = baseline.metrics
    if (!cm || !bm) return []
    return [
      { metric: 'Avg', baseline: bm.avg_latency_ms || 0, candidate: cm.avg_latency_ms || 0 },
      { metric: 'P50', baseline: bm.p50_latency_ms || 0, candidate: cm.p50_latency_ms || 0 },
      { metric: 'P95', baseline: bm.p95_latency_ms || 0, candidate: cm.p95_latency_ms || 0 },
      { metric: 'P99', baseline: bm.p99_latency_ms || 0, candidate: cm.p99_latency_ms || 0 }
    ]
  }

  const formatRunId = (runId) => runId ? runId.substring(0, 8) + '...' : 'N/A'

  return (
    <div className="benchmark-comparison">
      {/* Header */}
      <div className="comparison-header">
        <div className="comparison-title-row">
          <h2>📊 Benchmark Comparison</h2>
          <span className="dataset-badge">{datasetLabel}</span>
        </div>
      </div>

      {/* Baseline Card */}
      <div className="baseline-card">
        <div className="baseline-card-header">
          <div className="baseline-title">
            <span className="baseline-icon">🎯</span>
            <span>BASELINE</span>
          </div>
          <span className="run-id-badge">{formatRunId(baseline.run_id)}</span>
        </div>
        <div className="baseline-metrics-row">
          <div className="baseline-metric">
            <span className="metric-label">F1-Score</span>
            <span className="metric-value">{(baseline.metrics.f1_score * 100).toFixed(1)}%</span>
          </div>
          <div className="baseline-metric">
            <span className="metric-label">Precision</span>
            <span className="metric-value">{(baseline.metrics.precision * 100).toFixed(1)}%</span>
          </div>
          <div className="baseline-metric">
            <span className="metric-label">Recall</span>
            <span className="metric-value">{(baseline.metrics.recall * 100).toFixed(1)}%</span>
          </div>
          <div className="baseline-metric">
            <span className="metric-label">Accuracy</span>
            <span className="metric-value">{(baseline.metrics.accuracy * 100).toFixed(1)}%</span>
          </div>
          <div className="baseline-metric">
            <span className="metric-label">Avg Latency</span>
            <span className="metric-value">{baseline.metrics.avg_latency_ms?.toFixed(0) || 'N/A'} ms</span>
          </div>
        </div>
      </div>

      {/* Candidates */}
      {candidates.map((candidate) => {
        const deltas = candidate.deltas || {}
        const changes = candidate.sample_changes || {}
        const regressions = changes.regressions || {}
        const improvements = changes.improvements || {}
        const summary = changes.summary || {}

        const criticalCount = (regressions.critical || []).length
        const newFpCount = (regressions.new_false_positives || []).length
        const newDetectionsCount = (improvements.new_detections || []).length
        const fixedFpCount = (improvements.fixed_false_positives || []).length
        const totalRegressions = criticalCount + newFpCount
        const totalImprovements = newDetectionsCount + fixedFpCount

        const metricBarData = buildMetricBarData(candidate)
        const latencyBarData = buildLatencyBarData(candidate)

        return (
          <div key={candidate.run_id} className="candidate-section">
            {/* Candidate Header */}
            <div className="candidate-header-card">
              <div className="candidate-header-top">
                <div className="candidate-title">
                  <span className="candidate-icon">🔬</span>
                  <span>CANDIDATE</span>
                  <span className="run-id-badge">{formatRunId(candidate.run_id)}</span>
                </div>
              </div>
              
              {/* Quick Summary Cards */}
              <div className="summary-cards-row">
                <div className={`summary-card ${totalRegressions > 0 ? 'negative' : 'neutral'}`}>
                  <div className="summary-card-icon">📉</div>
                  <div className="summary-card-content">
                    <span className="summary-card-value">{totalRegressions}</span>
                    <span className="summary-card-label">Regressions</span>
                  </div>
                </div>
                <div className={`summary-card ${totalImprovements > 0 ? 'positive' : 'neutral'}`}>
                  <div className="summary-card-icon">📈</div>
                  <div className="summary-card-content">
                    <span className="summary-card-value">{totalImprovements}</span>
                    <span className="summary-card-label">Improvements</span>
                  </div>
                </div>
                <div className={`summary-card ${summary.net_change > 0 ? 'positive' : summary.net_change < 0 ? 'negative' : 'neutral'}`}>
                  <div className="summary-card-icon">⚖️</div>
                  <div className="summary-card-content">
                    <span className="summary-card-value">
                      {summary.net_change > 0 ? '+' : ''}{summary.net_change || 0}
                    </span>
                    <span className="summary-card-label">Net Change</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Metrics Comparison Tables */}
            <div className="metrics-tables-grid">
              {/* Classification Metrics */}
              <div className="metrics-table-card">
                <h4>📊 Classification Metrics</h4>
                <table className="comparison-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Baseline</th>
                      <th>Candidate</th>
                      <th>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="metric-name">F1-Score</td>
                      <td className="metric-baseline">{(baseline.metrics.f1_score * 100).toFixed(2)}%</td>
                      <td className="metric-candidate">{(candidate.metrics.f1_score * 100).toFixed(2)}%</td>
                      <td><DeltaValue delta={deltas.f1_score} isPercentMetric={true} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">Precision</td>
                      <td className="metric-baseline">{(baseline.metrics.precision * 100).toFixed(2)}%</td>
                      <td className="metric-candidate">{(candidate.metrics.precision * 100).toFixed(2)}%</td>
                      <td><DeltaValue delta={deltas.precision} isPercentMetric={true} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">Recall</td>
                      <td className="metric-baseline">{(baseline.metrics.recall * 100).toFixed(2)}%</td>
                      <td className="metric-candidate">{(candidate.metrics.recall * 100).toFixed(2)}%</td>
                      <td><DeltaValue delta={deltas.recall} isPercentMetric={true} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">Accuracy</td>
                      <td className="metric-baseline">{(baseline.metrics.accuracy * 100).toFixed(2)}%</td>
                      <td className="metric-candidate">{(candidate.metrics.accuracy * 100).toFixed(2)}%</td>
                      <td><DeltaValue delta={deltas.accuracy} isPercentMetric={true} /></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Errors & Latency */}
              <div className="metrics-table-card">
                <h4>⚡ Errors & Latency</h4>
                <table className="comparison-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Baseline</th>
                      <th>Candidate</th>
                      <th>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="metric-name">False Positives</td>
                      <td className="metric-baseline">{baseline.metrics.false_positives}</td>
                      <td className="metric-candidate">{candidate.metrics.false_positives}</td>
                      <td><DeltaValue delta={deltas.false_positives} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">False Negatives</td>
                      <td className="metric-baseline">{baseline.metrics.false_negatives}</td>
                      <td className="metric-candidate">{candidate.metrics.false_negatives}</td>
                      <td><DeltaValue delta={deltas.false_negatives} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">Avg Latency</td>
                      <td className="metric-baseline">{baseline.metrics.avg_latency_ms?.toFixed(1)} ms</td>
                      <td className="metric-candidate">{candidate.metrics.avg_latency_ms?.toFixed(1)} ms</td>
                      <td><DeltaValue delta={deltas.avg_latency_ms} /></td>
                    </tr>
                    <tr>
                      <td className="metric-name">P95 Latency</td>
                      <td className="metric-baseline">{baseline.metrics.p95_latency_ms?.toFixed(1)} ms</td>
                      <td className="metric-candidate">{candidate.metrics.p95_latency_ms?.toFixed(1)} ms</td>
                      <td><DeltaValue delta={deltas.p95_latency_ms} /></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Charts */}
            <div className="comparison-charts-grid">
              <div className="comparison-chart-card">
                <h4>Classification Metrics Comparison</h4>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={metricBarData} barGap={8}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="metric" stroke="var(--text-secondary)" />
                    <YAxis domain={[0, 100]} stroke="var(--text-secondary)" />
                    <Tooltip 
                      formatter={(value) => `${value.toFixed(2)}%`}
                      contentStyle={{ 
                        backgroundColor: 'var(--bg-secondary)', 
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="baseline" fill="#6b7280" name="Baseline" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="candidate" fill="#3b82f6" name="Candidate" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="comparison-chart-card">
                <h4>Latency Comparison (ms)</h4>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={latencyBarData} barGap={8}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="metric" stroke="var(--text-secondary)" />
                    <YAxis stroke="var(--text-secondary)" />
                    <Tooltip 
                      formatter={(value) => `${value.toFixed(2)} ms`}
                      contentStyle={{ 
                        backgroundColor: 'var(--bg-secondary)', 
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Bar dataKey="baseline" fill="#6b7280" name="Baseline" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="candidate" fill="#10b981" name="Candidate" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Sample Changes - Collapsible Sections */}
            <div className="sample-changes-section">
              <h3>🔄 State Changes (Sample Analysis)</h3>
              
              <div className="sample-changes-grid">
                {/* Regressions Column */}
                <div className="sample-changes-column">
                  <div className="column-header regression-header">
                    <span className="column-icon">⚠️</span>
                    <span className="column-title">Regressions</span>
                    <span className="column-count">{totalRegressions} total</span>
                  </div>

                  <CollapsibleSection
                    title="Critical Regressions"
                    subtitle="Attacks now passing (TP → FN)"
                    count={criticalCount}
                    type="critical"
                    defaultOpen={criticalCount > 0 && criticalCount <= 5}
                  >
                    {criticalCount === 0 ? (
                      <div className="no-items-message">No critical regressions found 🎉</div>
                    ) : (
                      <div className="samples-list">
                        {(regressions.critical || []).slice(0, 10).map((item) => (
                          <SampleCard key={item.sample_index} sample={item} type="critical" />
                        ))}
                        {criticalCount > 10 && (
                          <div className="more-items-badge">
                            +{criticalCount - 10} more critical regressions
                          </div>
                        )}
                      </div>
                    )}
                  </CollapsibleSection>

                  <CollapsibleSection
                    title="New False Positives"
                    subtitle="Legit requests now blocked (TN → FP)"
                    count={newFpCount}
                    type="warning"
                    defaultOpen={newFpCount > 0 && newFpCount <= 5}
                  >
                    {newFpCount === 0 ? (
                      <div className="no-items-message">No new false positives 🎉</div>
                    ) : (
                      <div className="samples-list">
                        {(regressions.new_false_positives || []).slice(0, 10).map((item) => (
                          <SampleCard key={item.sample_index} sample={item} type="warning" />
                        ))}
                        {newFpCount > 10 && (
                          <div className="more-items-badge">
                            +{newFpCount - 10} more false positives
                          </div>
                        )}
                      </div>
                    )}
                  </CollapsibleSection>
                </div>

                {/* Improvements Column */}
                <div className="sample-changes-column">
                  <div className="column-header improvement-header">
                    <span className="column-icon">✨</span>
                    <span className="column-title">Improvements</span>
                    <span className="column-count">{totalImprovements} total</span>
                  </div>

                  <CollapsibleSection
                    title="New Detections"
                    subtitle="Attacks now blocked (FN → TP)"
                    count={newDetectionsCount}
                    type="success"
                    defaultOpen={newDetectionsCount > 0 && newDetectionsCount <= 5}
                  >
                    {newDetectionsCount === 0 ? (
                      <div className="no-items-message">No new detections</div>
                    ) : (
                      <div className="samples-list">
                        {(improvements.new_detections || []).slice(0, 10).map((item) => (
                          <SampleCard key={item.sample_index} sample={item} type="success" />
                        ))}
                        {newDetectionsCount > 10 && (
                          <div className="more-items-badge success">
                            +{newDetectionsCount - 10} more detections
                          </div>
                        )}
                      </div>
                    )}
                  </CollapsibleSection>

                  <CollapsibleSection
                    title="Fixed False Positives"
                    subtitle="Legit requests now allowed (FP → TN)"
                    count={fixedFpCount}
                    type="success"
                    defaultOpen={fixedFpCount > 0 && fixedFpCount <= 5}
                  >
                    {fixedFpCount === 0 ? (
                      <div className="no-items-message">No fixed false positives</div>
                    ) : (
                      <div className="samples-list">
                        {(improvements.fixed_false_positives || []).slice(0, 10).map((item) => (
                          <SampleCard key={item.sample_index} sample={item} type="success" />
                        ))}
                        {fixedFpCount > 10 && (
                          <div className="more-items-badge success">
                            +{fixedFpCount - 10} more fixed
                          </div>
                        )}
                      </div>
                    )}
                  </CollapsibleSection>
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
