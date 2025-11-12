<!-- cbd593c1-0bfe-4ae5-af12-3957936bda66 7ed72c31-21d1-47a5-807c-6980ec72489c -->
# Plan de Implementación: Firewall Semántico con Arquitectura Hexagonal

## Objetivo

Refactorizar el firewall actual para integrar 4 módulos nuevos usando **Arquitectura Hexagonal (Ports & Adapters)** con **dependency injection** (`dependency-injector`), manteniendo la funcionalidad principal: si el prompt es permitido → llama al backend, si es bloqueado → deniega y envía respuesta.

## Principios Arquitectónicos

### Ports & Adapters (Hexagonal Architecture)

- **Ports (Interfaces)**: Contratos agnósticos usando ABC (Abstract Base Classes) de Python
- **Adapters (Implementaciones)**: Implementaciones concretas intercambiables
- **Dependency Injection**: Usar `dependency-injector` para centralizar dependencias
- **Core (Lógica de Negocio)**: Servicios que dependen solo de ports, no de adapters

### Beneficios para POC

- Cambiar tecnologías sin reescribir lógica (ej: Qdrant → Pinecone, ONNX → TensorFlow)
- Testing fácil con mocks/stubs
- Configuración centralizada de dependencias
- Código mantenible y extensible

## Estructura de Módulos

### 1. Preprocessor & Vectorizer (`firewall/preprocessor/`)

**Estructura:**

```
firewall/preprocessor/
├── __init__.py
├── ports/
│   ├── __init__.py
│   ├── normalizer_port.py          # INormalizer (ABC)
│   ├── vectorizer_port.py          # IVectorizer (ABC)
│   ├── feature_extractor_port.py   # IFeatureExtractor (ABC)
│   ├── vector_store_port.py        # IVectorStore (ABC) - Qdrant/Pinecone/etc
│   └── feature_store_port.py       # IFeatureStore (ABC) - Feast/dict/etc
├── adapters/
│   ├── __init__.py
│   ├── text_normalizer.py          # Implementa INormalizer
│   ├── sentence_transformer_vectorizer.py  # Implementa IVectorizer
│   ├── basic_feature_extractor.py  # Implementa IFeatureExtractor
│   ├── qdrant_vector_store.py      # Implementa IVectorStore
│   └── memory_feature_store.py     # Implementa IFeatureStore (mock POC)
└── preprocessor_service.py         # Core: usa ports inyectados
```

**Responsabilidades:**

- Normalizar texto (lowercase, limpieza, tokenización)
- Calcular embeddings (agnóstico: sentence-transformers/OpenAI/etc)
- Extraer features básicas
- Guardar vectores y features (agnóstico: Qdrant/Feast o mocks)

### 2. Fast ML Filter (`firewall/fast_ml_filter/`)

**Estructura:**

```
firewall/fast_ml_filter/
├── __init__.py
├── ports/
│   ├── __init__.py
│   ├── pii_detector_port.py        # IPIIDetector (ABC)
│   ├── toxicity_detector_port.py   # IToxicityDetector (ABC)
│   ├── heuristic_detector_port.py # IHeuristicDetector (ABC)
│   └── ml_model_port.py            # IMLModel (ABC) - genérico
├── adapters/
│   ├── __init__.py
│   ├── onnx_pii_detector.py        # Implementa IPIIDetector
│   ├── onnx_toxicity_detector.py   # Implementa IToxicityDetector
│   ├── regex_heuristic_detector.py # Implementa IHeuristicDetector
│   └── mock_pii_detector.py        # Mock para testing
└── ml_filter_service.py            # Core: orquesta detectores
```

**Responsabilidades:**

- Detectar PII (agnóstico: ONNX/TensorFlow/etc)
- Detectar toxicidad (agnóstico: modelo/interfaz)
- Aplicar heurísticas (usa reglas existentes)
- Retornar scores estructurados

### 3. Policy Engine (`firewall/policy_engine/`)

**Estructura:**

