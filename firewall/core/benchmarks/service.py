from __future__ import annotations

import json
import logging
from typing import Optional, Dict, Any, List

from benchmark.database import BenchmarkDatabase
from benchmark.benchmark_runner import BenchmarkRunner
from core.gateway import get_default_gateway, create_gateway_orchestrator


logger = logging.getLogger(__name__)


class BenchmarkService:
    """High-level service to manage firewall benchmarks."""

    def __init__(self, db_path: str = "benchmarks.db") -> None:
        self._database = BenchmarkDatabase(db_path)
        # The runner is initialized in `initialize` because it needs the DB initialized
        self._runner: Optional[BenchmarkRunner] = None
        self._db_path = db_path

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
        dataset_name: str,
        dataset_split: str = "test",
        max_samples: Optional[int] = None,
        tenant_id: str = "benchmark",
        detector_config: Optional[Dict[str, str]] = None,
    ) -> str:
        if not self._runner:
            raise RuntimeError("Benchmark system not initialized")

        run_id = await self._runner.start_benchmark(
            dataset_name=dataset_name,
            dataset_split=dataset_split,
            max_samples=max_samples,
            tenant_id=tenant_id,
            model_config=detector_config,
        )
        return run_id

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


# Global instance; initialized in startup.
benchmark_service = BenchmarkService()


