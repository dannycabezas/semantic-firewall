import { useState, useEffect } from 'react'

// Model labels mapping
const MODEL_LABELS = {
  custom_onnx: 'Custom ONNX',
  deberta: 'DeBERTa',
  llama_guard_86m: 'Llama Guard 2 86M (Multilingual)',
  llama_guard_22m: 'Llama Guard 2 22M (Fast)',
  presidio: 'Presidio',
  onnx: 'ONNX',
  mock: 'Mock',
  detoxify: 'Detoxify'
}

export default function ModelSelector({ onConfigChange, initialConfig = null }) {
  const [config, setConfig] = useState({
    prompt_injection: initialConfig?.prompt_injection || 'custom_onnx',
    pii: initialConfig?.pii || 'presidio',
    toxicity: initialConfig?.toxicity || 'detoxify'
  })

  // Available models for each category (fallback hardcoded)
  const [availableModels, setAvailableModels] = useState({
    prompt_injection: [
      { value: 'custom_onnx', label: 'Custom ONNX' },
      { value: 'deberta', label: 'DeBERTa' },
      { value: 'llama_guard_86m', label: 'Llama Guard 2 86M (Multilingual)' },
      { value: 'llama_guard_22m', label: 'Llama Guard 2 22M (Fast)' }
    ],
    pii: [
      { value: 'presidio', label: 'Presidio' },
      { value: 'onnx', label: 'ONNX' },
      { value: 'mock', label: 'Mock' }
    ],
    toxicity: [
      { value: 'detoxify', label: 'Detoxify' },
      { value: 'onnx', label: 'ONNX' }
    ]
  })

  useEffect(() => {
    // Try to fetch available models from backend
    const fetchModels = async () => {
      try {
        const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'
        const response = await fetch(`${BASE}/api/models/available`)
        if (response.ok) {
          const data = await response.json()
          // Transform backend data to UI format
          const transformed = {}
          for (const [category, models] of Object.entries(data.available)) {
            transformed[category] = models.map(value => ({
              value,
              label: MODEL_LABELS[value] || value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            }))
          }
          setAvailableModels(transformed)
        }
      } catch (error) {
        console.log('Using fallback model list:', error.message)
      }
    }

    fetchModels()

    // Notify parent of initial config
    if (onConfigChange) {
      onConfigChange(config)
    }
  }, []) // Only on mount

  const handleChange = (category, value) => {
    const newConfig = {
      ...config,
      [category]: value
    }
    setConfig(newConfig)
    if (onConfigChange) {
      onConfigChange(newConfig)
    }
  }

  return (
    <div className="model-selector">
      <h4>Model Configuration</h4>
      <div className="model-selector-grid">
        <div className="model-selector-item">
          <label htmlFor="pi-model">
            Prompt Injection (PI)
          </label>
          <select
            id="pi-model"
            value={config.prompt_injection}
            onChange={(e) => handleChange('prompt_injection', e.target.value)}
            className="model-select"
          >
            {availableModels.prompt_injection.map(model => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <div className="model-selector-item">
          <label htmlFor="pii-model">
            PII
          </label>
          <select
            id="pii-model"
            value={config.pii}
            onChange={(e) => handleChange('pii', e.target.value)}
            className="model-select"
          >
            {availableModels.pii.map(model => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </div>

        <div className="model-selector-item">
          <label htmlFor="toxicity-model">
            Toxicity
          </label>
          <select
            id="toxicity-model"
            value={config.toxicity}
            onChange={(e) => handleChange('toxicity', e.target.value)}
            className="model-select"
          >
            {availableModels.toxicity.map(model => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}