```
firewall/policy_engine/
├── __init__.py
├── ports/
│   ├── __init__.py
│   ├── policy_evaluator_port.py    # IPolicyEvaluator (ABC)
│   ├── policy_loader_port.py       # IPolicyLoader (ABC) - YAML/Rego/etc
│   └── tenant_context_port.py     # ITenantContextProvider (ABC)
├── adapters/
│   ├── __init__.py
│   ├── yaml_policy_loader.py       # Implementa IPolicyLoader
│   ├── rego_policy_loader.py       # Implementa IPolicyLoader (futuro)
│   └── memory_tenant_context.py   # Implementa ITenantContextProvider
├── policy_service.py               # Core: evaluación de políticas
└── policies.yaml                   # Reglas configurables
```

**Responsabilidades:**

- Cargar políticas (agnóstico: YAML/Rego/etc)
- Combinar señales: ML + heurísticas + contexto tenant
- Evaluar reglas (AND/OR, umbrales, excepciones)
- Retornar decisión: ALLOW/BLOCK con razón

### 4. Action Orchestrator (`firewall/action_orchestrator/`)

**Estructura:**

```
firewall/action_orchestrator/
├── __init__.py
├── ports/
│   ├── __init__.py
│   ├── action_executor_port.py     # IActionExecutor (ABC)
│   ├── logger_port.py              # ILogger (ABC) - structlog/print/etc
│   ├── alerter_port.py             # IAlerter (ABC) - Slack/webhook/etc
│   └── idempotency_store_port.py   # IIdempotencyStore (ABC) - Redis/dict/etc
├── adapters/
│   ├── __init__.py
│   ├── structlog_logger.py         # Implementa ILogger
│   ├── slack_alerter.py            # Implementa IAlerter (opcional)
│   └── memory_idempotency_store.py # Implementa IIdempotencyStore
└── orchestrator_service.py         # Core: ejecuta acciones
```

**Responsabilidades:**

- Ejecutar acciones idempotentes
- Logging estructurado (agnóstico: structlog/print/etc)
- Alertas (agnóstico: Slack/webhook/etc)
- Manejar idempotencia (agnóstico: Redis/dict/etc)

## Dependency Injection Container

### Archivo: `firewall/container.py`

**Responsabilidades:**

- Configurar `dependency-injector` Container
- Registrar todos los ports y adapters
- Proporcionar factory methods para servicios
- Permitir cambiar adapters fácilmente (config/env)

**Estructura:**

```python
from dependency_injector import containers, providers

class FirewallContainer(containers.DeclarativeContainer):
    # Configuración
    config = providers.Configuration()
    
    # Adapters - Preprocessor
    normalizer = providers.Factory(TextNormalizer)
    vectorizer = providers.Factory(SentenceTransformerVectorizer, model_name=config.vectorizer.model)
    vector_store = providers.Singleton(QdrantVectorStore, url=config.qdrant.url)
    
    # Adapters - Fast ML Filter
    pii_detector = providers.Singleton(ONNXPIIDetector, model_path=config.ml.pii_model)
    toxicity_detector = providers.Singleton(ONNXToxicityDetector, model_path=config.ml.toxicity_model)
    
    # Services - Core
    preprocessor_service = providers.Factory(
        PreprocessorService,
        normalizer=normalizer,
        vectorizer=vectorizer,
        vector_store=vector_store
    )
    # ... más servicios
```

## Refactorización del Firewall Principal

### Archivo: `firewall/semantic_firewall.py`

**Cambios:**

- Inyectar dependencias usando container
- Refactorizar `analyze_prompt()` para usar servicios
- Mantener endpoint `/api/chat` con misma interfaz
- Integrar flujo: Preprocessor → Fast ML Filter → Policy Engine → Action Orchestrator

**Flujo integrado:**

