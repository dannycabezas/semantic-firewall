"""Dependency injection container for firewall components."""

from dependency_injector import containers, providers

from action_orchestrator.adapters.memory_idempotency_store import MemoryIdempotencyStore
from action_orchestrator.adapters.print_logger import PrintLogger

# Action Orchestrator
from action_orchestrator.adapters.structlog_logger import StructlogLogger
from action_orchestrator.orchestrator_service import OrchestratorService
from config import FirewallConfig

# Fast ML Filter
from fast_ml_filter.adapters.onnx_pii_detector import ONNXPIIDetector
from fast_ml_filter.adapters.onnx_toxicity_detector import ONNXToxicityDetector
from fast_ml_filter.adapters.presidio_pii_detector import PresidioPIIDetector
from fast_ml_filter.adapters.regex_heuristic_detector import RegexHeuristicDetector
from fast_ml_filter.ml_filter_service import MLFilterService
from fast_ml_filter.adapters.deberta_prompt_injection_detector import DeBERTaPromptInjectionDetector
from policy_engine.adapters.memory_tenant_context import MemoryTenantContext
from policy_engine.adapters.opa_evaluator import OPAEvaluator

# Policy Engine
from policy_engine.adapters.rego_policy_loader import RegoPolicyLoader
from policy_engine.policy_service import PolicyService
from preprocessor.adapters.basic_feature_extractor import BasicFeatureExtractor
from preprocessor.adapters.memory_feature_store import MemoryFeatureStore
from preprocessor.adapters.qdrant_vector_store import QdrantVectorStore
from preprocessor.adapters.sentence_transformer_vectorizer import SentenceTransformerVectorizer

# Preprocessor
from preprocessor.adapters.text_normalizer import TextNormalizer
from preprocessor.preprocessor_service import PreprocessorService


class FirewallContainer(containers.DeclarativeContainer):
    """Dependency injection container for firewall components."""

    # Configuration
    config = providers.Singleton(FirewallConfig)

    # Preprocessor Adapters
    normalizer = providers.Factory(TextNormalizer)

    vectorizer = providers.Factory(SentenceTransformerVectorizer, model_name=config.provided.vectorizer.model)

    feature_extractor = providers.Factory(BasicFeatureExtractor)

    vector_store = providers.Singleton(
        QdrantVectorStore,
        url=config.provided.qdrant.url,
        collection_name=config.provided.qdrant.collection_name,
        enabled=config.provided.qdrant.enabled,
    )

    feature_store = providers.Singleton(MemoryFeatureStore)

    # Preprocessor Service
    preprocessor_service = providers.Factory(
        PreprocessorService,
        normalizer=normalizer,
        vectorizer=vectorizer,
        feature_extractor=feature_extractor,
        vector_store=vector_store,
        feature_store=feature_store,
    )

    pii_detector = providers.Singleton(
        PresidioPIIDetector,
        # model_path=config.provided.ml.pii_model
    )

    toxicity_detector = providers.Singleton(ONNXToxicityDetector, model_path=config.provided.ml.toxicity_model)

    prompt_injection_detector = providers.Singleton(DeBERTaPromptInjectionDetector, model_name=config.provided.ml.prompt_injection_model)

    heuristic_detector = providers.Factory(RegexHeuristicDetector, rules_path=config.provided.heuristic.rules_path)

    # Fast ML Filter Service
    ml_filter_service = providers.Factory(
        MLFilterService,
        pii_detector=pii_detector,
        toxicity_detector=toxicity_detector,
        prompt_injection_detector=prompt_injection_detector,
        heuristic_detector=heuristic_detector,
    )

    # Policy Engine Adapters
    policy_loader = providers.Factory(RegoPolicyLoader, policies_path=config.provided.policy.policies_path)

    tenant_context_provider = providers.Singleton(MemoryTenantContext)

    policy_evaluator = providers.Factory(
        OPAEvaluator,
        opa_url=config.provided.policy.opa_url,
        opa_policy_name=config.provided.policy.opa_policy_name,
    )

    # Policy Engine Service
    policy_service = providers.Factory(
        PolicyService, evaluator=policy_evaluator, loader=policy_loader, tenant_context_provider=tenant_context_provider
    )

    # Action Orchestrator Adapters
    logger = providers.Singleton(PrintLogger)
    idempotency_store = providers.Singleton(MemoryIdempotencyStore)

    # Action Orchestrator Service
    orchestrator_service = providers.Factory(
        OrchestratorService,
        logger=logger,
        alerter=None,  # Can be added later if needed
        idempotency_store=idempotency_store,
    )
