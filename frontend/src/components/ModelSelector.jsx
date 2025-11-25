import { useState, useEffect } from 'react'

export default function ModelSelector({ onConfigChange, initialConfig = null }) {
  const [config, setConfig] = useState({
    prompt_injection: initialConfig?.prompt_injection || 'custom_onnx',
    pii: initialConfig?.pii || 'presidio',
    toxicity: initialConfig?.toxicity || 'detoxify'
  })

  // Available models for each category
  const availableModels = {
    prompt_injection: [
      { value: 'custom_onnx', label: 'Custom ONNX' },
      { value: 'deberta', label: 'DeBERTa' }
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
  }

  useEffect(() => {
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

