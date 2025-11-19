# Dashboard Ejecutivo SPG - Semantic Firewall

## Descripción General

Dashboard en tiempo real para monitoreo y análisis de seguridad del Semantic Firewall de SPG. Proporciona visualización ejecutiva de KPIs, análisis de amenazas, inspección profunda de prompts y monitoreo de rendimiento.

## Características Principales

### 🎯 KPIs Ejecutivos en Tiempo Real
- **Total de Prompts**: Contador animado con total de peticiones procesadas
- **Porcentaje Benignos**: Prompts seguros que pasaron el firewall
- **Porcentaje Sospechosos**: Prompts con indicios de riesgo medio
- **Porcentaje Maliciosos**: Prompts bloqueados por alto riesgo
- **Ratio Bloqueados/Permitidos**: Proporción de peticiones bloqueadas vs permitidas
- **Prompts por Minuto**: Tasa de procesamiento en tiempo real

### 📊 Gráficos de Seguridad
- **Distribución de Categorías de Riesgo**: Gráfico de dona mostrando:
  - Injection (rojo)
  - PII (naranja)
  - Toxicity (amarillo)
  - Leak (morado)
  - Harmful (rosa)
  - Clean (verde)
- **Tendencia Temporal**: Gráfico de líneas mostrando evolución de categorías en tiempo real

### ⚡ Gráficos de Rendimiento
- **Latencia Promedio por Fase**: Barras horizontales para:
  - Preprocessing (azul)
  - ML Analysis (verde)
  - Policy Evaluation (amarillo)
  - Backend (morado)
- **Timeline de Latencias**: Scatter plot con latencia total y promedio móvil

### 📋 Tabla de Peticiones Recientes
- Vista tabular de últimas 50-100 peticiones
- Filtros rápidos: Todas / Bloqueadas / Sospechosas
- Auto-scroll opcional para nuevas peticiones
- Click en fila para inspección profunda

### 🔍 Prompt Explorer (Inspección Profunda)
Modal con información detallada de cada petición:
- Prompt completo (enmascarado si contiene PII)
- Respuesta final
- Scores de todos los modelos ML
- Heurísticas disparadas
- Decisión de política OPA/Rego
- Desglose completo de latencias
- Info de preprocesamiento

### 📈 Análisis de Sesiones
Panel simplificado mostrando:
- Top 5 sesiones con más actividad sospechosa
- Total de requests por sesión
- Contadores de maliciosos y sospechosos
- Última actividad

⚠️ **Nota**: Análisis basado en sesiones temporales en memoria sin autenticación real.

### 💬 Chat Simplificado
- Interfaz compacta en sidebar derecho
- Sin métricas visibles (solo para testing)
- Mensajes genéricos de bloqueo
- Integración directa con firewall

## Arquitectura Técnica

### Backend (FastAPI + WebSocket)

#### Componentes Principales

**1. MetricsManager** (`firewall/metrics_manager.py`)
- Cola circular thread-safe de 500 peticiones
- Cálculo en tiempo real de KPIs ejecutivos
- Agregación temporal para gráficos
- Analítica básica de sesiones

**2. WebSocket Manager** (`firewall/semantic_firewall.py`)
- Endpoint: `/ws/dashboard`
- Sistema de heartbeat (ping/pong cada 30s)
- Cola asyncio para eventos ordenados
- Broadcast automático a todos los clientes
- Auto-reconexión con backoff exponencial

**3. Endpoints REST**
- `GET /api/stats` - KPIs ejecutivos y estadísticas agregadas
- `GET /api/recent-requests?limit=N` - Últimas N peticiones
- `GET /api/session-analytics?top=N` - Top N sesiones sospechosas
- `GET /api/temporal-breakdown?minutes=N` - Breakdown temporal de categorías

#### Esquema Estándar de Eventos WebSocket

```json
{
  "id": "uuid",
  "timestamp": "ISO8601",
  "prompt": "string (masked if PII)",
  "response": "string",
  "risk_level": "benign | suspicious | malicious",
  "risk_category": "injection | pii | toxicity | leak | harmful | clean",
  "scores": {
    "prompt_injection": 0.42,
    "pii": 0.10,
    "toxicity": 0.07,
    "heuristic": 0.0
  },
  "heuristics": ["bypass_attempt"],
  "policy": {
    "matched_rule": "string",
    "decision": "allow | block"
  },
  "action": "allow | block",
  "latency_ms": {
    "preprocessing": 4,
    "ml": 16,
    "policy": 5,
    "backend": 22,
    "total": 47
  },
  "session_id": "optional",
  "preprocessing_info": {
    "original_length": 150,
    "normalized_length": 145,
    "word_count": 25
  }
}
```

### Frontend (React + WebSocket + Canvas)

#### Componentes Principales

1. **Dashboard.jsx** - Layout principal y orquestación
2. **ExecutiveKPIs.jsx** - 6 tarjetas de KPIs animadas
3. **SecurityCharts.jsx** - Gráficos de seguridad (Canvas API)
4. **PerformanceCharts.jsx** - Gráficos de rendimiento (Canvas API)
5. **RecentRequestsTable.jsx** - Tabla con filtros y auto-scroll
6. **PromptExplorer.jsx** - Modal de inspección profunda
7. **SessionAnalytics.jsx** - Panel de análisis de sesiones
8. **SimplifiedChat.jsx** - Chat minimalista sin métricas

