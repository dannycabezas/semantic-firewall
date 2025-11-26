const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

export async function sendMessage(message, modelConfig = null){
  const payload = { message }
  if (modelConfig) {
    payload.detector_config = modelConfig
  }
  
  const r = await fetch(`${BASE}/api/chat`,{
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if(!r.ok) throw new Error(`HTTP ${r.status}`)
  return await r.json()
}