```python
from firewall.container import FirewallContainer

container = FirewallContainer()
container.config.from_yaml("config.yaml")

@app.post("/api/chat")
async def proxy_chat(payload: ChatIn):
    request_id = generate_request_id()
    
    # Servicios inyectados
    preprocessor = container.preprocessor_service()
    ml_filter = container.ml_filter_service()
    policy_engine = container.policy_service()
    orchestrator = container.orchestrator_service()
    
    # 1. Preprocess
    preprocessed = preprocessor.preprocess(payload.message)
    
    # 2. Fast ML Filter
    ml_signals = ml_filter.analyze(preprocessed.normalized_text)
    
    # 3. Policy Engine
    decision = policy_engine.evaluate(ml_signals, preprocessed.features, tenant_id)
    
    # 4. Action Orchestrator
    orchestrator.execute(decision, request_id, context)
    
    # 5. Decisión final
    if decision.blocked:
        return {"blocked": True, "reason": decision.reason}
    
    # Llamar backend si permitido
    # ... código existente ...
```

## Dependencias Nuevas

Actualizar `firewall/requirements.txt`:

- `dependency-injector` - Para DI container
- `sentence-transformers` - Para embeddings (puede cambiarse)
- `onnxruntime` - Para modelos ONNX (puede cambiarse)
- `qdrant-client` - Para Qdrant (opcional, puede ser mock)
- `structlog` - Para logging estructurado (puede cambiarse)

## Configuración

Actualizar `firewall/config.yaml`:

```yaml
# Configuración de adapters (fácil de cambiar)
vectorizer:
  model: "sentence-transformers/all-MiniLM-L6-v2"  # Cambiar modelo fácilmente

ml:
  pii_model: "models/pii_detector.onnx"  # Cambiar path/tecnología
  toxicity_model: "models/toxicity.onnx"

qdrant:
  url: "http://qdrant:6333"  # Cambiar a Pinecone fácilmente
  enabled: true

policy:
  loader: "yaml"  # Cambiar a "rego" fácilmente

logging:
  type: "structlog"  # Cambiar a "print" fácilmente
```

## Migración Gradual

1. Crear estructura de ports (interfaces ABC)
2. Crear adapters básicos (implementaciones)
3. Crear servicios core (lógica de negocio)
4. Configurar dependency injection container
5. Refactorizar `semantic_firewall.py` para usar container
6. Migrar lógica existente a nuevos módulos
7. Mantener tests de regresión

## Archivos a Crear/Modificar

**Nuevos módulos (Ports & Adapters):**

- `firewall/preprocessor/ports/*.py` (5 ports)
- `firewall/preprocessor/adapters/*.py` (5 adapters)
- `firewall/preprocessor/preprocessor_service.py`
- `firewall/fast_ml_filter/ports/*.py` (4 ports)
- `firewall/fast_ml_filter/adapters/*.py` (4 adapters)
- `firewall/fast_ml_filter/ml_filter_service.py`
- `firewall/policy_engine/ports/*.py` (3 ports)
- `firewall/policy_engine/adapters/*.py` (3 adapters)
- `firewall/policy_engine/policy_service.py`
- `firewall/action_orchestrator/ports/*.py` (4 ports)
- `firewall/action_orchestrator/adapters/*.py` (3 adapters)
- `firewall/action_orchestrator/orchestrator_service.py`
- `firewall/container.py` - Dependency injection container

**Archivos a modificar:**

- `firewall/semantic_firewall.py` - Refactorizar para usar DI
- `firewall/requirements.txt` - Agregar `dependency-injector` y otras deps
- `firewall/config.yaml` - Agregar configuraciones de adapters
- `firewall/Dockerfile` - Potencialmente actualizar

**Archivos a mantener:**

- `firewall/rules/prompt_injection_rules.yaml` - Usado por heuristic_detector adapter

## Ventajas de esta Arquitectura

1. **Cambio de Tecnología Fácil**: Cambiar Qdrant → Pinecone solo requiere nuevo adapter
2. **Testing**: Mockear ports es trivial (implementar ABC con valores fijos)
3. **Configuración**: Cambiar adapters vía config sin tocar código
4. **Extensibilidad**: Agregar nuevos adapters sin modificar core
5. **Mantenibilidad**: Separación clara de responsabilidades