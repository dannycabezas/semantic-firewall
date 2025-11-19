<!-- 80c16a11-6a8d-49b9-8cc6-31badc9c98bb daaf9cc6-95f2-4a99-af73-5a5bbf6c08d5 -->
# Dashboard Ejecutivo SPG - Tiempo Real Mejorado

## Objetivo

Crear un dashboard ejecutivo intuitivo y altamente detallado que permita visualizar en tiempo real el análisis completo de todas las peticiones procesadas por el firewall semántico, incluyendo KPIs ejecutivos, analítica de seguridad avanzada, inspección profunda de prompts, monitoreo de rendimiento y análisis básico de comportamiento.

## Arquitectura Mejorada

### Backend (FastAPI + WebSocket con Heartbeat)

**Sistema robusto de eventos en tiempo real:**

- WebSocket endpoint `/ws/dashboard` con sistema de heartbeat (ping/pong cada 30s)
- Gestor de métricas en memoria que almacena últimas 200-500 peticiones con detalles completos
- Cola interna de eventos para garantizar orden y consistencia en broadcasts
- Broadcast automático con esquema JSON estandarizado
- Tracking básico de sesiones (session_id temporal en memoria para analítica)
- Endpoints REST mínimos: `/api/stats` y `/api/recent-requests?limit=N`

**Esquema Estándar de Eventos WebSocket:**

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
  "heuristics": ["bypass_attempt", "roleplay_pattern"],
  "policy": {
    "matched_rule": "string",
    "decision": "allow | block | warn"
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

### Frontend (React + WebSocket + Canvas Charts)

**Layout Multipanel Responsive:**

1. **Fila Superior**: 6 KPIs ejecutivos en tarjetas
2. **Fila Media Izquierda**: Gráficos de seguridad (distribución + tendencia)
3. **Fila Media Derecha**: Gráficos de rendimiento + analítica simplificada
4. **Fila Inferior**: Tabla de peticiones recientes (expandible)
5. **Sidebar Derecho**: Chat simplificado sin métricas
6. **Modal Flotante**: Prompt Explorer para inspección profunda

## Implementación Detallada

### 1. Backend - MetricsManager Mejorado

Archivo: `firewall/metrics_manager.py`

**Funcionalidades:**

- Cola circular thread-safe de 500 peticiones
- Calcular KPIs ejecutivos en tiempo real:
  - Total prompts, % benignos/sospechosos/maliciosos
  - Ratio bloqueados/permitidos
  - Prompts por minuto (rolling window)
  - Tendencia de riesgo
- Clasificar por categorías de riesgo
- Analítica básica de sesiones (sin auth real)
- Agregación temporal para gráficos de tendencia
- Métodos: `add_request()`, `get_stats()`, `get_recent()`, `get_risk_breakdown()`, `get_session_analytics()`

### 2. Backend - WebSocket con Heartbeat

Modificar `firewall/semantic_firewall.py`:

**Agregar:**

- Endpoint WebSocket `/ws/dashboard` con ConnectionManager
- Sistema de heartbeat (ping cada 30s, desconexión si no responde en 90s)
- Cola asyncio para eventos (garantiza orden)
- Broadcast del esquema estandarizado a todos los clientes
- Integrar con MetricsManager para cada request procesado
- Manejo de conexiones/desconexiones limpias

**Endpoints REST:**

- `GET /api/stats` → KPIs ejecutivos + breakdown de riesgos
- `GET /api/recent-requests?limit=50` → Últimas N peticiones completas

### 3. Frontend - Chat Simplificado

Crear `frontend/src/components/SimplifiedChat.jsx`:

**Características:**

- Diseño compacto para sidebar (300-400px)
- Sin métricas visibles, solo mensajes
- Respuesta exitosa: mostrar reply del backend
- Respuesta bloqueada: "🛡️ Contenido no permitido por políticas de seguridad"
- Estilo minimalista y limpio
- Eliminar completamente MetricsPanel.jsx (ya no se usa)

### 4. Frontend - KPIs Ejecutivos

Crear `frontend/src/components/ExecutiveKPIs.jsx`:

**6 Tarjetas con métricas en tiempo real:**

1. Total de Prompts (contador animado)
2. % Benignos (con indicador verde)
3. % Sospechosos (con indicador amarillo)
4. % Maliciosos/Bloqueados (con indicador rojo)
5. Ratio Bloqueados/Permitidos (formato "1:X")
6. Prompts por Minuto (rate con mini-gráfico de línea)

**Actualización vía WebSocket y cálculo local incremental**

### 5. Frontend - Prompt Explorer (Inspección Profunda)

Crear `frontend/src/components/PromptExplorer.jsx`:

**Modal/Panel lateral con detalles completos:**

- Prompt completo (enmascarado si contiene PII)
- Respuesta final enviada al usuario
- Todos los scores ML detallados:
  - Prompt Injection (barra + valor)
  - PII Detection (barra + valor)
  - Toxicity (barra + valor)
  - Heuristic (barra + valor)
- Heurísticas disparadas (lista con badges)
- Decisión de política OPA/Rego (nombre de regla)
- Acción tomada (allow/block/warn) con badge de color
- Desglose de latencias por fase (gráfico de barras horizontal)
- Info de preprocesamiento (length, word_count)
- Session ID si está disponible
- Timestamp completo

**Activación:** Click en cualquier fila de RecentRequestsTable

### 6. Frontend - Risk Category Breakdown

Crear `frontend/src/components/SecurityCharts.jsx`:

**Gráficos con Canvas API:**

a) **Gráfico de Torta/Dona**: Distribución de categorías de riesgo

   - Injection (rojo)
   - PII (naranja)
   - Toxicity (amarillo)
   - Leak (morado)
   - Harmful (rosa)
   - Clean (verde)

