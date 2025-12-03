import logging
import time
from typing import Any

from action_orchestrator.orchestrator_service import OrchestratorService
from core.analyzer import AnalysisDirection, AnalysisResult, FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.exceptions import BackendError, ContentBlockedException
from core.request_context import RequestContext
from core.utils.decorators import log_execution_time

logger = logging.getLogger(__name__)


class FirewallOrchestrator:
    """
    Orchestrator principal of the firewall.

    Responsibility: Coordinate the complete flow of ingress/egress analysis
    and communication with the backend.

    Applied principles:
    - SRP: Only coordinates, does not analyze or process
    - OCP: Open to extension (add new analyzers)
    - DIP: Depends on abstractions (dependency injection)
    """

    def __init__(
        self,
        analyzer: FirewallAnalyzer,
        proxy: BackendProxyService,
        orchestrator: OrchestratorService,
    ) -> None:
        """
        Initialize the orchestrator with the dependencies.

        Args:
            analyzer: Content analyzer of the firewall
            proxy: Proxy service to the backend
            orchestrator: Orchestrator of actions
        """
        self._analyzer = analyzer
        self._proxy = proxy
        self._orchestrator = orchestrator

    @log_execution_time()
    async def process_chat_request(
        self,
        message: str,
        request_id: str,
        analyze_egress: bool = True,
        context: RequestContext | None = None,
    ) -> dict[str, Any]:
        """
        Processes a complete chat request: ingress + backend + egress.

        Args:
            message: User message
            request_id: Unique request ID
            analyze_egress: If it should analyze the backend response
            context: Request context
        Returns:
            Backend response or block message con métricas

        Raises:
            ContentBlockedException: If the content is blocked
            BackendError: If there is an error in the backend
        """
        start_time = time.time()
        analysis_result = None

        try:
            # === INGRESS ANALYSIS ===
            analysis_result = await self._analyze_with_orchestration(
                content=message,
                direction=AnalysisDirection.INGRESS,
                request_id=request_id,
                context=context,
            )

            # === PROXY TO BACKEND ===
            backend_start = time.time()
            backend_response = await self._proxy_with_error_handling(
                message=message,
                request_id=request_id,
            )
            backend_latency_ms = (time.time() - backend_start) * 1000

            # === EGRESS ANALYSIS (OPTIONAL) ===
            if analyze_egress:
                reply = backend_response.get("reply", "")
                if reply:
                    await self._analyze_with_orchestration(
                        content=reply,
                        direction=AnalysisDirection.EGRESS,
                        request_id=f"{request_id}_egress",
                        context=context,
                    )

            # === SUCCESS LOG ===
            total_latency_ms = (time.time() - start_time) * 1000
            self._orchestrator.logger.log(
                "info",
                f"Request allowed - latency: {total_latency_ms:.1f}ms",
                request_id=request_id,
                latency_ms=total_latency_ms,
            )

            # Add metrics to the response
            backend_response["metrics"] = {
                "ml_signals": analysis_result.ml_signals if analysis_result else None,
                "preprocessed": analysis_result.preprocessed if analysis_result else None,
                "decision": analysis_result.decision if analysis_result else None,
                "analysis_latency_ms": analysis_result.latency_ms if analysis_result else 0,
                "preprocessing_latency_ms": 0,  # Could be extracted if needed
                "policy_latency_ms": 0,  # Could be extracted if needed
            }
            backend_response["backend_latency_ms"] = backend_latency_ms
            
            return backend_response

        except ContentBlockedException as e:
            # Already orchestrated in _analyze_with_orchestration
            logger.info(f"Content blocked ({e.direction}): {e.reason}")
            # Attach ml_signals and preprocessed to the exception if available
            if analysis_result:
                e.ml_signals = analysis_result.ml_signals
                e.preprocessed = analysis_result.preprocessed
            raise

        except BackendError as e:
            # Orchestrate backend error
            self._orchestrator.logger.log(
                "error",
                f"Backend error: {e.message}",
                request_id=request_id,
                **e.details,
            )
            raise

        except Exception as e:
            # Unexpected error
            self._orchestrator.logger.log(
                "error",
                f"Unexpected error in the firewall: {e}",
                request_id=request_id,
                error=str(e),
            )
            raise

    
    @log_execution_time()
    async def _analyze_with_orchestration(
        self,
        content: str,
        direction: AnalysisDirection,
        request_id: str,
        context: RequestContext | None = None,
    ) -> AnalysisResult:
        """
        Analyzes content and orchestrates the corresponding actions.

        Args:
            content: Content to analyze
            direction: Analysis direction
            request_id: Request ID
            context: Request context
        Returns:
            AnalysisResult if the content is allowed

        Raises:
            ContentBlockedException: If the content is blocked
        """
        try:
            result = await self._analyzer.analyze_content(
                content=content,
                direction=direction,
                store=False,
                context=context,
            )

            # Orchestrate decision to allow
            self._orchestrator.execute(
                decision=result.decision,
                request_id=request_id,
                context={
                    "timestamp": time.time(),
                    "direction": direction.value,
                    "message_length": len(content),
                    "latency_ms": result.latency_ms,
                },
            )

            return result

        except ContentBlockedException as e:
            # Orchestrate decision to block
            from policy_engine.policy_service import PolicyDecision

            blocked_decision = PolicyDecision(
                blocked=True,
                reason=e.reason,
                confidence=e.details.get("confidence", 1.0),
                matched_rule=e.details.get("matched_rule"),
            )

            self._orchestrator.execute(
                decision=blocked_decision,
                request_id=request_id,
                context={
                    "timestamp": time.time(),
                    "direction": e.direction,
                    "latency_ms": e.details.get("latency_ms", 0),
                },
            )

            raise

    @log_execution_time()
    async def _proxy_with_error_handling(
        self,
        message: str,
        request_id: str,
    ) -> dict[str, Any]:
        """
        Sends a message to the backend with error handling.

        Args:
            message: Message to send
            request_id: Request ID

        Returns:
            Backend response

        Raises:
            BackendError: If there is an error in the backend
        """
        try:
            return await self._proxy.send_chat_message(message)
        except BackendError:
            raise
