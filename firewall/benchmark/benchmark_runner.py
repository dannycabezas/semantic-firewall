"""Benchmark runner service for executing firewall benchmarks."""

import asyncio
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from benchmark.database import BenchmarkDatabase
from benchmark.dataset_loader import DatasetLoader, DatasetSample
from benchmark.metrics_calculator import MetricsCalculator
from core.orchestrator import FirewallOrchestrator
from core.request_context import RequestContext
from core.exceptions import ContentBlockedException

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Runs benchmarks against the semantic firewall."""
    
    def __init__(
        self,
        orchestrator: FirewallOrchestrator,
        database: BenchmarkDatabase
    ):
        self.orchestrator = orchestrator
        self.database = database
        self.dataset_loader = DatasetLoader()
        self.metrics_calculator = MetricsCalculator()
        
        # Track running benchmarks
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        self.cancel_flags: Dict[str, bool] = {}
    
    async def start_benchmark(
        self,
        dataset_name: str,
        dataset_split: str = "test",
        max_samples: Optional[int] = None,
        tenant_id: str = "benchmark",
        model_config: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new benchmark run.
        
        Args:
            dataset_name: HuggingFace dataset identifier
            dataset_split: Dataset split to use
            max_samples: Maximum samples to process
            tenant_id: Tenant ID for the benchmark
            
        Returns:
            Benchmark run ID
        """
        run_id = str(uuid.uuid4())
        
        logger.info(f"Starting benchmark {run_id}: {dataset_name} ({dataset_split})")
        
        # Load dataset samples
        try:
            samples = await self.dataset_loader.load_dataset_samples(
                dataset_name=dataset_name,
                split=dataset_split,
                max_samples=max_samples
            )
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
        
        if not samples:
            raise ValueError("No samples loaded from dataset")
        
        # Create benchmark run in database
        config_snapshot = {
            "dataset_name": dataset_name,
            "dataset_split": dataset_split,
            "max_samples": max_samples,
            "tenant_id": tenant_id,
            "model_config": model_config,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.database.create_run(
            run_id=run_id,
            dataset_name=dataset_name,
            dataset_source="huggingface",
            dataset_split=dataset_split,
            config_snapshot=config_snapshot,
            total_samples=len(samples)
        )
        
        # Initialize tracking
        self.active_runs[run_id] = {
            "status": "running",
            "total_samples": len(samples),
            "processed_samples": 0,
            "start_time": time.time(),
            "model_config": model_config
        }
        self.cancel_flags[run_id] = False
        
        # Run benchmark in background
        asyncio.create_task(self._execute_benchmark(run_id, samples, tenant_id, model_config))
        
        return run_id
    
    async def _execute_benchmark(
        self,
        run_id: str,
        samples: list[DatasetSample],
        tenant_id: str,
        model_config: Optional[Dict[str, str]] = None
    ):
        """Execute the benchmark processing."""
        # Create orchestrator with model config if provided
        if model_config:
            from container import FirewallContainer
            from core.analyzer import FirewallAnalyzer
            from core.backend_proxy import BackendProxyService
            import os
            
            container = FirewallContainer()
            BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
            TENANT_ID = os.getenv("TENANT_ID", "default")
            
            # Create ML filter service with specified models
            from fast_ml_filter.ml_filter_service import MLFilterService
            ml_filter = MLFilterService.create_with_models(model_config=model_config)
            
            analyzer = FirewallAnalyzer(
                preprocessor=container.preprocessor_service(),
                ml_filter=ml_filter,
                policy_engine=container.policy_service(),
                tenant_id=TENANT_ID,
            )
            
            proxy = BackendProxyService(backend_url=BACKEND_URL, timeout=30.0)
            orchestrator_service = container.orchestrator_service()
            
            benchmark_orchestrator = FirewallOrchestrator(
                analyzer=analyzer,
                proxy=proxy,
                orchestrator=orchestrator_service,
            )
        else:
            benchmark_orchestrator = self.orchestrator
        
        results = []
        
        try:
            for sample in samples:
                # Check for cancellation
                if self.cancel_flags.get(run_id, False):
                    logger.info(f"Benchmark {run_id} cancelled")
                    await self.database.update_run_status(run_id, "cancelled")
                    break
                
                # Process sample through firewall
                result = await self._process_sample(run_id, sample, tenant_id, benchmark_orchestrator)
                results.append(result)
                
                # Update progress
                self.active_runs[run_id]["processed_samples"] += 1
                await self.database.increment_processed_samples(run_id)
            
            # If not cancelled, calculate and save final metrics
            if not self.cancel_flags.get(run_id, False):
                metrics = self.metrics_calculator.calculate_metrics(results)
                await self.database.save_metrics(run_id, metrics)
                await self.database.update_run_status(run_id, "completed")
                self.active_runs[run_id]["status"] = "completed"
                logger.info(f"Benchmark {run_id} completed. F1-Score: {metrics['f1_score']:.4f}")
            
        except Exception as e:
            logger.error(f"Benchmark {run_id} failed: {e}", exc_info=True)
            await self.database.update_run_status(run_id, "failed", str(e))
            self.active_runs[run_id]["status"] = "failed"
        
        finally:
            # Cleanup
            if run_id in self.cancel_flags:
                del self.cancel_flags[run_id]
    
    async def _process_sample(
        self,
        run_id: str,
        sample: DatasetSample,
        tenant_id: str,
        orchestrator: Optional[FirewallOrchestrator] = None
    ) -> Dict[str, Any]:
        """Process a single sample through the firewall."""
        start_time = time.time()
        
        # Create request context
        request_context = RequestContext(
            request_id=f"benchmark-{run_id}-{sample.index}",
            user_id=f"benchmark-user-{run_id}",
            session_id=f"benchmark-session-{run_id}",
            tenant_id=tenant_id,
            device="benchmark",
            temperature=0.5,
            max_tokens=20,
            turn_count=1,
            rate_limit_remaining=0,
            custom={"benchmark_run": run_id, "sample_index": sample.index}
        )
        
        try:
            # Use provided orchestrator or fallback to default
            current_orchestrator = orchestrator or self.orchestrator
            
            # Run through firewall orchestrator
            result = await current_orchestrator.process_chat_request(
                message=sample.prompt,
                request_id=f"benchmark-{run_id}-{sample.index}",
                analyze_egress=False,
                context=request_context,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract metrics from result dictionary
            metrics = result.get("metrics", {})
            decision = metrics.get("decision")
            ml_signals = metrics.get("ml_signals")
            
            # Determine result type
            blocked = decision.blocked if decision else False
            result_type = self.metrics_calculator.calculate_result_type(
                expected_label=sample.expected_label,
                predicted_blocked=blocked
            )
            
            # Build analysis details from orchestrator result
            analysis_details = {
                "blocked": blocked,
                "reason": decision.reason if decision else None,
                "ml_signals": {
                    "prompt_injection_score": ml_signals.prompt_injection_score if ml_signals else 0.0,
                    "toxicity_score": ml_signals.toxicity_score if ml_signals else 0.0,
                    "pii_score": ml_signals.pii_score if ml_signals else 0.0,
                    "heuristic_blocked": ml_signals.heuristic_blocked if ml_signals else False
                } if ml_signals else None,
                "policy_decision": {
                "blocked": decision.blocked if decision else False,
                "reason": decision.reason if decision else None,
                "confidence": decision.confidence if decision else 0.0,
                "matched_rule": decision.matched_rule if decision else None,
                } if decision else None,
                "latency_ms": latency_ms
            }
            
            # Save to database
            await self.database.save_result(
                run_id=run_id,
                sample_index=sample.index,
                input_text=sample.prompt,
                expected_label=sample.expected_label,
                predicted_label="blocked" if blocked else "allowed",
                is_correct=(result_type in ["TRUE_POSITIVE", "TRUE_NEGATIVE"]),
                result_type=result_type,
                analysis_details=analysis_details,
                latency_ms=latency_ms
            )
            
            return {
                "result_type": result_type,
                "latency_ms": latency_ms,
                "expected_label": sample.expected_label,
                "predicted_label": "blocked" if blocked else "allowed"
            }
        
        except ContentBlockedException as e:
            # Content was blocked - this is a valid result, not an error
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Sample {sample.index} blocked: {e.reason}")
            
            # Determine result type (blocked = True)
            result_type = self.metrics_calculator.calculate_result_type(
                expected_label=sample.expected_label,
                predicted_blocked=True
            )
            
            # Build analysis details from exception
            analysis_details = {
                "blocked": True,
                "reason": e.reason,
                "direction": e.direction,
                "ml_signals": {
                    "prompt_injection_score": e.ml_signals.prompt_injection_score if e.ml_signals else 0.0,
                    "toxicity_score": e.ml_signals.toxicity_score if e.ml_signals else 0.0,
                    "pii_score": e.ml_signals.pii_score if e.ml_signals else 0.0,
                    "heuristic_blocked": e.ml_signals.heuristic_blocked if e.ml_signals else False
                } if e.ml_signals else None,
                "policy_decision": e.details,
                "latency_ms": latency_ms
            }
            
            # Save to database
            await self.database.save_result(
                run_id=run_id,
                sample_index=sample.index,
                input_text=sample.prompt,
                expected_label=sample.expected_label,
                predicted_label="blocked",
                is_correct=(result_type in ["TRUE_POSITIVE", "TRUE_NEGATIVE"]),
                result_type=result_type,
                analysis_details=analysis_details,
                latency_ms=latency_ms
            )
            
            return {
                "result_type": result_type,
                "latency_ms": latency_ms,
                "expected_label": sample.expected_label,
                "predicted_label": "blocked"
            }
            
        except Exception as e:
            # Unexpected error during processing
            logger.error(f"Error processing sample {sample.index}: {e}")
            
            # Save error result
            latency_ms = (time.time() - start_time) * 1000
            analysis_details = {"error": str(e)}
            
            await self.database.save_result(
                run_id=run_id,
                sample_index=sample.index,
                input_text=sample.prompt,
                expected_label=sample.expected_label,
                predicted_label="error",
                is_correct=False,
                result_type="ERROR",
                analysis_details=analysis_details,
                latency_ms=latency_ms
            )
            
            return {
                "result_type": "ERROR",
                "latency_ms": latency_ms,
                "expected_label": sample.expected_label,
                "predicted_label": "error"
            }
    
    async def cancel_benchmark(self, run_id: str) -> bool:
        """Cancel a running benchmark."""
        if run_id in self.active_runs and self.active_runs[run_id]["status"] == "running":
            logger.info(f"Cancelling benchmark {run_id}")
            self.cancel_flags[run_id] = True
            return True
        return False
    
    def get_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a benchmark run."""
        if run_id in self.active_runs:
            run_info = self.active_runs[run_id]
            elapsed_time = time.time() - run_info["start_time"]
            
            processed = run_info["processed_samples"]
            total = run_info["total_samples"]
            
            # Estimate remaining time
            if processed > 0:
                avg_time_per_sample = elapsed_time / processed
                remaining_samples = total - processed
                estimated_remaining = avg_time_per_sample * remaining_samples
            else:
                estimated_remaining = None
            
            return {
                "run_id": run_id,
                "status": run_info["status"],
                "total_samples": total,
                "processed_samples": processed,
                "progress_percent": (processed / total * 100) if total > 0 else 0,
                "elapsed_time_seconds": elapsed_time,
                "estimated_remaining_seconds": estimated_remaining
            }
        return None

