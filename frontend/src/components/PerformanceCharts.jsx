import { useEffect, useRef } from 'react'

export default function PerformanceCharts({ avgLatency, requests }) {
  const barRef = useRef(null)
  const timelineRef = useRef(null)

  useEffect(() => {
    if (barRef.current && avgLatency) {
      drawLatencyBars(barRef.current, avgLatency)
    }
  }, [avgLatency])

  useEffect(() => {
    if (timelineRef.current && requests) {
      drawLatencyTimeline(timelineRef.current, requests)
    }
  }, [requests])

  return (
    <div className="performance-charts">
      <div className="chart-container">
        <h3>Average Latency by Phase</h3>
        <canvas ref={barRef} width="350" height="250"></canvas>
      </div>
      <div className="chart-container">
        <h3>Latency Timeline</h3>
        <canvas ref={timelineRef} width="400" height="250"></canvas>
      </div>
    </div>
  )
}

function drawLatencyBars(canvas, avgLatency) {
  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height
  const padding = { top: 20, right: 20, bottom: 40, left: 100 }

  // Clear canvas
  ctx.clearRect(0, 0, width, height)

  const phases = [
    { key: 'preprocessing', label: 'Preprocessing', color: '#3b82f6' },
    { key: 'ml', label: 'ML Analysis', color: '#10b981' },
    { key: 'policy', label: 'Policy Eval', color: '#f59e0b' },
    { key: 'backend', label: 'Backend', color: '#8b5cf6' }
  ]

  const maxLatency = Math.max(...phases.map(p => avgLatency[p.key] || 0), 1)
  const barHeight = (height - padding.top - padding.bottom) / phases.length
  const chartWidth = width - padding.left - padding.right

  phases.forEach((phase, idx) => {
    const latency = avgLatency[phase.key] || 0
    const barWidth = (latency / maxLatency) * chartWidth
    const y = padding.top + idx * barHeight

    // Draw bar
    ctx.fillStyle = phase.color
    ctx.fillRect(padding.left, y + 5, barWidth, barHeight - 10)

    // Draw label
    ctx.fillStyle = '#e2e8f0'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(phase.label, padding.left - 10, y + barHeight / 2 + 4)

    // Draw value
    ctx.fillStyle = '#e2e8f0'
    ctx.textAlign = 'left'
    ctx.fillText(`${latency.toFixed(2)}ms`, padding.left + barWidth + 5, y + barHeight / 2 + 4)
  })

  // Draw total
  const totalLatency = avgLatency.total || 0
  ctx.fillStyle = '#94a3b8'
  ctx.font = 'bold 14px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(`Total: ${totalLatency.toFixed(2)}ms`, width / 2, height - 10)
}

function drawLatencyTimeline(canvas, requests) {
  const ctx = canvas.getContext('2d')
  const width = canvas.width
  const height = canvas.height
  const padding = 40

  // Clear canvas
  ctx.clearRect(0, 0, width, height)

  if (!requests || requests.length === 0) {
    ctx.fillStyle = '#6b7280'
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Not enough data', width / 2, height / 2)
    return
  }

  // Take last 30 requests
  const recentRequests = requests.slice(-30)

  // Extract total latencies
  const latencies = recentRequests.map(r => r.latency_ms?.total || 0)
  const maxLatency = Math.max(...latencies, 1)
  const minLatency = Math.min(...latencies)

  // Draw grid
  ctx.strokeStyle = '#334155'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = padding + (height - 2 * padding) * (i / 4)
    ctx.beginPath()
    ctx.moveTo(padding, y)
    ctx.lineTo(width - padding, y)
    ctx.stroke()
  }

  // Draw axes
  ctx.strokeStyle = '#64748b'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(padding, padding)
  ctx.lineTo(padding, height - padding)
  ctx.lineTo(width - padding, height - padding)
  ctx.stroke()

  // Draw scatter points
  const xStep = (width - 2 * padding) / (latencies.length - 1 || 1)
  
  ctx.fillStyle = '#3b82f6'
  latencies.forEach((latency, idx) => {
    const x = padding + idx * xStep
    const normalizedLatency = (latency - minLatency) / (maxLatency - minLatency || 1)
    const y = height - padding - (normalizedLatency * (height - 2 * padding))
    
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, 2 * Math.PI)
    ctx.fill()
  })

  // Draw moving average line
  const windowSize = 5
  ctx.strokeStyle = '#f59e0b'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  latencies.forEach((_, idx) => {
    if (idx >= windowSize - 1) {
      const window = latencies.slice(idx - windowSize + 1, idx + 1)
      const avg = window.reduce((sum, val) => sum + val, 0) / window.length
      const x = padding + idx * xStep
      const normalizedAvg = (avg - minLatency) / (maxLatency - minLatency || 1)
      const y = height - padding - (normalizedAvg * (height - 2 * padding))
      
      if (idx === windowSize - 1) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    }
  })
  ctx.stroke()

  // Draw axis labels
  ctx.fillStyle = '#94a3b8'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'right'
  for (let i = 0; i <= 4; i++) {
    const y = padding + (height - 2 * padding) * (i / 4)
    const value = maxLatency * (1 - i / 4)
    ctx.fillText(`${value.toFixed(0)}ms`, padding - 5, y + 4)
  }

  // Legend
  ctx.fillStyle = '#3b82f6'
  ctx.beginPath()
  ctx.arc(width - 120, 30, 4, 0, 2 * Math.PI)
  ctx.fill()
  ctx.fillStyle = '#e2e8f0'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('Latencia', width - 110, 34)

  ctx.strokeStyle = '#f59e0b'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(width - 120, 45)
  ctx.lineTo(width - 105, 45)
  ctx.stroke()
  ctx.fillText('Moving average', width - 100, 49)
}

