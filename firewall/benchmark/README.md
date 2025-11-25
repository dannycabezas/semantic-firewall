# Benchmark System - Semantic Firewall

Sistema de benchmarks para evaluar el rendimiento del firewall semántico contra datasets de Hugging Face.

## Características

- ✅ Carga automática de datasets desde Hugging Face Hub
- ✅ Ejecución asíncrona de benchmarks
- ✅ Métricas detalladas: Precision, Recall, F1-Score, Accuracy
- ✅ Matriz de confusión (TP, FP, TN, FN)
- ✅ Análisis de errores: Falsos Positivos y Falsos Negativos
- ✅ Almacenamiento persistente en SQLite
- ✅ Dashboard interactivo en React
- ✅ Soporte para cancelación de benchmarks
- ✅ Exportación de resultados a CSV

## Arquitectura

### Backend

```
firewall/benchmark/
├── __init__.py
├── database.py              # Schema SQLite y operaciones DB
├── dataset_loader.py        # Carga datasets de HuggingFace
├── benchmark_runner.py      # Orquestación de benchmarks
├── metrics_calculator.py    # Cálculo de métricas
├── init_db.py              # Script de inicialización
└── README.md
```

### Frontend

```
frontend/src/components/benchmarks/
├── BenchmarkDashboard.jsx      # Componente principal
├── BenchmarkExecutor.jsx       # Formulario para iniciar benchmarks
├── BenchmarkHistory.jsx        # Historial de ejecuciones
├── BenchmarkMetricsView.jsx    # Visualización de métricas
└── ErrorAnalysisView.jsx       # Análisis de FP/FN
```

## Uso

### 1. Inicializar la Base de Datos

```bash
cd firewall
python -m benchmark.init_db
```

### 2. Iniciar el Firewall

El sistema de benchmarks se inicializa automáticamente al arrancar el firewall:

```bash
python semantic_firewall.py
```

### 3. Acceder al Dashboard

Navega a `http://localhost:5173/benchmarks` en el frontend.

### 4. Ejecutar un Benchmark

1. Ve a la pestaña "Nueva Ejecución"
2. Ingresa el nombre del dataset (ej: `jackhhao/jailbreak-classification`)
3. Selecciona el split (test/train/validation)
4. Opcionalmente, limita el número de muestras
5. Click en "Iniciar Benchmark"

### 5. Ver Resultados

- **Métricas**: Visualiza F1-Score, Accuracy, Matriz de Confusión
- **Análisis de Errores**: Explora falsos positivos y negativos con detalles de scores ML
- **Historial**: Compara múltiples ejecuciones

## Datasets Soportados

El sistema mapea automáticamente estos datasets:

### jackhhao/jailbreak-classification
- **Columna prompt**: `prompt`
- **Columna label**: `type`
- **Valores**: `"jailbreak"` (malicioso) o `"benign"` (seguro)

### Datasets Personalizados

Para agregar soporte a otros datasets, edita `dataset_loader.py`:

```python
DATASET_MAPPINGS = {
    "tu-usuario/tu-dataset": {
        "prompt_column": "text",
        "label_column": "label",
        "label_mapping": {
            "attack": "jailbreak",
            "safe": "benign"
        }
    }
}
```

## API Endpoints

### POST /api/benchmarks/start
Inicia un nuevo benchmark.

**Request:**
```json
{
  "dataset_name": "jackhhao/jailbreak-classification",
  "dataset_split": "test",
  "max_samples": 100,
  "tenant_id": "benchmark"
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "status": "running",
  "message": "Benchmark started successfully"
}
```

### GET /api/benchmarks/status/{run_id}
Obtiene el estado actual de un benchmark.

**Response:**
```json
{
  "run_id": "uuid",
  "status": "running",
  "total_samples": 100,
  "processed_samples": 45,
  "progress_percent": 45.0,
  "elapsed_time_seconds": 67.5,
  "estimated_remaining_seconds": 82.5
}
```

### GET /api/benchmarks/metrics/{run_id}
Obtiene métricas calculadas.

**Response:**
```json
{
  "true_positives": 85,
  "false_positives": 5,
  "true_negatives": 90,
  "false_negatives": 20,
  "precision": 0.9444,
  "recall": 0.8095,
  "f1_score": 0.8717,
  "accuracy": 0.8750,
  "avg_latency_ms": 125.5
}
```

### GET /api/benchmarks/errors/{run_id}
Obtiene análisis de errores detallado.

**Response:**
```json
{
  "false_positives": [
    {
      "id": 1,
      "input_text": "prompt bloqueado incorrectamente",
      "expected_label": "benign",
      "predicted_label": "blocked",
      "analysis_details": {
        "reason": "High toxicity score",
        "ml_signals": {
          "prompt_injection_score": 0.65,
          "toxicity_score": 0.82,
          "pii_score": 0.12
        }
      }
    }
  ],
  "false_negatives": [...]
}
```

## Interpretación de Métricas

### Matriz de Confusión

- **True Positive (TP)**: Ataques detectados correctamente ✅
- **False Negative (FN)**: Ataques que pasaron ❌ (CRÍTICO - riesgo de seguridad)
- **False Positive (FP)**: Usuarios legítimos bloqueados ⚠️ (impacto UX)
- **True Negative (TN)**: Usuarios legítimos permitidos ✅

### Métricas de Clasificación

- **Precision** = TP / (TP + FP) - De todo lo bloqueado, cuánto era realmente malicioso
- **Recall** = TP / (TP + FN) - De todos los ataques, cuántos detectamos
- **F1-Score** = 2 * (Precision * Recall) / (Precision + Recall) - Balance entre Precision y Recall
- **Accuracy** = (TP + TN) / Total - Porcentaje de aciertos totales

### Casos de Uso para Ajuste

#### FN Alto (Falsos Negativos)
- **Problema**: Ataques pasando el firewall
- **Solución**: 
  - Aumentar sensibilidad de detectores
  - Reducir thresholds
  - Entrenar modelos con nuevos ejemplos

#### FP Alto (Falsos Positivos)
- **Problema**: Usuarios legítimos bloqueados
- **Solución**:
  - Reducir sensibilidad
  - Aumentar thresholds
  - Refinar reglas heurísticas

## Variables de Entorno

```bash
# Ruta de la base de datos de benchmarks
BENCHMARK_DB_PATH=/data/benchmarks.db
```

## Dependencias

Backend:
- `datasets` - Hugging Face datasets library
- `aiosqlite` - SQLite async
- `numpy` - Cálculos estadísticos

Frontend:
- `react-router-dom` - Routing
- `recharts` - Visualizaciones

## Troubleshooting

### Error: "Benchmark system not initialized"
- Verifica que la base de datos se haya inicializado correctamente
- Revisa los logs del servidor para errores de startup

### Benchmark se queda en "running" indefinidamente
- Verifica logs del servidor para excepciones
- Chequea conectividad con Hugging Face Hub
- Asegúrate de que el dataset existe y es accesible

### Métricas no disponibles
- Las métricas solo se calculan cuando el benchmark completa
- Espera a que el status sea "completed"
- Si el benchmark falló, no habrá métricas

## Contribuir

Para agregar soporte a nuevos tipos de datasets:

1. Edita `DATASET_MAPPINGS` en `dataset_loader.py`
2. Agrega tests para el nuevo formato
3. Actualiza esta documentación

