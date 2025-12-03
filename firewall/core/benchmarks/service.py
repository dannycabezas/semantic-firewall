from __future__ import annotations

import json
import logging
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List

from benchmark.database import BenchmarkDatabase
from benchmark.benchmark_runner import BenchmarkRunner
from benchmark.minio_storage import MinioDatasetStorage
from core.gateway import get_default_gateway, create_gateway_orchestrator


logger = logging.getLogger(__name__)


class SampleChangeType(Enum):
    """Classification of how a sample's result changed between runs."""

    # Regressions (🔴)
    REGRESSION_TP_TO_FN = "regression_tp_to_fn"  # Before: correctly blocked → Now: allowed
    REGRESSION_TN_TO_FP = "regression_tn_to_fp"  # Before: correctly allowed → Now: blocked

    # Improvements (🟢)
    IMPROVEMENT_FN_TO_TP = "improvement_fn_to_tp"  # Before: missed attack → Now: detected
    IMPROVEMENT_FP_TO_TN = "improvement_fp_to_tn"  # Before: false positive → Now: correct allow

    # No meaningful change
    UNCHANGED = "unchanged"


class BenchmarkService:
    """High-level service to manage firewall benchmarks."""

    def __init__(self, db_path: str = "benchmarks.db") -> None:
        self._database = BenchmarkDatabase(db_path)
        # The runner is initialized in `initialize` because it needs the DB initialized
        self._runner: Optional[BenchmarkRunner] = None
        self._db_path = db_path
        self._storage = MinioDatasetStorage()

    @property
    def database(self) -> BenchmarkDatabase:
        return self._database

    @property
    def runner(self) -> Optional[BenchmarkRunner]:
        return self._runner

    async def initialize(self) -> None:
        """Initialize database and runner."""
        try:
            await self._database.initialize()
            firewall = get_default_gateway()
            self._runner = BenchmarkRunner(firewall, self._database)
            logger.info(
                "BenchmarkService initialized with database at %s", self._db_path
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to initialize BenchmarkService: %s", exc)
            self._runner = None

    async def start_benchmark(
        self,
        dataset_name: Optional[str],
        dataset_split: str = "test",
        max_samples: Optional[int] = None,
        tenant_id: str = "benchmark",
        detector_config: Optional[Dict[str, str]] = None,
        custom_dataset_id: Optional[str] = None,
    ) -> str:
        if not self._runner:
            raise RuntimeError("Benchmark system not initialized")

        if not dataset_name and not custom_dataset_id:
            raise ValueError("Either dataset_name or custom_dataset_id must be provided")

        run_id = await self._runner.start_benchmark(
            dataset_name=dataset_name,
            dataset_split=dataset_split,
            max_samples=max_samples,
            tenant_id=tenant_id,
            model_config=detector_config,
            custom_dataset_id=custom_dataset_id,
        )
        return run_id

    # ------------------------------------------------------------------
    # Custom datasets management
    # ------------------------------------------------------------------

    async def register_custom_dataset(
        self,
        name: str,
        description: Optional[str],
        file_content: bytes,
        file_type: str,
        total_samples: int,
    ) -> tuple[str, str]:
        """
        Register a new custom dataset:
        - Upload file to MinIO
        - Save metadata in the database

        Returns (dataset_id, created_at).
        """
        dataset_id = str(uuid.uuid4())
        file_ext = "csv" if file_type == "text/csv" else "json"
        file_key = f"datasets/{dataset_id}.{file_ext}"

        from io import BytesIO

        # Upload to MinIO
        self._storage.upload_dataset(
            file_key=file_key,
            file_obj=BytesIO(file_content),
            length=len(file_content),
            content_type=file_type,
        )

        # Save metadata
        await self._database.save_dataset_metadata(
            dataset_id=dataset_id,
            name=name,
            description=description,
            file_key=file_key,
            file_type=file_type,
            total_samples=total_samples,
        )

        meta = await self._database.get_dataset_metadata(dataset_id)
        created_at = meta["created_at"] if meta else ""
        return dataset_id, created_at

    async def list_custom_datasets(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Dict[str, Any]]:
        """List available custom datasets (for the API)."""
        datasets = await self._database.list_datasets(limit=limit, offset=offset)
        return [
            {
                "id": d["id"],
                "name": d["name"],
                "description": d.get("description"),
                "file_type": d["file_type"],
                "total_samples": d["total_samples"],
                "created_at": d["created_at"],
            }
            for d in datasets
        ]

    async def delete_custom_dataset(self, dataset_id: str) -> None:
        """
        Delete a custom dataset:
        - Delete the file from MinIO if it exists
        - Delete the metadata from the database

        Does not affect benchmarks that already used that dataset.
        """
        meta = await self._database.get_dataset_metadata(dataset_id)
        if not meta:
            raise KeyError("Dataset not found")

        file_key = meta["file_key"]
        if self._storage.dataset_exists(file_key):
            self._storage.delete_dataset(file_key)

        await self._database.delete_dataset_metadata(dataset_id)

    async def get_status(self, run_id: str) -> Dict[str, Any]:
        if not self._runner:
            raise RuntimeError("Benchmark system not initialized")

        status_info = self._runner.get_status(run_id)
        if not status_info:
            # Check DB for completed/failed runs
            run_info = await self._database.get_run(run_id)
            if not run_info:
                raise KeyError("Benchmark run not found")

            config_snapshot: Dict[str, Any] = {}
            if run_info.get("config_snapshot"):
                try:
                    config_snapshot = json.loads(run_info["config_snapshot"])
                except Exception:
                    config_snapshot = {}

            return {
                "run_id": run_id,
                "status": run_info["status"],
                "total_samples": run_info["total_samples"],
                "processed_samples": run_info["processed_samples"],
                "progress_percent": (
                    run_info["processed_samples"] / run_info["total_samples"] * 100
                    if run_info["total_samples"] > 0
                    else 0
                ),
                "detector_config": config_snapshot.get("detector_config"),
            }

        # add detector_config from DB if available
        run_info = await self._database.get_run(run_id)
        if run_info and run_info.get("config_snapshot"):
            try:
                config_snapshot = json.loads(run_info["config_snapshot"])
                status_info["detector_config"] = config_snapshot.get("detector_config")
            except Exception:
                pass

        return status_info

    async def cancel_benchmark(self, run_id: str) -> bool:
        if not self._runner:
            raise RuntimeError("Benchmark system not initialized")
        return await self._runner.cancel_benchmark(run_id)

    async def get_runs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        if not self._database:
            raise RuntimeError("Benchmark system not initialized")
        return await self._database.get_all_runs(limit=limit, offset=offset)

    async def get_results(
        self,
        run_id: str,
        result_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if not self._database:
            raise RuntimeError("Benchmark system not initialized")
        return await self._database.get_results(
            run_id=run_id, result_type=result_type, limit=limit, offset=offset
        )

    async def get_metrics(self, run_id: str) -> Dict[str, Any]:
        if not self._database:
            raise RuntimeError("Benchmark system not initialized")

        metrics = await self._database.get_metrics(run_id)
        if not metrics:
            raise KeyError(
                "Metrics not found for this run (may still be processing)"
            )

        # Add detector_config from run info
        run_info = await self._database.get_run(run_id)
        if run_info and run_info.get("config_snapshot"):
            try:
                config_snapshot = json.loads(run_info["config_snapshot"])
                metrics["detector_config"] = config_snapshot.get("detector_config")
            except Exception:
                pass

        return metrics

    async def get_error_analysis(self, run_id: str) -> Dict[str, Any]:
        if not self._database:
            raise RuntimeError("Benchmark system not initialized")
        return await self._database.get_error_analysis(run_id)

    # ------------------------------------------------------------------
    # Comparison API
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_sample_change(
        baseline_result_type: str,
        candidate_result_type: str,
    ) -> SampleChangeType:
        """Classify how a single sample changed between baseline and candidate."""
        transitions: Dict[tuple[str, str], SampleChangeType] = {
            ("TRUE_POSITIVE", "FALSE_NEGATIVE"): SampleChangeType.REGRESSION_TP_TO_FN,
            ("TRUE_NEGATIVE", "FALSE_POSITIVE"): SampleChangeType.REGRESSION_TN_TO_FP,
            ("FALSE_NEGATIVE", "TRUE_POSITIVE"): SampleChangeType.IMPROVEMENT_FN_TO_TP,
            ("FALSE_POSITIVE", "TRUE_NEGATIVE"): SampleChangeType.IMPROVEMENT_FP_TO_TN,
        }
        return transitions.get(
            (baseline_result_type, candidate_result_type), SampleChangeType.UNCHANGED
        )

    @staticmethod
    def _compute_delta(
        baseline_value: Optional[float],
        candidate_value: Optional[float],
        *,
        positive_when_increases: bool,
    ) -> Dict[str, Any]:
        """
        Compute absolute/relative delta and polarity for a metric.

        Args:
            baseline_value: Metric value for baseline.
            candidate_value: Metric value for candidate.
            positive_when_increases: If True, Δ>0 is positive (e.g. F1).
                                     If False, Δ>0 is negative (e.g. latency).
        """
        if baseline_value is None or candidate_value is None:
            return {
                "value": None,
                "percent": None,
                "polarity": "neutral",
            }

        delta = candidate_value - baseline_value
        percent = (delta / baseline_value * 100.0) if baseline_value != 0 else None

        if delta == 0 or percent is None:
            polarity = "neutral"
        else:
            is_positive_delta = delta > 0
            # If metric is better when it increases, Δ>0 is positive.
            # If metric is better when it decreases (latency/errors), Δ>0 is negative.
            if positive_when_increases:
                polarity = "positive" if is_positive_delta else "negative"
            else:
                polarity = "negative" if is_positive_delta else "positive"

        return {
            "value": round(delta, 4) if isinstance(delta, float) else delta,
            "percent": round(percent, 2) if isinstance(percent, float) and percent is not None else percent,
            "polarity": polarity,
        }

    async def compare_benchmarks(
        self,
        baseline_run_id: str,
        candidate_run_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare a baseline benchmark run against one or more candidate runs.

        Guardrails:
        - All runs must exist
        - All runs must be completed
        - All runs must share the same dataset_name and dataset_split

        Raises:
            ValueError: For invalid input (missing candidates, mismatched datasets,
                        runs not completed).
            KeyError: If any run is not found.
        """
        if not candidate_run_ids:
            raise ValueError("At least one candidate_run_id is required for comparison")

        # Ensure uniqueness and avoid comparing baseline against itself
        candidate_run_ids = [
            run_id for run_id in candidate_run_ids if run_id and run_id != baseline_run_id
        ]
        if not candidate_run_ids:
            raise ValueError(
                "No valid candidate_run_ids provided (they may all match the baseline_run_id)"
            )

        all_run_ids = [baseline_run_id] + candidate_run_ids

        # ------------------------------------------------------------------
        # 1. Load run metadata and enforce guardrails
        # ------------------------------------------------------------------
        runs_info: Dict[str, Dict[str, Any]] = {}
        for run_id in all_run_ids:
            run_info = await self._database.get_run(run_id)
            if not run_info:
                raise KeyError(f"Benchmark run not found: {run_id}")
            runs_info[run_id] = run_info

        # All runs must be completed
        incomplete = [
            run_id for run_id, info in runs_info.items() if info.get("status") != "completed"
        ]
        if incomplete:
            raise ValueError(
                "All benchmarks must be completed before comparison. "
                f"Non-completed runs: {', '.join(incomplete)}"
            )

        # All runs must share same dataset_name and dataset_split
        baseline_info = runs_info[baseline_run_id]
        baseline_dataset_name = baseline_info.get("dataset_name")
        baseline_dataset_split = baseline_info.get("dataset_split")

        mismatched = [
            run_id
            for run_id, info in runs_info.items()
            if info.get("dataset_name") != baseline_dataset_name
            or info.get("dataset_split") != baseline_dataset_split
        ]
        if mismatched:
            raise ValueError(
                "Cannot compare benchmarks from different datasets or splits. "
                "All runs must share the same dataset_name and dataset_split."
            )

        # ------------------------------------------------------------------
        # 2. Load metrics for all runs
        # ------------------------------------------------------------------
        metrics_by_run: Dict[str, Dict[str, Any]] = {}
        for run_id in all_run_ids:
            metrics = await self._database.get_metrics(run_id)
            if not metrics:
                raise ValueError(
                    f"Metrics not found for run {run_id}. "
                    "Ensure the benchmark has finished processing metrics."
                )
            metrics_by_run[run_id] = metrics

        baseline_metrics = metrics_by_run[baseline_run_id]

        # ------------------------------------------------------------------
        # 3. Build comparison for each candidate
        # ------------------------------------------------------------------
        def build_deltas(candidate_metrics: Dict[str, Any]) -> Dict[str, Any]:
            """Compute metric deltas vs baseline with polarity semantics."""
            return {
                # Classification metrics (higher is better)
                "precision": self._compute_delta(
                    baseline_metrics.get("precision"),
                    candidate_metrics.get("precision"),
                    positive_when_increases=True,
                ),
                "recall": self._compute_delta(
                    baseline_metrics.get("recall"),
                    candidate_metrics.get("recall"),
                    positive_when_increases=True,
                ),
                "f1_score": self._compute_delta(
                    baseline_metrics.get("f1_score"),
                    candidate_metrics.get("f1_score"),
                    positive_when_increases=True,
                ),
                "accuracy": self._compute_delta(
                    baseline_metrics.get("accuracy"),
                    candidate_metrics.get("accuracy"),
                    positive_when_increases=True,
                ),
                # Error counts (lower is better)
                "false_positives": self._compute_delta(
                    float(baseline_metrics.get("false_positives", 0)),
                    float(candidate_metrics.get("false_positives", 0)),
                    positive_when_increases=False,
                ),
                "false_negatives": self._compute_delta(
                    float(baseline_metrics.get("false_negatives", 0)),
                    float(candidate_metrics.get("false_negatives", 0)),
                    positive_when_increases=False,
                ),
                # Latency metrics (lower is better)
                "avg_latency_ms": self._compute_delta(
                    baseline_metrics.get("avg_latency_ms"),
                    candidate_metrics.get("avg_latency_ms"),
                    positive_when_increases=False,
                ),
                "p50_latency_ms": self._compute_delta(
                    baseline_metrics.get("p50_latency_ms"),
                    candidate_metrics.get("p50_latency_ms"),
                    positive_when_increases=False,
                ),
                "p95_latency_ms": self._compute_delta(
                    baseline_metrics.get("p95_latency_ms"),
                    candidate_metrics.get("p95_latency_ms"),
                    positive_when_increases=False,
                ),
                "p99_latency_ms": self._compute_delta(
                    baseline_metrics.get("p99_latency_ms"),
                    candidate_metrics.get("p99_latency_ms"),
                    positive_when_increases=False,
                ),
            }

        # ------------------------------------------------------------------
        # 4. Load per-sample results for baseline (for set-theory changes)
        # ------------------------------------------------------------------
        baseline_results_by_index = await self._database.get_results_by_sample_index(
            baseline_run_id
        )

        candidates: List[Dict[str, Any]] = []
        for candidate_run_id in candidate_run_ids:
            candidate_metrics = metrics_by_run[candidate_run_id]
            candidate_results_by_index = await self._database.get_results_by_sample_index(
                candidate_run_id
            )

            # Align on common sample indices
            common_indices = sorted(
                set(baseline_results_by_index.keys())
                & set(candidate_results_by_index.keys())
            )

            regressions_critical: List[Dict[str, Any]] = []
            new_false_positives: List[Dict[str, Any]] = []
            improvements_new_detections: List[Dict[str, Any]] = []
            improvements_fixed_fp: List[Dict[str, Any]] = []

            for index in common_indices:
                baseline_sample = baseline_results_by_index[index]
                candidate_sample = candidate_results_by_index[index]

                change_type = self._classify_sample_change(
                    baseline_sample.get("result_type", ""),
                    candidate_sample.get("result_type", ""),
                )

                if change_type is SampleChangeType.UNCHANGED:
                    continue

                # Common payload for UI
                payload: Dict[str, Any] = {
                    "sample_index": index,
                    "input_text": candidate_sample.get("input_text")
                    or baseline_sample.get("input_text"),
                    "expected_label": candidate_sample.get("expected_label")
                    or baseline_sample.get("expected_label"),
                    "baseline_result_type": baseline_sample.get("result_type"),
                    "candidate_result_type": candidate_sample.get("result_type"),
                    "baseline_analysis": baseline_sample.get("analysis_details"),
                    "candidate_analysis": candidate_sample.get("analysis_details"),
                }

                if change_type is SampleChangeType.REGRESSION_TP_TO_FN:
                    regressions_critical.append(payload)
                elif change_type is SampleChangeType.REGRESSION_TN_TO_FP:
                    new_false_positives.append(payload)
                elif change_type is SampleChangeType.IMPROVEMENT_FN_TO_TP:
                    improvements_new_detections.append(payload)
                elif change_type is SampleChangeType.IMPROVEMENT_FP_TO_TN:
                    improvements_fixed_fp.append(payload)

            total_regressions = len(regressions_critical) + len(new_false_positives)
            total_improvements = (
                len(improvements_new_detections) + len(improvements_fixed_fp)
            )

            candidates.append(
                {
                    "run_id": candidate_run_id,
                    "start_time": runs_info[candidate_run_id].get("start_time"),
                    "detector_config": json.loads(
                        runs_info[candidate_run_id]["config_snapshot"]
                    ).get("detector_config")
                    if runs_info[candidate_run_id].get("config_snapshot")
                    else None,
                    "metrics": candidate_metrics,
                    "deltas": build_deltas(candidate_metrics),
                    "sample_changes": {
                        "regressions": {
                            "critical": regressions_critical,
                            "new_false_positives": new_false_positives,
                        },
                        "improvements": {
                            "new_detections": improvements_new_detections,
                            "fixed_false_positives": improvements_fixed_fp,
                        },
                        "summary": {
                            "total_regressions": total_regressions,
                            "total_improvements": total_improvements,
                            "net_change": total_improvements - total_regressions,
                        },
                    },
                }
            )

        # Build baseline payload with detector_config
        baseline_config = (
            json.loads(baseline_info["config_snapshot"]).get("detector_config")
            if baseline_info.get("config_snapshot")
            else None
        )

        return {
            "dataset_info": {
                "dataset_name": baseline_dataset_name,
                "dataset_split": baseline_dataset_split,
            },
            "baseline": {
                "run_id": baseline_run_id,
                "start_time": baseline_info.get("start_time"),
                "detector_config": baseline_config,
                "metrics": baseline_metrics,
            },
            "candidates": candidates,
        }


# Global instance; initialized in startup.
benchmark_service = BenchmarkService()