b) **Gráfico de Tendencia Temporal**: Líneas por categoría en últimos N minutos

   - Eje X: timestamps agrupados por minuto
   - Eje Y: cantidad de detecciones
   - Múltiples líneas de colores

**Actualización en tiempo real vía WebSocket**

### 7. Frontend - Performance Charts

Crear `frontend/src/components/PerformanceCharts.jsx`:

**Gráficos con Canvas API:**

a) **Latencia Promedio por Fase**: Gráfico de barras horizontal

   - Preprocessing (azul)
   - ML Analysis (verde)
   - Policy Evaluation (amarillo)
   - Backend (morado)

b) **Timeline de Latencias**: Gráfico de línea con últimas N peticiones

   - Scatter plot con latencia total
   - Línea de promedio móvil

### 8. Frontend - User Behavior Analytics (Simplificado)

Crear `frontend/src/components/SessionAnalytics.jsx`:

**NOTA**: Sin sistema de auth real, análisis básico por session_id temporal

**Panel simplificado mostrando:**

- Top 5 sesiones con más prompts sospechosos
- Detección de patrones repetitivos (ej: múltiples intentos de bypass)
- Tabla simple: session_id | total_requests | malicious_count | last_seen

**Limitación clara**: "Análisis basado en sesiones temporales sin autenticación"

### 9. Frontend - Recent Requests Table

Mejorar `frontend/src/components/RecentRequestsTable.jsx`:

**Columnas:**

- Timestamp (formato relativo: "hace 2 min")
- Prompt (truncado con "...")
- Risk Level (badge con color)
- Risk Category (badge)
- Action (allow/block badge)
- Latencia Total (ms)
- Session ID (opcional)

**Funcionalidad:**

- Click en fila → abre PromptExplorer con detalles completos
- Auto-scroll con nuevas peticiones
- Paginación o scroll infinito
- Filtros rápidos: All | Blocked | Suspicious

### 10. Frontend - Dashboard Layout Principal

Crear `frontend/src/components/Dashboard.jsx`:

**Grid CSS Responsive:**

```
+----------------------------------+----------+
|        Executive KPIs (6)        | Simplified |
+----------------------------------+   Chat   |
|  Security  |  Performance Chart  |   (Sidebar)|
|   Charts   |  Session Analytics  |          |
+----------------------------------+----------+
|      Recent Requests Table       |          |
+----------------------------------+----------+
```

**Integración:**

- Conexión WebSocket global
- Estado compartido entre componentes
- Actualizaciones en tiempo real
- Manejo de reconexión automática

### 11. Frontend - WebSocket Service

Crear `frontend/src/services/websocket.js`:

**Hook personalizado `useWebSocket()`:**

