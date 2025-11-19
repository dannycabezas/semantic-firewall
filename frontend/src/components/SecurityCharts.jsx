import { useEffect, useRef } from 'react'

export default function SecurityCharts({ riskBreakdown, requests }) {
  const donutRef = useRef(null)
  const trendRef = useRef(null)

  useEffect(() => {
    if (donutRef.current && riskBreakdown) {
      drawDonutChart(donutRef.current, riskBreakdown)
    }
  }, [riskBreakdown])

  useEffect(() => {
    if (trendRef.current && requests) {
      drawTrendChart(trendRef.current, requests)
    }
  }, [requests])

  return (
    <div className="security-charts">
      <div className="chart-container">
        <h3>Risk Category Distribution</h3>
        <canvas ref={donutRef} width="300" height="300"></canvas>
      </div>
      <div className="chart-container">
        <h3>Temporal Trend (last prompts)</h3>
        <canvas ref={trendRef} width="400" height="250"></canvas>
      </div>
    </div>
  )
}

function drawDonutChart(canvas, breakdown) {
  const ctx = canvas.getContext('2d')
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2
  const radius = 100
  const innerRadius = 60

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const categories = [
    { key: 'clean', label: 'Clean', color: '#10b981' },
    { key: 'injection', label: 'Injection', color: '#ef4444' },
    { key: 'pii', label: 'PII', color: '#f97316' },
    { key: 'toxicity', label: 'Toxicity', color: '#eab308' },
    { key: 'leak', label: 'Leak', color: '#8b5cf6' },
    { key: 'harmful', label: 'Harmful', color: '#ec4899' }
  ]

  const total = Object.values(breakdown).reduce((sum, val) => sum + val, 0)
  if (total === 0) {
    ctx.fillStyle = '#6b7280'
    ctx.font = '14px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('No data', centerX, centerY)
    return
  }

  let currentAngle = -Math.PI / 2 // Start at top

  categories.forEach(({ key, label, color }) => {
    const value = breakdown[key] || 0
    const sliceAngle = (value / total) * 2 * Math.PI

    if (value > 0) {
      // Draw slice
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle)
      ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true)
      ctx.closePath()
      ctx.fill()

      // Draw label
      const labelAngle = currentAngle + sliceAngle / 2
      const labelX = centerX + Math.cos(labelAngle) * (radius + 20)
      const labelY = centerY + Math.sin(labelAngle) * (radius + 20)
      
      ctx.fillStyle = color
      ctx.font = '12px sans-serif'
      ctx.textAlign = labelX > centerX ? 'left' : 'right'
      ctx.fillText(`${label} (${value})`, labelX, labelY)

      currentAngle += sliceAngle
    }
  })

  // Draw center circle (donut hole)
  ctx.fillStyle = '#1e293b'
  ctx.beginPath()
  ctx.arc(centerX, centerY, innerRadius, 0, 2 * Math.PI)
  ctx.fill()

  // Draw total in center
  ctx.fillStyle = '#e2e8f0'
  ctx.font = 'bold 24px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(total, centerX, centerY - 10)
  ctx.font = '12px sans-serif'
  ctx.fillText('Total', centerX, centerY + 10)
}

function drawTrendChart(canvas, requests) {
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

  // Take last 20 requests
  const recentRequests = requests.slice(-20)

  // Count by category
  const categories = ['injection', 'pii', 'toxicity', 'leak', 'harmful']
  const colors = {
    injection: '#ef4444',
    pii: '#f97316',
    toxicity: '#eab308',
    leak: '#8b5cf6',
    harmful: '#ec4899'
  }

  // Accumulate counts
  const data = {}
  categories.forEach(cat => {
    data[cat] = []
    let count = 0
    recentRequests.forEach(req => {
      if (req.risk_category === cat) count++
      data[cat].push(count)
    })
  })

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

  // Draw lines for each category
  const maxCount = Math.max(...Object.values(data).flat(), 1)
  const xStep = (width - 2 * padding) / (recentRequests.length - 1 || 1)

  categories.forEach(cat => {
    const points = data[cat]
    if (points.some(p => p > 0)) {
      ctx.strokeStyle = colors[cat]
      ctx.lineWidth = 2
      ctx.beginPath()
      points.forEach((count, idx) => {
        const x = padding + idx * xStep
        const y = height - padding - ((count / maxCount) * (height - 2 * padding))
        if (idx === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // Draw label
      const lastY = height - padding - ((points[points.length - 1] / maxCount) * (height - 2 * padding))
      ctx.fillStyle = colors[cat]
      ctx.font = '11px sans-serif'
      ctx.fillText(cat, width - padding + 5, lastY)
    }
  })

  // Draw axis labels
  ctx.fillStyle = '#94a3b8'
  ctx.font = '11px sans-serif'
  ctx.textAlign = 'right'
  for (let i = 0; i <= 4; i++) {
    const y = padding + (height - 2 * padding) * (i / 4)
    const value = Math.round(maxCount * (1 - i / 4))
    ctx.fillText(value, padding - 5, y + 4)
  }
}

