# Semantic Firewall - Frontend Dashboard

A real-time monitoring dashboard for the SPG Semantic Firewall built with React and Vite. This dashboard provides comprehensive security analytics, live threat monitoring, and interactive testing capabilities for AI/LLM applications.

## 🎯 Overview

The frontend dashboard is a modern, responsive web application that provides real-time visibility into the security posture of your AI applications. It displays executive KPIs, security metrics, performance analytics, and allows interactive testing of the firewall's protection capabilities.

### Key Features

- ✅ **Real-Time Monitoring**
  - Live WebSocket connection for instant updates
  - Auto-reconnection with exponential backoff
  - Heartbeat mechanism for connection stability
  
- ✅ **Executive Dashboard**
  - Key Performance Indicators (KPIs)
  - Risk distribution visualization
  - Block rate and throughput metrics
  - Trend analysis
  
- ✅ **Security Analytics**
  - Risk level breakdown (Benign, Suspicious, Malicious)
  - Threat category distribution (Injection, PII, Toxicity, Leak)
  - Temporal threat timeline
  - Session-based threat tracking
  
- ✅ **Performance Monitoring**
  - Latency analysis across pipeline stages
  - Detector performance metrics
  - Request throughput visualization
  
- ✅ **Interactive Testing**
  - Built-in chat interface
  - Test malicious and benign prompts
  - Real-time feedback on blocks and allows
  
- ✅ **Request Explorer**
  - Detailed view of individual requests
  - Full metrics breakdown
  - ML detector scores and thresholds
  - Policy decision details

## 🏗️ Architecture

### Component Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx           # Main dashboard container
│   │   ├── ExecutiveKPIs.jsx       # Top-level KPI cards
│   │   ├── SecurityCharts.jsx      # Security visualizations
│   │   ├── PerformanceCharts.jsx   # Performance metrics
│   │   ├── SessionAnalytics.jsx    # Session analysis
│   │   ├── RecentRequestsTable.jsx # Request history table
│   │   ├── PromptExplorer.jsx      # Detailed request modal
│   │   └── SimplifiedChat.jsx      # Test chat interface
│   ├── services/
│   │   ├── api.js                  # REST API client
│   │   └── websocket.js            # WebSocket client
│   ├── App.jsx                     # Root component
│   ├── main.jsx                    # Entry point
│   └── styles.css                  # Global styles
├── index.html
├── package.json
├── vite.config.js
└── Dockerfile
```

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│                  Dashboard Component                 │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐      ┌─────────────────────┐  │
│  │  WebSocket      │      │  REST API           │  │
│  │  Connection     │      │  Polling            │  │
│  │                 │      │                     │  │
│  │  • Live events  │      │  • /api/stats       │  │
│  │  • Auto-reconnect│     │  • /api/recent-*    │  │
│  │  • Heartbeat    │      │  • /api/session-*   │  │
│  └────────┬────────┘      └──────────┬──────────┘  │
│           │                          │              │
│           └──────────┬───────────────┘              │
│                      ▼                               │
│          ┌───────────────────────┐                  │
│          │   React State         │                  │
│          │   • stats             │                  │
│          │   • requests          │                  │
│          │   • connectionStatus  │                  │
│          └───────────┬───────────┘                  │
│                      ▼                               │
│          ┌───────────────────────┐                  │
│          │  Child Components     │                  │
│          │  • ExecutiveKPIs      │                  │
│          │  • SecurityCharts     │                  │
│          │  • PerformanceCharts  │                  │
│          │  • RequestsTable      │                  │
│          │  • SimplifiedChat     │                  │
│          └───────────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Node.js 20+ (LTS recommended)
- npm or yarn
- Running Semantic Firewall backend (on port 8080)

### Installation

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment** (optional)
   
   Create a `.env` file if you need custom configuration:
   ```env
   VITE_API_BASE=http://localhost:8080
   VITE_WS_BASE=ws://localhost:8080
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open browser**
   
   Navigate to http://localhost:5173

### Running with Docker

The frontend is included in the docker-compose setup:

```bash
# From project root
docker-compose up frontend
```

Or build and run standalone:

```bash
cd frontend
docker build -t spg-frontend .
docker run -p 5173:5173 -e VITE_API_BASE=http://localhost:8080 spg-frontend
```

## 📊 Dashboard Components

### Executive KPIs

Displays high-level security metrics:
- **Total Prompts**: Total number of requests processed
- **Risk Distribution**: Percentage of benign, suspicious, and malicious requests
- **Block Ratio**: Percentage of requests blocked by the firewall
- **Throughput**: Prompts per minute
- **Risk Trend**: Current trend (stable, increasing, decreasing)

