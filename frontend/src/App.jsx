import ChatWindow from './components/ChatWindow.jsx'

export default function App() {
  return (
    <div className="container">
      <h1>SPG Chatbot Testbed</h1>
      <p className="subtitle">Messages go through the Semantic Firewall before reaching the backend.</p>
      <ChatWindow />
    </div>
  )
}