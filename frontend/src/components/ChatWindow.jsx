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
        setMessages(m => [...m, { sender: 'bot', text: `⛔ Blocked by firewall: ${res.reason}` }])
      } else if(res.reply){
        setMessages(m => [...m, { sender: 'bot', text: res.reply }])
      } else {
        setMessages(m => [...m, { sender: 'bot', text: 'Unexpected response from server.' }])
      }
    }catch(err){
      setMessages(m => [...m, { sender: 'bot', text: `Error: ${err.message}` }])
    } finally { setLoading(false) }
  }

  const onKey = (e)=>{ if(e.key === 'Enter') handleSend() }

  return (
    <div className="chatbox">
      <div className="messages" ref={scroller}>
        {messages.map((msg, i)=>(
          <div key={i} className={`msg ${msg.sender}`}>{msg.text}</div>
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