#### Servicios

**WebSocket Service** (`services/websocket.js`)
- Hook `useWebSocket()` con auto-reconexión
- Manejo de heartbeat (responde a pings automáticamente)
- Backoff exponencial para reconexiones
- Parser de eventos con esquema estándar
- Estados: conectado / conectando / reconectando / desconectado

## Configuración

### Variables de Entorno

**Backend:**
```bash
# .env (firewall/)
BACKEND_URL=http://backend:8000
TENANT_ID=default
DEBUG=false
```

**Frontend:**
```bash
# .env (frontend/)
VITE_API_BASE=http://localhost:8080
VITE_WS_BASE=ws://localhost:8080
```

## Ejecución

### Desarrollo Local

1. **Backend (Firewall):**
```bash
cd firewall
pip install -r requirements.txt
uvicorn semantic_firewall:app --reload --port 8080
```

2. **Frontend:**
```bash
cd frontend
npm install
npm run dev
```

3. **Backend Simple (opcional para testing):**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Docker Compose

```bash
docker-compose up --build
```

Acceso:
- Dashboard: http://localhost:5173
- API Firewall: http://localhost:8080
- WebSocket: ws://localhost:8080/ws/dashboard

## Flujo de Datos

1. Usuario envía mensaje desde chat simplificado
2. Backend procesa con firewall completo (preprocess → ML → policy)
3. Backend genera evento estandarizado
4. Evento se agrega a MetricsManager (memoria)
5. Evento se envía a cola asyncio
6. WebSocket hace broadcast a todos los dashboards conectados
7. Frontend actualiza KPIs, gráficos y tabla en tiempo real
8. Chat muestra solo respuesta simple o mensaje genérico de bloqueo
9. Admin puede hacer click en tabla para ver detalles en PromptExplorer

## Métricas y Cálculos

### KPIs Ejecutivos

- **Total Prompts**: `len(requests)`
- **% Benignos**: `(benign_count / total) * 100`
- **% Sospechosos**: `(suspicious_count / total) * 100`
- **% Maliciosos**: `(malicious_count / total) * 100`
- **Ratio**: `f"1:{allowed // blocked if blocked > 0 else allowed}"`
- **Prompts/Min**: Calculado sobre ventana deslizante de 5 minutos
- **Tendencia**: Comparación últimos 10% vs previos

### Latencias

Promedio calculado sobre todas las peticiones en memoria:
- `preprocessing_avg = sum(preprocessing_latencies) / total`
- `ml_avg = sum(ml_latencies) / total`
- `policy_avg = sum(policy_latencies) / total`
- `backend_avg = sum(backend_latencies) / total`

## Limitaciones Conocidas

1. **Sin Autenticación Real**: El análisis de sesiones usa session_id temporal en memoria
2. **Datos en Memoria**: Al reiniciar el servidor se pierden todas las métricas
3. **Límite de Peticiones**: Solo se mantienen últimas 500 peticiones en memoria
4. **Sin Persistencia**: No hay almacenamiento en base de datos

## Mejoras Futuras

### Para Producción

1. **Autenticación y Autorización**
   - Integrar con sistema de auth real
   - Roles: Admin, Analista, Viewer
   - Session tracking persistente

2. **Persistencia de Datos**
   - Base de datos (PostgreSQL / MongoDB)
   - Retención configurable de métricas históricas
   - Exportación de reportes

3. **Alertas y Notificaciones**
   - Webhooks para eventos críticos
   - Email/Slack notifications
   - Umbrales configurables

4. **Análisis Avanzado**
   - Machine learning para detección de patrones
   - Correlación de eventos
   - Predicción de amenazas

5. **Escalabilidad**
   - Redis para caché distribuido
   - Message queue (RabbitMQ/Kafka) para eventos
   - Clustering de WebSocket

## Troubleshooting

### WebSocket no conecta

**Problema**: Dashboard muestra "Desconectado"

**Soluciones**:
1. Verificar que el backend esté corriendo en puerto correcto
2. Verificar variables de entorno `VITE_WS_BASE`
3. Revisar consola del navegador para errores
4. Verificar CORS en backend

### Gráficos no se muestran

**Problema**: Canvas en blanco

**Soluciones**:
1. Verificar que haya datos suficientes (mínimo 1-2 peticiones)
2. Revisar consola para errores de JavaScript
3. Verificar que el navegador soporte Canvas API

### Métricas incorrectas

**Problema**: KPIs muestran valores extraños

**Soluciones**:
1. Verificar que los eventos WebSocket sigan el esquema estándar
2. Revisar logs del backend para errores
3. Refrescar la página para recargar datos desde API

## Soporte

Para issues o preguntas:
- Revisar logs del backend: `firewall/logs/`
- Revisar consola del navegador (F12)
- Verificar estado de conexión WebSocket en Dashboard

## Licencia

Copyright © 2024 SPG - Todos los derechos reservados

