import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../services/api.js'

export default function SimplifiedChat() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hello! I am protected by SPG Semantic Firewall.' }
  ])
  const [loading, setLoading] = useState(false)
  const scroller = useRef(null)

  useEffect(() => {
    if (scroller.current) {
      scroller.current.scrollTop = scroller.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    
    setInput('')
    setMessages(m => [...m, { sender: 'user', text }])
    setLoading(true)
    
    try {
      const res = await sendMessage(text)
      
      if (res.blocked) {
        // Generic block message without metrics
        setMessages(m => [...m, { 
          sender: 'bot', 
          text: '🛡️ Content not allowed by security policies',
          isBlocked: true
        }])
      } else if (res.reply) {
        // Simple reply without metrics
        setMessages(m => [...m, { 
          sender: 'bot', 
          text: res.reply
        }])
      } else {
        setMessages(m => [...m, { 
          sender: 'bot', 
          text: 'Unexpected server response.' 
        }])
      }
    } catch (err) {
      setMessages(m => [...m, { 
        sender: 'bot', 
        text: `❌ Error: ${err.message}` 
      }])
    } finally {
      setLoading(false)
    }
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="simplified-chat">
      <div className="chat-header">
        <h3>💬 Test Chat</h3>
        <span className="chat-subtitle">Protected by Semantic Firewall</span>
      </div>
      
      <div className="chat-messages" ref={scroller}>
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.sender}`}>
            <div className={`chat-bubble ${msg.sender} ${msg.isBlocked ? 'blocked' : ''}`}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      
      <div className="chat-input-row">
        <input 
          type="text" 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          onKeyDown={onKey} 
          placeholder="Write a message..." 
          disabled={loading}
          className="chat-input"
        />
        <button 
          onClick={handleSend} 
          disabled={loading}
          className="chat-send-btn"
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  )
}

