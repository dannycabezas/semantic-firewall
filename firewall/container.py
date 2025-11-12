"""Dependency injection container for firewall components."""

from dependency_injector import containers, providers

# Preprocessor
from preprocessor.adapters.text_normalizer import TextNormalizer
from preprocessor.adapters.sentence_transformer_vectorizer import SentenceTransformerVectorizer
from preprocessor.adapters.basic_feature_extractor import BasicFeatureExtractor
from preprocessor.adapters.qdrant_vector_store import QdrantVectorStore
from preprocessor.adapters.memory_feature_store import MemoryFeatureStore
from preprocessor.preprocessor_service import PreprocessorService

# Fast ML Filter
from fast_ml_filter.adapters.onnx_pii_detector import ONNXPIIDetector
from fast_ml_filter.adapters.onnx_toxicity_detector import ONNXToxicityDetector
from fast_ml_filter.adapters.regex_heuristic_detector import RegexHeuristicDetector
from fast_ml_filter.ml_filter_service import MLFilterService

# Policy Engine
from policy_engine.adapters.yaml_policy_loader import YAMLPolicyLoader
from policy_engine.adapters.memory_tenant_context import MemoryTenantContext
from policy_engine.adapters.simple_policy_evaluator import SimplePolicyEvaluator
from policy_engine.policy_service import PolicyService

# Action Orchestrator
from action_orchestrator.adapters.structlog_logger import StructlogLogger
from action_orchestrator.adapters.print_logger import PrintLogger
from action_orchestrator.adapters.memory_idempotency_store import MemoryIdempotencyStore
from action_orchestrator.orchestrator_service import OrchestratorService


class FirewallContainer(containers.DeclarativeContainer):
    """Dependency injection container for firewall components."""
    
    # Configuration
    config = providers.Configuration()
    
    # Preprocessor Adapters
    normalizer = providers.Factory(TextNormalizer)
    
    vectorizer = providers.Factory(
        SentenceTransformerVectorizer,
        model_name=config.vectorizer.model
    )
    
    feature_extractor = providers.Factory(BasicFeatureExtractor)
    
    vector_store = providers.Singleton(
        QdrantVectorStore,
        url=config.qdrant.url,
        collection_name=config.qdrant.collection_name,
        enabled=config.qdrant.enabled
    )
    
    feature_store = providers.Singleton(MemoryFeatureStore)
    
    # Preprocessor Service
    preprocessor_service = providers.Factory(
        PreprocessorService,
        normalizer=normalizer,
        vectorizer=vectorizer,
        feature_extractor=feature_extractor,
        vector_store=vector_store,
        feature_store=feature_store
    )
    
    # Fast ML Filter Adapters
    def _get_pii_model_path():
        try:
            path = config.ml.pii_model()
            return path if path else None
        except Exception:
            return None
    
    def _get_toxicity_model_path():
        try:
            path = config.ml.toxicity_model()
            return path if path else None
        except Exception:
            return None
    
    def _get_rules_path():
        try:
            return config.heuristic.rules_path()
        except Exception:
            return "rules/prompt_injection_rules.yaml"
    
    pii_detector = providers.Singleton(
        ONNXPIIDetector,
        model_path=providers.Callable(_get_pii_model_path)
    )
    
    toxicity_detector = providers.Singleton(
        ONNXToxicityDetector,
        model_path=providers.Callable(_get_toxicity_model_path)
    )
    
    heuristic_detector = providers.Factory(
        RegexHeuristicDetector,
        rules_path=providers.Callable(_get_rules_path)
    )
    
    # Fast ML Filter Service
    ml_filter_service = providers.Factory(
        MLFilterService,
        pii_detector=pii_detector,
        toxicity_detector=toxicity_detector,
        heuristic_detector=heuristic_detector
    )
    
    # Policy Engine Adapters
    def _get_policies_path():
        try:
            return config.policy.policies_path()
        except Exception:
            return "policy_engine/policies.yaml"
    
    policy_loader = providers.Factory(
        YAMLPolicyLoader,
        policies_path=providers.Callable(_get_policies_path)
    )
    
    tenant_context_provider = providers.Singleton(MemoryTenantContext)
    
    policy_evaluator = providers.Factory(SimplePolicyEvaluator)
    
    # Policy Engine Service
    policy_service = providers.Factory(
        PolicyService,
        evaluator=policy_evaluator,
        loader=policy_loader,
        tenant_context_provider=tenant_context_provider
    )
    
    # Action Orchestrator Adapters
    def _create_logger():
        """Factory function to create logger based on config."""
        try:
            log_type = config.logging.type()
            if log_type == "structlog":
                return StructlogLogger()
        except Exception:
            pass
        return PrintLogger()
    
    logger = providers.Singleton(providers.Callable(_create_logger))
    
    idempotency_store = providers.Singleton(MemoryIdempotencyStore)
    
    # Action Orchestrator Service
    orchestrator_service = providers.Factory(
        OrchestratorService,
        logger=logger,
        alerter=None,  # Can be added later if needed
        idempotency_store=idempotency_store
    )
