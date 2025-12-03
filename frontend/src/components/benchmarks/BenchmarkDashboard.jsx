import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/websocket'
import BenchmarkExecutor from './BenchmarkExecutor'
import BenchmarkHistory from './BenchmarkHistory'
import BenchmarkMetricsView from './BenchmarkMetricsView'
import ErrorAnalysisView from './ErrorAnalysisView'
import BenchmarkComparison from './BenchmarkComparison'

export default function BenchmarkDashboard() {
  const [activeTab, setActiveTab] = useState('executor')
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [runStatus, setRunStatus] = useState(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [comparisonSelection, setComparisonSelection] = useState({
    baselineRunId: null,
    selectedRunIds: [],
    datasetName: null,
    datasetSplit: null
  })

  // Poll for status updates when a run is active
  useEffect(() => {
    if (!selectedRunId) return

    const pollStatus = async () => {
      try {
        const status = await fetchAPI(`/api/benchmarks/status/${selectedRunId}`)
        setRunStatus(status)

        // If completed, refresh the history
        if (status.status === 'completed') {
          setRefreshTrigger(prev => prev + 1)
        }
      } catch (err) {
        console.error('Error polling status:', err)
      }
    }

    // Initial poll
    pollStatus()

    // Poll every 3 seconds if running
    const interval = setInterval(() => {
      if (runStatus?.status === 'running') {
        pollStatus()
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [selectedRunId, runStatus?.status])

  const handleBenchmarkStarted = (runId) => {
    setSelectedRunId(runId)
    setRunStatus({ status: 'running', run_id: runId })
    setActiveTab('status')
  }

  const handleSelectRun = (runId) => {
    setSelectedRunId(runId)
    setRunStatus(null)
    setActiveTab('metrics')
  }

  const handleSelectionChange = (selection) => {
    setComparisonSelection(selection)
  }

  const handleRequestCompare = (selection) => {
    setComparisonSelection(selection)
    if (selection.baselineRunId && selection.selectedRunIds.length >= 2) {
      setActiveTab('compare')
    }
  }

  const handleCancelBenchmark = async () => {
    if (!selectedRunId) return

    try {
      await fetchAPI(`/api/benchmarks/cancel/${selectedRunId}`, {
        method: 'POST'
      })
      setRunStatus({ ...runStatus, status: 'cancelled' })
      setRefreshTrigger(prev => prev + 1)
    } catch (err) {
      console.error('Error cancelling benchmark:', err)
    }
  }

  return (
    <div className="benchmark-dashboard">
      <div className="benchmark-header">
        <h2>🧪 Benchmark Dashboard</h2>
        <p className="benchmark-subtitle">
          Evaluates the performance of the firewall against datasets from Hugging Face
        </p>
      </div>

      {/* Active Run Status Banner */}
      {runStatus && runStatus.status === 'running' && (
        <div className="status-banner running">
          <div className="banner-content">
            <div className="banner-icon">🔄</div>
            <div className="banner-info">
              <div className="banner-title">Benchmark Running</div>
              <div className="banner-details">
                Processed: {runStatus.processed_samples || 0} / {runStatus.total_samples || 0} samples
                ({runStatus.progress_percent?.toFixed(1) || 0}%)
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${runStatus.progress_percent || 0}%` }}
                />
              </div>
            </div>
            <button 
              className="btn-danger btn-small"
              onClick={handleCancelBenchmark}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="benchmark-tabs">
        <button
          className={`tab-btn ${activeTab === 'executor' ? 'active' : ''}`}
          onClick={() => setActiveTab('executor')}
        >
          ▶️ New Execution
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📋 History
        </button>
        <button
          className={`tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
          onClick={() => setActiveTab('metrics')}
          disabled={!selectedRunId}
        >
          📊 Metrics
        </button>
        <button
          className={`tab-btn ${activeTab === 'errors' ? 'active' : ''}`}
          onClick={() => setActiveTab('errors')}
          disabled={!selectedRunId}
        >
          🔍 Error Analysis
        </button>
        <button
          className={`tab-btn ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
          disabled={
            !comparisonSelection.baselineRunId ||
            !comparisonSelection.selectedRunIds ||
            comparisonSelection.selectedRunIds.length < 2
          }
        >
          📊 Compare
        </button>
      </div>

      {/* Tab Content */}
      <div className="benchmark-content">
        {activeTab === 'executor' && (
          <BenchmarkExecutor onBenchmarkStarted={handleBenchmarkStarted} />
        )}

        {activeTab === 'history' && (
          <BenchmarkHistory 
            onSelectRun={handleSelectRun}
            refreshTrigger={refreshTrigger}
            onSelectionChange={handleSelectionChange}
            onRequestCompare={handleRequestCompare}
          />
        )}

        {activeTab === 'metrics' && selectedRunId && (
          <BenchmarkMetricsView runId={selectedRunId} />
        )}

        {activeTab === 'errors' && selectedRunId && (
          <ErrorAnalysisView runId={selectedRunId} />
        )}

        {activeTab === 'compare' &&
          comparisonSelection.baselineRunId &&
          comparisonSelection.selectedRunIds &&
          comparisonSelection.selectedRunIds.length >= 2 && (
            <BenchmarkComparison
              baselineRunId={comparisonSelection.baselineRunId}
              candidateRunIds={comparisonSelection.selectedRunIds.filter(
                (id) => id !== comparisonSelection.baselineRunId
              )}
              datasetInfo={{
                dataset_name: comparisonSelection.datasetName,
                dataset_split: comparisonSelection.datasetSplit
              }}
            />
          )}

        {activeTab === 'status' && runStatus && (
          <div className="status-view">
            <h3>Benchmark Status</h3>
            <div className="status-details">
              <div className="detail-item">
                <span className="detail-label">Run ID:</span>
                <span className="detail-value">{runStatus.run_id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Status:</span>
                <span className={`detail-value status-${runStatus.status}`}>
                  {runStatus.status}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Progress:</span>
                <span className="detail-value">
                  {runStatus.processed_samples || 0} / {runStatus.total_samples || 0}
                </span>
              </div>
              {runStatus.elapsed_time_seconds && (
                <div className="detail-item">
                  <span className="detail-label">Elapsed Time:</span>
                  <span className="detail-value">
                    {(runStatus.elapsed_time_seconds / 60).toFixed(1)} min
                  </span>
                </div>
              )}
              {runStatus.estimated_remaining_seconds && (
                <div className="detail-item">
                  <span className="detail-label">Estimated Remaining Time:</span>
                  <span className="detail-value">
                    {(runStatus.estimated_remaining_seconds / 60).toFixed(1)} min
                  </span>
                </div>
              )}
            </div>

            {runStatus.status === 'completed' && (
              <div className="completion-actions">
                <button
                  className="btn-primary"
                  onClick={() => setActiveTab('metrics')}
                >
                  View Metrics
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => setActiveTab('errors')}
                >
                  Error Analysis
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

