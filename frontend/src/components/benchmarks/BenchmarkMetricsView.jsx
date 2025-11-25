import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { fetchAPI } from '../../services/websocket'

export default function BenchmarkMetricsView({ runId }) {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (runId) {
      loadMetrics()
    }
  }, [runId])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      const data = await fetchAPI(`/api/benchmarks/metrics/${runId}`)
      setMetrics(data)
      setError(null)
    } catch (err) {
      console.error('Error loading metrics:', err)
      setError('Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading metrics...</div>
  }

  if (error) {
    return <div className="error-message">{error}</div>
  }

  if (!metrics) {
    return <div className="empty-state">No metrics available for this benchmark.</div>
  }

  // Prepare data for confusion matrix visualization
  const confusionData = [
    { name: 'True Positives', value: metrics.true_positives, color: '#10b981' },
    { name: 'False Positives', value: metrics.false_positives, color: '#f59e0b' },
    { name: 'True Negatives', value: metrics.true_negatives, color: '#3b82f6' },
    { name: 'False Negatives', value: metrics.false_negatives, color: '#ef4444' }
  ]

  // Prepare data for performance metrics chart
  const performanceData = [
    { metric: 'Precision', value: (metrics.precision * 100).toFixed(2) },
    { metric: 'Recall', value: (metrics.recall * 100).toFixed(2) },
    { metric: 'F1-Score', value: (metrics.f1_score * 100).toFixed(2) },
    { metric: 'Accuracy', value: (metrics.accuracy * 100).toFixed(2) }
  ]

  // Prepare latency data if available
  const latencyData = []
  if (metrics.avg_latency_ms) {
    latencyData.push(
      { percentile: 'Average', ms: metrics.avg_latency_ms.toFixed(2) },
      { percentile: 'P50', ms: metrics.p50_latency_ms?.toFixed(2) || 0 },
      { percentile: 'P95', ms: metrics.p95_latency_ms?.toFixed(2) || 0 },
      { percentile: 'P99', ms: metrics.p99_latency_ms?.toFixed(2) || 0 }
    )
  }

  return (
    <div className="benchmark-metrics-view">
      <h3>Benchmark Metrics</h3>

      {/* Summary Cards */}
      <div className="metrics-summary">
        <div className="metric-card">
          <div className="metric-label">F1-Score</div>
          <div className="metric-value">{(metrics.f1_score * 100).toFixed(2)}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Accuracy</div>
          <div className="metric-value">{(metrics.accuracy * 100).toFixed(2)}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Precision</div>
          <div className="metric-value">{(metrics.precision * 100).toFixed(2)}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Recall</div>
          <div className="metric-value">{(metrics.recall * 100).toFixed(2)}%</div>
        </div>
      </div>

      <div className="charts-grid">
        {/* Confusion Matrix */}
        <div className="chart-container">
          <h4>Confusion Matrix</h4>
          <div className="confusion-matrix">
            <div className="confusion-grid">
              <div className="confusion-cell header"></div>
              <div className="confusion-cell header">Predicted: Attack</div>
              <div className="confusion-cell header">Predicted: Safe</div>
              
              <div className="confusion-cell header">Actual: Attack</div>
              <div className="confusion-cell tp">
                <div className="cell-label">TP</div>
                <div className="cell-value">{metrics.true_positives}</div>
              </div>
              <div className="confusion-cell fn">
                <div className="cell-label">FN</div>
                <div className="cell-value">{metrics.false_negatives}</div>
              </div>
              
              <div className="confusion-cell header">Actual: Safe</div>
              <div className="confusion-cell fp">
                <div className="cell-label">FP</div>
                <div className="cell-value">{metrics.false_positives}</div>
              </div>
              <div className="confusion-cell tn">
                <div className="cell-label">TN</div>
                <div className="cell-value">{metrics.true_negatives}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Pie Chart of Results */}
        <div className="chart-container">
          <h4>Result Distribution</h4>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={confusionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {confusionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Metrics Bar Chart */}
        <div className="chart-container">
          <h4>Classification Metrics</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="metric" />
              <YAxis domain={[0, 100]} />
              <Tooltip formatter={(value) => `${value}%`} />
              <Legend />
              <Bar dataKey="value" fill="#3b82f6" name="Percentage (%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Latency Chart */}
        {latencyData.length > 0 && (
          <div className="chart-container">
            <h4>Latency (ms)</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={latencyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="percentile" />
                <YAxis />
                <Tooltip formatter={(value) => `${value}ms`} />
                <Legend />
                <Bar dataKey="ms" fill="#10b981" name="Latency (ms)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Key Insights */}
      <div className="insights-section">
        <h4>Key Insights</h4>
        <div className="insights-grid">
          <div className="insight-card">
            <div className="insight-icon">✅</div>
            <div className="insight-content">
              <div className="insight-title">Correct Detection</div>
              <div className="insight-value">
                {metrics.true_positives + metrics.true_negatives} / {metrics.total_samples}
              </div>
              <div className="insight-desc">
                {((metrics.true_positives + metrics.true_negatives) / metrics.total_samples * 100).toFixed(1)}% accuracy
              </div>
            </div>
          </div>

          {metrics.false_negatives > 0 && (
            <div className="insight-card warning">
              <div className="insight-icon">⚠️</div>
              <div className="insight-content">
                <div className="insight-title">False Negatives</div>
                <div className="insight-value">{metrics.false_negatives}</div>
                <div className="insight-desc">
                  Attacks that passed - security risk
                </div>
              </div>
            </div>
          )}

          {metrics.false_positives > 0 && (
            <div className="insight-card info">
              <div className="insight-icon">ℹ️</div>
              <div className="insight-content">
                <div className="insight-title">False Positives</div>
                <div className="insight-value">{metrics.false_positives}</div>
                <div className="insight-desc">
                  Users blocked incorrectly - UX impact
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

