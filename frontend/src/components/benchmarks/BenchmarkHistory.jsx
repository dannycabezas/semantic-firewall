import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/websocket'

export default function BenchmarkHistory({
  onSelectRun,
  refreshTrigger,
  onSelectionChange,
  onRequestCompare
}) {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedIds, setSelectedIds] = useState([])
  const [baselineId, setBaselineId] = useState(null)
  const [datasetFilter, setDatasetFilter] = useState(null)

  useEffect(() => {
    loadRuns()
  }, [refreshTrigger])

  // Notify parent whenever selection changes
  useEffect(() => {
    if (!onSelectionChange) return

    if (!baselineId || selectedIds.length < 1 || !datasetFilter) {
      onSelectionChange({
        baselineRunId: null,
        selectedRunIds: [],
        datasetName: null,
        datasetSplit: null
      })
      return
    }

    onSelectionChange({
      baselineRunId: baselineId,
      selectedRunIds: selectedIds,
      datasetName: datasetFilter.dataset_name,
      datasetSplit: datasetFilter.dataset_split
    })
  }, [baselineId, selectedIds, datasetFilter, onSelectionChange])

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

  const isRunSelectable = (run) => {
    // Only completed runs can be compared
    if (run.status !== 'completed') return false
    if (!datasetFilter) return true
    return (
      run.dataset_name === datasetFilter.dataset_name &&
      run.dataset_split === datasetFilter.dataset_split
    )
  }

  const handleToggleSelect = (run) => {
    const isSelected = selectedIds.includes(run.id)

    if (isSelected) {
      const nextSelected = selectedIds.filter((id) => id !== run.id)
      setSelectedIds(nextSelected)

      // If we removed the baseline, assign a new one or clear filter
      if (baselineId === run.id) {
        const newBaseline = nextSelected.length > 0 ? nextSelected[0] : null
        setBaselineId(newBaseline)
        if (!newBaseline) {
          setDatasetFilter(null)
        }
      }
      return
    }

    // Selecting a new run
    if (!datasetFilter) {
      // First selection defines the dataset filter and becomes baseline
      setDatasetFilter({
        dataset_name: run.dataset_name,
        dataset_split: run.dataset_split
      })
      setSelectedIds([run.id])
      setBaselineId(run.id)
    } else if (isRunSelectable(run)) {
      setSelectedIds([...selectedIds, run.id])
    }
  }

  const handleBaselineChange = (runId) => {
    if (!selectedIds.includes(runId)) return
    setBaselineId(runId)
  }

  const handleRequestCompareClick = () => {
    if (!onRequestCompare) return
    if (!baselineId || selectedIds.length < 2) return
    onRequestCompare({
      baselineRunId: baselineId,
      selectedRunIds: selectedIds,
      datasetName: datasetFilter?.dataset_name ?? null,
      datasetSplit: datasetFilter?.dataset_split ?? null
    })
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

      <div className="history-toolbar">
        <div className="history-toolbar-info">
          {datasetFilter ? (
            <span className="dataset-filter">
              Comparing runs for dataset{' '}
              <strong>{datasetFilter.dataset_name}</strong> (
              {datasetFilter.dataset_split})
            </span>
          ) : (
            <span className="dataset-filter">
              Select a completed run to set the comparison baseline.
            </span>
          )}
        </div>
        <div className="history-toolbar-actions">
          <button
            className="btn-primary btn-small"
            onClick={handleRequestCompareClick}
            disabled={!baselineId || selectedIds.length < 2}
          >
            Compare Selected
          </button>
        </div>
      </div>
      
      <div className="table-container">
        <table className="benchmark-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Baseline</th>
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
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(run.id)}
                    onChange={() => handleToggleSelect(run)}
                    disabled={!isRunSelectable(run)}
                    title={
                      !isRunSelectable(run) && datasetFilter
                        ? 'Only runs from the same dataset and split can be compared'
                        : undefined
                    }
                  />
                </td>
                <td>
                  <input
                    type="radio"
                    name="baseline-run"
                    checked={baselineId === run.id}
                    onChange={() => handleBaselineChange(run.id)}
                    disabled={!selectedIds.includes(run.id)}
                    title={
                      !selectedIds.includes(run.id)
                        ? 'Select the run first to set it as baseline'
                        : 'Set as baseline for comparison'
                    }
                  />
                </td>
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

