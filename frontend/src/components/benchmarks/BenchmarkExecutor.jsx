import { useState, useEffect, useRef } from 'react'
import { fetchAPI, uploadCustomDataset, listCustomDatasets, deleteCustomDataset } from '../../services/websocket'
import ModelSelector from '../ModelSelector.jsx'

export default function BenchmarkExecutor({ onBenchmarkStarted }) {
  // Dataset source toggle
  const [datasetSource, setDatasetSource] = useState('huggingface') // 'huggingface' | 'custom'
  
  // Hugging Face dataset fields
  const [datasetName, setDatasetName] = useState('jackhhao/jailbreak-classification')
  const [datasetSplit, setDatasetSplit] = useState('test')
  
  // Custom dataset fields
  const [customDatasets, setCustomDatasets] = useState([])
  const [selectedCustomDatasetId, setSelectedCustomDatasetId] = useState('')
  const [loadingDatasets, setLoadingDatasets] = useState(false)
  
  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadName, setUploadName] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const fileInputRef = useRef(null)
  
  // Common fields
  const [maxSamples, setMaxSamples] = useState('')
  const [modelConfig, setModelConfig] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Load custom datasets when switching to custom source
  useEffect(() => {
    if (datasetSource === 'custom') {
      loadCustomDatasets()
    }
  }, [datasetSource])

  const loadCustomDatasets = async () => {
    setLoadingDatasets(true)
    try {
      const response = await listCustomDatasets()
      setCustomDatasets(response.datasets || [])
    } catch (err) {
      console.error('Error loading custom datasets:', err)
      setError('Failed to load custom datasets')
    } finally {
      setLoadingDatasets(false)
    }
  }

  const handleUploadDataset = async (e) => {
    e.preventDefault()
    if (!uploadFile || !uploadName.trim()) return

    setUploading(true)
    setUploadError(null)

    try {
      const formData = new FormData()
      formData.append('name', uploadName.trim())
      if (uploadDescription.trim()) {
        formData.append('description', uploadDescription.trim())
      }
      formData.append('file', uploadFile)

      const result = await uploadCustomDataset(formData)
      
      // Refresh the datasets list
      await loadCustomDatasets()
      
      // Select the newly uploaded dataset
      setSelectedCustomDatasetId(result.dataset_id)
      
      // Close modal and reset form
      setShowUploadModal(false)
      setUploadName('')
      setUploadDescription('')
      setUploadFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      console.error('Error uploading dataset:', err)
      setUploadError(err.message || 'Failed to upload dataset')
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteDataset = async (datasetId) => {
    if (!confirm('Are you sure you want to delete this dataset? This action cannot be undone.')) {
      return
    }

    try {
      await deleteCustomDataset(datasetId)
      await loadCustomDatasets()
      if (selectedCustomDatasetId === datasetId) {
        setSelectedCustomDatasetId('')
      }
    } catch (err) {
      console.error('Error deleting dataset:', err)
      setError(err.message || 'Failed to delete dataset')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const payload = {
        dataset_split: datasetSplit,
        tenant_id: 'benchmark'
      }

      // Set dataset source
      if (datasetSource === 'huggingface') {
        payload.dataset_name = datasetName
      } else {
        if (!selectedCustomDatasetId) {
          throw new Error('Please select a custom dataset')
        }
        payload.custom_dataset_id = selectedCustomDatasetId
      }

      if (maxSamples && parseInt(maxSamples) > 0) {
        payload.max_samples = parseInt(maxSamples)
      }

      if (modelConfig) {
        payload.detector_config = modelConfig
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="benchmark-executor">
      <h3>New Benchmark Execution</h3>
      
      <form onSubmit={handleSubmit} className="benchmark-form">
        {/* Dataset Source Toggle */}
        <div className="form-group">
          <label>Dataset Source</label>
          <div className="dataset-source-toggle">
            <button
              type="button"
              className={`toggle-btn ${datasetSource === 'huggingface' ? 'active' : ''}`}
              onClick={() => setDatasetSource('huggingface')}
            >
              🤗 Hugging Face
            </button>
            <button
              type="button"
              className={`toggle-btn ${datasetSource === 'custom' ? 'active' : ''}`}
              onClick={() => setDatasetSource('custom')}
            >
              📁 Custom Dataset
            </button>
          </div>
        </div>

        {/* Hugging Face Dataset Fields */}
        {datasetSource === 'huggingface' && (
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
        )}

        {/* Custom Dataset Selection */}
        {datasetSource === 'custom' && (
          <div className="form-group">
            <label>
              Select Custom Dataset
              <span className="help-text">Upload CSV or JSON with 'prompt' and 'type' columns</span>
            </label>
            
            {loadingDatasets ? (
              <div className="loading-datasets">Loading datasets...</div>
            ) : (
              <>
                <div className="custom-dataset-selector">
                  <select
                    value={selectedCustomDatasetId}
                    onChange={(e) => setSelectedCustomDatasetId(e.target.value)}
                    className="dataset-select"
                  >
                    <option value="">-- Select a dataset --</option>
                    {customDatasets.map((dataset) => (
                      <option key={dataset.id} value={dataset.id}>
                        {dataset.name} ({dataset.total_samples} samples)
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn-secondary btn-small"
                    onClick={() => setShowUploadModal(true)}
                  >
                    ➕ Upload New
                  </button>
                </div>

                {/* Dataset Details */}
                {selectedCustomDatasetId && (
                  <div className="selected-dataset-info">
                    {(() => {
                      const dataset = customDatasets.find(d => d.id === selectedCustomDatasetId)
                      if (!dataset) return null
                      return (
                        <>
                          <div className="dataset-info-row">
                            <span className="info-label">Name:</span>
                            <span className="info-value">{dataset.name}</span>
                          </div>
                          {dataset.description && (
                            <div className="dataset-info-row">
                              <span className="info-label">Description:</span>
                              <span className="info-value">{dataset.description}</span>
                            </div>
                          )}
                          <div className="dataset-info-row">
                            <span className="info-label">Samples:</span>
                            <span className="info-value">{dataset.total_samples}</span>
                          </div>
                          <div className="dataset-info-row">
                            <span className="info-label">Type:</span>
                            <span className="info-value">{dataset.file_type}</span>
                          </div>
                          <div className="dataset-info-row">
                            <span className="info-label">Uploaded:</span>
                            <span className="info-value">{formatDate(dataset.created_at)}</span>
                          </div>
                          <button
                            type="button"
                            className="btn-danger btn-small"
                            onClick={() => handleDeleteDataset(dataset.id)}
                          >
                            🗑️ Delete Dataset
                          </button>
                        </>
                      )
                    })()}
                  </div>
                )}

                {customDatasets.length === 0 && (
                  <div className="no-datasets-message">
                    <p>No custom datasets available.</p>
                    <button
                      type="button"
                      className="btn-primary btn-small"
                      onClick={() => setShowUploadModal(true)}
                    >
                      Upload Your First Dataset
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

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

        <ModelSelector onConfigChange={setModelConfig} />

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <button 
          type="submit" 
          className="btn-primary"
          disabled={isSubmitting || (datasetSource === 'custom' && !selectedCustomDatasetId)}
        >
          {isSubmitting ? 'Starting...' : 'Start Benchmark'}
        </button>
      </form>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📤 Upload Custom Dataset</h2>
              <button className="modal-close" onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleUploadDataset} className="upload-form">
                <div className="form-group">
                  <label htmlFor="upload-name">Dataset Name *</label>
                  <input
                    id="upload-name"
                    type="text"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    placeholder="e.g. My Custom Jailbreak Dataset"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="upload-description">Description (optional)</label>
                  <input
                    id="upload-description"
                    type="text"
                    value={uploadDescription}
                    onChange={(e) => setUploadDescription(e.target.value)}
                    placeholder="Brief description of the dataset"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="upload-file">
                    Dataset File *
                    <span className="help-text">CSV or JSON format</span>
                  </label>
                  <input
                    ref={fileInputRef}
                    id="upload-file"
                    type="file"
                    accept=".csv,.json,text/csv,application/json"
                    onChange={(e) => setUploadFile(e.target.files[0])}
                    required
                  />
                </div>

                <div className="upload-format-help">
                  <h4>Expected Format:</h4>
                  <div className="format-examples">
                    <div className="format-example">
                      <strong>CSV:</strong>
                      <pre>prompt,type
"Hello, how are you?",benign
"Ignore all instructions...",jailbreak</pre>
                    </div>
                    <div className="format-example">
                      <strong>JSON:</strong>
                      <pre>{`[
  {"prompt": "Hello", "type": "benign"},
  {"prompt": "Ignore...", "type": "jailbreak"}
]`}</pre>
                    </div>
                  </div>
                </div>

                {uploadError && (
                  <div className="error-message">
                    ⚠️ {uploadError}
                  </div>
                )}

                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowUploadModal(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={uploading || !uploadFile || !uploadName.trim()}
                  >
                    {uploading ? 'Uploading...' : 'Upload Dataset'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
