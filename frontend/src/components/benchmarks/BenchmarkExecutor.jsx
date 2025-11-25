import { useState } from 'react'
import { fetchAPI } from '../../services/websocket'

export default function BenchmarkExecutor({ onBenchmarkStarted }) {
  const [datasetName, setDatasetName] = useState('jackhhao/jailbreak-classification')
  const [datasetSplit, setDatasetSplit] = useState('test')
  const [maxSamples, setMaxSamples] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const payload = {
        dataset_name: datasetName,
        dataset_split: datasetSplit,
        tenant_id: 'benchmark'
      }

      if (maxSamples && parseInt(maxSamples) > 0) {
        payload.max_samples = parseInt(maxSamples)
      }

      const result = await fetchAPI('/api/benchmarks/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      // Notify parent component
      if (onBenchmarkStarted) {
        onBenchmarkStarted(result.run_id)
      }
    } catch (err) {
      console.error('Error starting benchmark:', err)
      setError(err.message || 'Failed to start benchmark')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="benchmark-executor">
      <h3>New Benchmark Execution</h3>
      
      <form onSubmit={handleSubmit} className="benchmark-form">
        <div className="form-group">
          <label htmlFor="dataset-name">
            Hugging Face Dataset
            <span className="help-text">e.g. jackhhao/jailbreak-classification</span>
          </label>
          <input
            id="dataset-name"
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="username/dataset-name"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="dataset-split">Dataset Split</label>
          <select
            id="dataset-split"
            value={datasetSplit}
            onChange={(e) => setDatasetSplit(e.target.value)}
          >
            <option value="test">Test</option>
            <option value="train">Train</option>
            <option value="validation">Validation</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="max-samples">
            Max Samples (optional)
            <span className="help-text">Leave empty to process all</span>
          </label>
          <input
            id="max-samples"
            type="number"
            min="1"
            value={maxSamples}
            onChange={(e) => setMaxSamples(e.target.value)}
            placeholder="e.g. 100"
          />
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <button 
          type="submit" 
          className="btn-primary"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Starting...' : 'Start Benchmark'}
        </button>
      </form>
    </div>
  )
}