- Conexión a `/ws/dashboard`
- Auto-reconexión con backoff exponencial
- Manejo de heartbeat (responder a ping)
- Parser de eventos con esquema estándar
- Estado de conexión (conectado/desconectado/reconectando)
- Callback para eventos recibidos

### 12. Estilos Modernos Mejorados

Actualizar `frontend/src/styles.css`:

**Agregar:**

- Grid layout para dashboard multipanel
- Cards con glassmorphism y sombras suaves
- Animaciones de entrada para nuevos datos
- Badges de colores para risk levels
- Modal overlay para PromptExplorer
- Responsive breakpoints (tablet, mobile)
- Animaciones de contador para KPIs
- Estilos para gráficos Canvas

## Flujo de Datos

1. Usuario envía mensaje desde chat simplificado
2. Backend procesa request con firewall completo
3. Backend genera evento con esquema estándar
4. Backend agrega a MetricsManager y envía a cola de eventos
5. WebSocket hace broadcast a todos los dashboards conectados
6. Frontend actualiza KPIs, gráficos, tabla en tiempo real
7. Chat muestra solo respuesta simple o mensaje de bloqueo genérico
8. Admin puede hacer click en tabla para ver detalles en PromptExplorer

## Archivos Clave

### Backend

- `firewall/metrics_manager.py` (nuevo) - Gestor de métricas con KPIs
- `firewall/semantic_firewall.py` (modificar) - WebSocket + heartbeat + endpoints
- `firewall/requirements.txt` (modificar) - Agregar websockets

### Frontend

- `frontend/src/App.jsx` (modificar) - Integrar Dashboard
- `frontend/src/components/Dashboard.jsx` (nuevo) - Layout principal
- `frontend/src/components/SimplifiedChat.jsx` (nuevo) - Chat sin métricas
- `frontend/src/components/ExecutiveKPIs.jsx` (nuevo) - KPIs ejecutivos
- `frontend/src/components/PromptExplorer.jsx` (nuevo) - Inspección profunda
- `frontend/src/components/SecurityCharts.jsx` (nuevo) - Gráficos de seguridad
- `frontend/src/components/PerformanceCharts.jsx` (nuevo) - Gráficos de rendimiento
- `frontend/src/components/SessionAnalytics.jsx` (nuevo) - Analítica simplificada
- `frontend/src/components/RecentRequestsTable.jsx` (nuevo) - Tabla de peticiones
- `frontend/src/services/websocket.js` (nuevo) - Hook WebSocket
- `frontend/src/styles.css` (actualizar) - Estilos para dashboard

### Archivos a Eliminar

- `frontend/src/components/MetricsPanel.jsx` (ya no se usa)
- `frontend/src/components/ChatWindow.jsx` (reemplazado por SimplifiedChat)

## Dependencias

**Backend:**

- `websockets` (ya incluido en FastAPI[standard])

**Frontend:**

- Sin nuevas dependencias (usar Canvas API nativo para gráficos)

## Notas Importantes

**Limitación de User Behavior Analytics:**

El sistema actual no tiene autenticación real. Para el POC implementaremos tracking básico por `session_id` temporal almacenado en memoria. Esto permite análisis básico de patrones pero se pierde al reiniciar el servidor. Para producción se recomienda integrar con sistema de auth real.

**Esquema Estandarizado:**

Todos los eventos WebSocket siguen el esquema JSON definido arriba, garantizando consistencia entre backend y frontend.

### To-dos

- [ ] Crear MetricsManager para almacenar peticiones en memoria
- [ ] Implementar endpoint WebSocket y broadcast de eventos
- [ ] Crear endpoints REST para estadísticas agregadas
- [ ] Crear servicio WebSocket con auto-reconexión
- [ ] Simplificar ChatWindow eliminando métricas detalladas
- [ ] Crear componente LiveStatsCards con métricas en tiempo real
- [ ] Crear componente ThreatTimeline con lista de amenazas
- [ ] Crear componente SecurityCharts con gráficos de amenazas
- [ ] Crear componente PerformanceCharts con gráficos de latencia
- [ ] Crear componente RecentRequestsTable con peticiones recientes
- [ ] Crear Dashboard principal integrando todos los componentes
- [ ] Actualizar estilos CSS para dashboard y componentes