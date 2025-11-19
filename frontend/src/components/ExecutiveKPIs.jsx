import { useEffect, useState } from 'react'

export default function ExecutiveKPIs({ stats }) {
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    setAnimated(true)
  }, [])

  const kpis = [
    {
      label: 'Total Prompts',
      value: stats?.total_prompts || 0,
      icon: '📊',
      color: '#3b82f6',
      format: (v) => v.toLocaleString()
    },
    {
      label: 'Benign ',
      value: stats?.benign_pct || 0,
      icon: '✅',
      color: '#10b981',
      format: (v) => `${v.toFixed(1)}%`,
      suffix: `(${stats?.benign_count || 0})`
    },
    {
      label: 'Suspicious',
      value: stats?.suspicious_pct || 0,
      icon: '⚠️',
      color: '#f59e0b',
      format: (v) => `${v.toFixed(1)}%`,
      suffix: `(${stats?.suspicious_count || 0})`
    },
    {
      label: 'Malicious',
      value: stats?.malicious_pct || 0,
      icon: '🚫',
      color: '#ef4444',
      format: (v) => `${v.toFixed(1)}%`,
      suffix: `(${stats?.malicious_count || 0})`
    },
    {
      label: 'Ratio Block/Allow',
      value: stats?.block_allow_ratio || '1:0',
      icon: '⚖️',
      color: '#8b5cf6',
      format: (v) => v
    },
    {
      label: 'Prompts/Min',
      value: stats?.prompts_per_minute || 0,
      icon: '⚡',
      color: '#06b6d4',
      format: (v) => v.toFixed(2),
      trend: stats?.risk_trend
    }
  ]

  return (
    <div className="executive-kpis">
      {kpis.map((kpi, idx) => (
        <div 
          key={idx} 
          className={`kpi-card ${animated ? 'animated' : ''}`}
          style={{ 
            animationDelay: `${idx * 0.1}s`,
            borderTopColor: kpi.color 
          }}
        >
          <div className="kpi-icon" style={{ color: kpi.color }}>
            {kpi.icon}
          </div>
          <div className="kpi-content">
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value" style={{ color: kpi.color }}>
              {kpi.format(kpi.value)}
            </div>
            {kpi.suffix && (
              <div className="kpi-suffix">{kpi.suffix}</div>
            )}
            {kpi.trend && (
              <div className={`kpi-trend ${kpi.trend}`}>
                {kpi.trend === 'increasing' ? '↗' : kpi.trend === 'decreasing' ? '↘' : '→'}
                {' '}
                {kpi.trend}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