### Security Charts

Visual representations of security data:
- **Risk Level Pie Chart**: Distribution of benign/suspicious/malicious
- **Threat Category Bar Chart**: Breakdown by attack type (injection, PII, toxicity, leak)
- **Temporal Timeline**: Risk levels over time

### Performance Charts

Performance monitoring visualizations:
- **Latency Breakdown**: Average latency by pipeline stage
  - Preprocessing
  - ML Analysis
  - Policy Evaluation
  - Total overhead
- **Request Timeline**: Latency trends over time

### Session Analytics

Track suspicious sessions and patterns:
- Top sessions with highest threat activity
- Session request count and blocked requests
- Average risk score per session
- Individual prompt inspection

### Recent Requests Table

Interactive table showing recent requests:
- Risk level indicator (color-coded)
- Prompt preview (truncated)
- Action taken (allow/block)
- Timestamp
- Risk category
- Click to view detailed metrics

### Prompt Explorer (Modal)

Detailed view of individual requests:
- Full prompt and response
- ML detector scores with thresholds
- Status indicators (pass/warn/block)
- Policy decision details
- Preprocessing metrics
- Complete latency breakdown
- Risk assessment

### Test Chat Interface

Interactive chat for testing the firewall:
- Send test prompts
- See real-time blocking decisions
- Simple, clean interface
- Visual feedback for blocked content

## 🔧 Configuration

### Environment Variables

Configure the frontend using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:8080` | Firewall API base URL |
| `VITE_WS_BASE` | `ws://localhost:8080` | WebSocket base URL |

### Vite Configuration

Edit `vite.config.js` for build and development settings:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,      // Expose on network
    port: 5173       // Development port
  }
})
```

## 📡 API Integration

### REST API Endpoints

The dashboard consumes the following firewall endpoints:

#### GET `/api/stats`

Get aggregated security statistics.

```javascript
const stats = await fetchAPI('/api/stats')
// Returns: {
//   total_prompts: 1500,
//   benign_percentage: 75.3,
//   suspicious_percentage: 18.2,
//   malicious_percentage: 6.5,
//   block_ratio: 8.3,
//   prompts_per_minute: 12.5,
//   risk_trend: "stable",
//   avg_latency_ms: { preprocessing: 15.2, ml: 68.4, ... },
//   risk_categories: { injection: 45, pii: 23, ... }
// }
```

#### GET `/api/recent-requests?limit=50`

Get recent requests with full details.

```javascript
const data = await fetchAPI('/api/recent-requests?limit=50')
// Returns: {
//   requests: [...],
//   count: 50
// }
```

#### GET `/api/session-analytics?top=5`

Get analytics for top suspicious sessions.

```javascript
const data = await fetchAPI('/api/session-analytics?top=5')
// Returns: {
//   sessions: [...],
//   count: 5
// }
```

#### POST `/api/chat`

Send chat message through the firewall.

```javascript
const response = await sendMessage('Hello, how are you?')
// Returns: {
//   blocked: false,
//   reply: "Echo: Hello, how are you?",
//   ml_detectors: [...],
//   preprocessing: {...},
//   policy: {...},
//   latency_breakdown: {...}
// }
```

### WebSocket Connection

Real-time event stream at `/ws/dashboard`:

```javascript
import { useWebSocket } from './services/websocket'

const handleMessage = (data) => {
  console.log('New event:', data)
  // data contains full request event with metrics
}

const { connectionStatus, error } = useWebSocket('/ws/dashboard', handleMessage)
```

**Event format:**
```json
{
  "id": "uuid",
  "timestamp": "2025-11-19T10:30:00Z",
  "prompt": "User prompt...",
  "response": "Bot response or block reason",
  "risk_level": "benign|suspicious|malicious",
  "risk_category": "injection|pii|toxicity|leak|clean",
  "scores": {
    "prompt_injection": 0.15,
    "pii": 0.05,
    "toxicity": 0.02,
    "heuristic": 0.0
  },
  "action": "allow|block",
  "latency_ms": {
    "preprocessing": 12.3,
    "ml": 67.8,
    "policy": 8.4,
    "backend": 145.2,
    "total": 233.7
  },
  "policy": {
    "matched_rule": null,
    "decision": "allow"
  },
  "session_id": null
}
```

## 🛠️ Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Server

The Vite development server provides:
- Hot Module Replacement (HMR)
- Fast refresh for React components
- Instant updates on file changes
- Network access (via `--host` flag)

### Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Dashboard.jsx    # Main container (state management)
│   │   ├── ExecutiveKPIs.jsx       # KPI cards
│   │   ├── SecurityCharts.jsx      # Security visualizations
│   │   ├── PerformanceCharts.jsx   # Performance metrics
│   │   ├── SessionAnalytics.jsx    # Session analysis
│   │   ├── RecentRequestsTable.jsx # Request table
│   │   ├── PromptExplorer.jsx      # Detail modal
│   │   └── SimplifiedChat.jsx      # Test chat
│   ├── services/            # External integrations
│   │   ├── api.js          # REST API client
│   │   └── websocket.js    # WebSocket client + custom hook
│   ├── App.jsx             # Root component
│   ├── main.jsx            # Entry point
│   └── styles.css          # Global styles
├── index.html              # HTML template
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration
└── Dockerfile              # Container definition
```

