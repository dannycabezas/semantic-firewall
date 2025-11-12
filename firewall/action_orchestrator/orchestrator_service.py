"""Action orchestrator service - core business logic."""

from typing import Dict, Any, Optional

from action_orchestrator.ports.logger_port import ILogger
from action_orchestrator.ports.alerter_port import IAlerter
from action_orchestrator.ports.idempotency_store_port import IIdempotencyStore
from policy_engine.policy_service import PolicyDecision


class OrchestratorService:
    """Service for orchestrating actions based on decisions."""

    def __init__(
        self,
        logger: ILogger,
        alerter: Optional[IAlerter] = None,
        idempotency_store: Optional[IIdempotencyStore] = None,
    ):
        """
        Initialize orchestrator service with injected dependencies.
        
        Args:
            logger: Logger implementation
            alerter: Optional alerter implementation
            idempotency_store: Optional idempotency store implementation
        """
        self.logger = logger
        self.alerter = alerter
        self.idempotency_store = idempotency_store

    def execute(
        self,
        decision: PolicyDecision,
        request_id: str,
        context: Dict[str, Any] = None
    ) -> None:
        """
        Execute actions based on decision.
        
        Args:
            decision: Policy decision
            request_id: Unique request identifier
            context: Additional context
        """
        context = context or {}
        
        # Check idempotency
        if self.idempotency_store:
            existing = self.idempotency_store.get(request_id)
            if existing:
                # Already processed, skip
                self.logger.log("debug", f"Request {request_id} already processed (idempotent)")
                return
        
        # Log decision
        log_data = {
            "request_id": request_id,
            "blocked": decision.blocked,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "matched_rule": decision.matched_rule,
            **context
        }
        
        if decision.blocked:
            self.logger.log("warning", f"Request blocked: {decision.reason}", **log_data)
            self.logger.log_structured({
                "event": "request_blocked",
                **log_data
            })
            
            # Alert if critical
            if self.alerter and decision.confidence > 0.8:
                severity = "high" if decision.confidence > 0.9 else "medium"
                self.alerter.alert(
                    severity=severity,
                    message=f"Request blocked: {decision.reason}",
                    context=log_data
                )
        else:
            self.logger.log("info", f"Request allowed", **log_data)
            self.logger.log_structured({
                "event": "request_allowed",
                **log_data
            })
        
        # Store result for idempotency
        if self.idempotency_store:
            self.idempotency_store.store(request_id, {
                "decision": decision.blocked,
                "reason": decision.reason,
                "timestamp": context.get("timestamp")
            })

