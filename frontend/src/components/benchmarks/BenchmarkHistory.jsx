import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/websocket'

export default function BenchmarkHistory({ onSelectRun, refreshTrigger }) {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadRuns()
  }, [refreshTrigger])

  const loadRuns = async () => {
    try {
      setLoading(true)
      const data = await fetchAPI('/api/benchmarks/runs?limit=50')
      setRuns(data.runs || [])
      setError(null)
    } catch (err) {
      console.error('Error loading benchmark runs:', err)
      setError('Failed to load benchmark history')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A'
    const date = new Date(isoString)
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (start, end) => {
    if (!start || !end) return 'N/A'
    const duration = (new Date(end) - new Date(start)) / 1000
    if (duration < 60) return `${duration.toFixed(0)}s`
    return `${(duration / 60).toFixed(1)}min`
  }

  const getStatusBadge = (status) => {
    const badges = {
      completed: '✅ Completed',
      running: '🔄 Running',
      failed: '❌ Failed',
      cancelled: '⚠️ Cancelled'
    }
    return badges[status] || status
  }

  if (loading) {
    return <div className="loading">Loading history...</div>
  }

  if (error) {
    return <div className="error-message">{error}</div>
  }

  if (runs.length === 0) {
    return (
      <div className="empty-state">
        <p>No benchmarks executed yet.</p>
        <p>Start one in the "New Execution" tab.</p>
      </div>
    )
  }

  return (
    <div className="benchmark-history">
      <h3>Benchmark History</h3>
      
      <div className="table-container">
        <table className="benchmark-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Dataset</th>
              <th>Split</th>
              <th>Samples</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className={`status-${run.status}`}>
                <td>{formatDate(run.start_time)}</td>
                <td className="dataset-name">{run.dataset_name}</td>
                <td>{run.dataset_split}</td>
                <td>
                  {run.processed_samples} / {run.total_samples}
                </td>
                <td>{formatDuration(run.start_time, run.end_time)}</td>
                <td>
                  <span className={`status-badge status-${run.status}`}>
                    {getStatusBadge(run.status)}
                  </span>
                </td>
                <td>
                  <button
                    className="btn-secondary btn-small"
                    onClick={() => onSelectRun(run.id)}
                    disabled={run.status === 'running'}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

