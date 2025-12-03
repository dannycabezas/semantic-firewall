import os
from typing import Optional

from container import FirewallContainer
from core.analyzer import FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.orchestrator import FirewallOrchestrator
from fast_ml_filter.ml_filter_service import MLFilterService


_BACKEND_URL_DEFAULT = "http://backend:8000"
_TENANT_ID_DEFAULT = "default"


# Shared container to build the components of the gateway/firewall
_container = FirewallContainer()


def _get_backend_url() -> str:
    return os.getenv("BACKEND_URL", _BACKEND_URL_DEFAULT)


def _get_tenant_id() -> str:
    return os.getenv("TENANT_ID", _TENANT_ID_DEFAULT)


def create_gateway_orchestrator(
    model_config: Optional[dict] = None,
    backend_url: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> FirewallOrchestrator:
    """
    Create a configured `FirewallOrchestrator` instance.

    Args:
        model_config: Optional model configuration:
            {
                "prompt_injection": "custom_onnx" | "deberta",
                "pii": "presidio" | "onnx" | "mock",
                "toxicity": "detoxify" | "onnx"
            }
        backend_url: Backend URL; if None, taken from env `BACKEND_URL`.
        tenant_id: Tenant ID; if None, taken from env `TENANT_ID`.
    """
    backend_url = backend_url or _get_backend_url()
    tenant_id = tenant_id or _get_tenant_id()

    # Create ML filter service with the specified models or using the ones from the container
    if model_config:
        ml_filter = MLFilterService.create_with_models(model_config=model_config)
    else:
        ml_filter = _container.ml_filter_service()

    analyzer = FirewallAnalyzer(
        preprocessor=_container.preprocessor_service(),
        ml_filter=ml_filter,
        policy_engine=_container.policy_service(),
        tenant_id=tenant_id,
    )

    proxy = BackendProxyService(backend_url=backend_url, timeout=30.0)

    orchestrator = _container.orchestrator_service()

    return FirewallOrchestrator(
        analyzer=analyzer,
        proxy=proxy,
        orchestrator=orchestrator,
    )


def get_default_gateway() -> FirewallOrchestrator:
    """
    Get a `FirewallOrchestrator` using default configuration
    (environment variables and the global container).
    """
    return create_gateway_orchestrator()


