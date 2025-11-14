import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../services/api.js'

export default function ChatWindow(){
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hi! I am secured by the SPG Semantic Firewall. Try me with normal and adversarial prompts.' }
  ])
  const [loading, setLoading] = useState(false)
  const scroller = useRef(null)

  useEffect(()=>{ if(scroller.current){ scroller.current.scrollTop = scroller.current.scrollHeight } }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if(!text || loading) return
    setInput('')
    setMessages(m => [...m, { sender: 'user', text }])
    setLoading(true)
    try{
      const res = await sendMessage(text)
      if(res.blocked){
        const metricsText = formatMetrics(res)
        setMessages(m => [...m, { 
          sender: 'bot', 
          text: `⛔ Blocked by firewall: ${res.reason}`,
          metrics: metricsText
        }])
      } else if(res.reply){
        const metricsText = formatMetrics(res)
        setMessages(m => [...m, { 
          sender: 'bot', 
          text: res.reply,
          metrics: metricsText
        }])
      } else {
        setMessages(m => [...m, { sender: 'bot', text: 'Unexpected response from server.' }])
      }
    }catch(err){
      setMessages(m => [...m, { sender: 'bot', text: `Error: ${err.message}` }])
    } finally { setLoading(false) }
  }

  const formatMetrics = (res) => {
    if (!res.ml_detectors || res.ml_detectors.length === 0) return null
    
    const detectorLines = res.ml_detectors.map(d => 
      `  • ${d.name}: ${(d.score * 100).toFixed(1)}% (${d.latency_ms.toFixed(1)}ms)`
    ).join('\n')
    
    return `
📊 Metrics of Detection:
${detectorLines}

⏱️ Latencies:
  • ML Analysis: ${res.analysis_latency_ms?.toFixed(1) || 'N/A'}ms
  • Backend Response: ${res.backend_latency_ms?.toFixed(1) || 'N/A'}ms
  • Total: ${res.total_latency_ms?.toFixed(1) || 'N/A'}ms
    `.trim()
  }

  const onKey = (e)=>{ if(e.key === 'Enter') handleSend() }

  return (
    <div className="chatbox">
      <div className="messages" ref={scroller}>
        {messages.map((msg, i)=>(
          <div key={i} className={`msg ${msg.sender}`}>
            <div>{msg.text}</div>
            {msg.metrics && (
              <pre style={{
                fontSize: '0.85em',
                marginTop: '8px',
                padding: '8px',
                background: 'rgba(0,0,0,0.1)',
                borderRadius: '4px',
                whiteSpace: 'pre-wrap'
              }}>
                {msg.metrics}
              </pre>
            )}
          </div>
        ))}
      </div>
      <div className="row">
        <input type="text" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={onKey} placeholder="Type a message..." />
        <button onClick={handleSend} disabled={loading}>{loading ? '...' : 'Send'}</button>
      </div>
      <small className="meta">API Base: {import.meta.env.VITE_API_BASE || 'http://localhost:8080'}</small>
    </div>
  )
}