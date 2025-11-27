import asyncio
import logging

from fastapi import FastAPI

from core.realtime import init_event_queue, event_broadcaster
from core.benchmarks import benchmark_service


logger = logging.getLogger(__name__)


def register_startup_events(app: FastAPI) -> None:
    """
    Register startup/shutdown handlers in the FastAPI app.

    Centralize the initialization of infrastructure services
    (realtime, benchmarks, etc.) to keep the endpoint modules
    cleaner.
    """

    @app.on_event("startup")
    async def _on_startup() -> None:  # pragma: no cover - framework hook
        # Initialize event queue and broadcast launcher
        await init_event_queue()
        asyncio.create_task(event_broadcaster())

        # Initialize benchmark system (DB + runner)
        await benchmark_service.initialize()

        logger.info("Startup hooks initialized (realtime + benchmarks)")
        
        # Warm-up of the ML models
        logger.info("Starting ML models warm-up...")
        await _warmup_ml_models()
        logger.info("ML models warm-up completed")


async def _warmup_ml_models() -> None:
    """
    Warm-up of the ML models to avoid latency in the first request.
    
    Warm up both the container (default) and the factory models
    to cover normal requests and benchmarks.
    """
    try:
        logger.info("Warming up default container models...")
        
        # 1. Warm-up the container models (default gateway)
        from core.gateway.factory import _container
        
        warmup_text = "This is a warmup text to load all ML models."
        
        # The detectors are Singleton, they are loaded once
        logger.info("  → Warming up PII detector (container)...")
        pii_det = _container.pii_detector()
        _ = pii_det.detect(warmup_text)
        
        logger.info("  → Warming up Toxicity detector (container)...")
        tox_det = _container.toxicity_detector()
        _ = tox_det.detect(warmup_text)
        
        logger.info("  → Warming up Prompt Injection detector (container)...")
        pi_det = _container.prompt_injection_detector()
        _ = pi_det.detect(warmup_text, context=None)
        
        # 2. Warm-up the alternative models from the factory (for benchmarks)
        logger.info("Warming up factory models (for benchmarks)...")
        from fast_ml_filter.detector_factory import DetectorFactory
        
        factory = DetectorFactory()
        
        # Pre-load common models used in benchmarks
        # (only if they are different from the container)
        try:
            logger.info("  → Pre-loading Presidio PII...")
            presidio = factory.create_pii_detector("presidio")
            _ = presidio.detect(warmup_text)
        except Exception as e:
            logger.warning(f"    Presidio warm-up failed: {e}")
        
        try:
            logger.info("  → Pre-loading Detoxify...")
            detoxify = factory.create_toxicity_detector("detoxify")
            _ = detoxify.detect(warmup_text)
        except Exception as e:
            logger.warning(f"    Detoxify warm-up failed: {e}")
        
        try:
            logger.info("  → Pre-loading Llama Guard 86M...")
            llama = factory.create_prompt_injection_detector("llama_guard_22m")
            _ = llama.detect(warmup_text, context=None)
        except Exception as e:
            logger.warning(f"    Llama Guard warm-up failed: {e}")
        
        logger.info("✅ All models warmed up successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ ML models warm-up failed (non-critical): {e}")
    """
    Warm-up of the ML models to avoid latency in the first request.
    
    This function loads all ML models by executing dummy inferences
    before the server starts receiving real requests.
    """
    try:
        # Import the container to access the ml_filter_service
        from core.gateway.factory import _container
        
        # Get the ml_filter_service from the container
        ml_filter = _container.ml_filter_service()
        
        # Dummy text for warm-up (short to be fast)
        warmup_text = "This is a warmup text to load all ML models."
        
        logger.info("  → Warming up PII detector...")
        _ = ml_filter.pii_detector.detect(warmup_text)
        
        logger.info("  → Warming up Toxicity detector...")
        _ = ml_filter.toxicity_detector.detect(warmup_text)
        
        logger.info("  → Warming up Prompt Injection detector...")
        _ = ml_filter.prompt_injection_detector.detect(warmup_text, context=None)
        
        logger.info("  → Warming up Heuristic detector...")
        _ = ml_filter.heuristic_detector.detect(warmup_text)
        
        logger.info("  ✓ All ML models loaded successfully")
        
    except Exception as e:
        logger.warning(f"ML models warm-up failed (non-critical): {e}")
        # Do not interrupt the startup if the warm-up fails