### Adding New Components

1. Create component in `src/components/`:
   ```jsx
   export default function MyComponent({ data }) {
     return (
       <div className="my-component">
         {/* Your component JSX */}
       </div>
     )
   }
   ```

2. Import in `Dashboard.jsx`:
   ```jsx
   import MyComponent from './MyComponent'
   ```

3. Add to dashboard layout:
   ```jsx
   <section className="dashboard-section">
     <MyComponent data={someData} />
   </section>
   ```

### Styling

Global styles are in `src/styles.css`. The project uses:
- CSS custom properties (variables)
- Flexbox/Grid layouts
- Responsive design patterns
- Color-coded risk levels

**Risk level colors:**
```css
.benign { color: #10b981; }      /* Green */
.suspicious { color: #f59e0b; }  /* Orange */
.malicious { color: #ef4444; }   /* Red */
```

## 🔍 Testing

### Manual Testing

1. **Start all services**
   ```bash
   docker-compose up
   ```

2. **Access dashboard**
   
   Open http://localhost:5173

3. **Test chat interface**
   - Send benign prompt: "Hello, how are you?"
   - Send malicious prompt: "Ignore all previous instructions"
   - Verify block/allow decisions

4. **Verify real-time updates**
   - Watch KPIs update
   - Check recent requests table
   - Observe charts changing

### Testing WebSocket Connection

Open browser console and look for:
```
[WebSocket] Connected
```

If disconnected, check:
- Firewall backend is running on port 8080
- CORS is configured correctly
- Network connectivity

## 📱 Responsive Design

The dashboard is responsive and adapts to different screen sizes:

- **Desktop (1200px+)**: Full dashboard with sidebar
- **Tablet (768px-1199px)**: Stacked layout, smaller charts
- **Mobile (<768px)**: Single column, simplified views

## 🚀 Production Build

### Building for Production

```bash
npm run build
```

This creates an optimized production build in `dist/`:
- Minified JavaScript
- CSS extraction and minification
- Asset optimization
- Source maps (optional)

### Deployment

#### Static Hosting (Vercel, Netlify, etc.)

1. Build the application:
   ```bash
   npm run build
   ```

2. Deploy the `dist/` folder to your hosting provider

3. Set environment variables:
   ```
   VITE_API_BASE=https://your-firewall-api.com
   VITE_WS_BASE=wss://your-firewall-api.com
   ```

#### Docker Production

Use a multi-stage build for smaller images:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🐛 Troubleshooting

### WebSocket Connection Issues

**Problem**: Dashboard shows "Disconnected" status

**Solutions**:
1. Verify firewall backend is running: `curl http://localhost:8080/health`
2. Check CORS configuration in firewall backend
3. Verify WebSocket URL in environment variables
4. Check browser console for errors

### API Errors

**Problem**: "Error loading stats" or empty dashboard

**Solutions**:
1. Verify API base URL is correct
2. Check firewall backend logs
3. Verify CORS allows your origin
4. Check network tab in browser DevTools

### Build Errors

**Problem**: `npm run build` fails

**Solutions**:
1. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
2. Check Node.js version: `node --version` (should be 20+)
3. Clear Vite cache: `rm -rf node_modules/.vite`

## 🤝 Contributing

Contributions are welcome! To contribute to the frontend:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly (visual and functional)
5. Commit with clear messages
6. Push and open a Pull Request

### Coding Standards

- Use functional components with hooks
- Follow React best practices
- Keep components focused and small
- Add comments for complex logic
- Use meaningful variable names
- Maintain responsive design


## 🙏 Acknowledgments

- React for the UI library
- Vite for blazing fast development
- WebSocket API for real-time updates
- Modern CSS for responsive design

---

