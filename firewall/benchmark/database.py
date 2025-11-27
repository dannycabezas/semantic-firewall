"""Database schema and operations for benchmark storage."""

import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class BenchmarkDatabase:
    """Manages SQLite database for benchmark results."""

    def __init__(self, db_path: str = "benchmarks.db"):
        self.db_path = db_path

    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Benchmark runs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    id TEXT PRIMARY KEY,
                    dataset_name TEXT NOT NULL,
                    dataset_source TEXT NOT NULL,
                    dataset_split TEXT,
                    config_snapshot TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    total_samples INTEGER,
                    processed_samples INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)

            # Individual benchmark results
            await db.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    sample_index INTEGER NOT NULL,
                    input_text TEXT NOT NULL,
                    expected_label TEXT NOT NULL,
                    predicted_label TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    result_type TEXT NOT NULL,
                    analysis_details TEXT,
                    latency_ms REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(id)
                )
            """)

            # Aggregate metrics per run
            await db.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_metrics (
                    run_id TEXT PRIMARY KEY,
                    true_positives INTEGER NOT NULL,
                    false_positives INTEGER NOT NULL,
                    true_negatives INTEGER NOT NULL,
                    false_negatives INTEGER NOT NULL,
                    precision REAL NOT NULL,
                    recall REAL NOT NULL,
                    f1_score REAL NOT NULL,
                    accuracy REAL NOT NULL,
                    avg_latency_ms REAL,
                    p50_latency_ms REAL,
                    p95_latency_ms REAL,
                    p99_latency_ms REAL,
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(id)
                )
            """)

            # Create indices for better query performance
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_run_id 
                ON benchmark_results(run_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_results_type 
                ON benchmark_results(result_type)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_status 
                ON benchmark_runs(status)
            """)

            await db.commit()

    async def create_run(
        self,
        run_id: str,
        dataset_name: str,
        dataset_source: str,
        dataset_split: str,
        config_snapshot: Dict[str, Any],
        total_samples: int
    ) -> str:
        """Create a new benchmark run."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO benchmark_runs 
                (id, dataset_name, dataset_source, dataset_split, config_snapshot, 
                 start_time, status, total_samples, processed_samples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                dataset_name,
                dataset_source,
                dataset_split,
                json.dumps(config_snapshot),
                datetime.utcnow().isoformat(),
                "running",
                total_samples,
                0
            ))
            await db.commit()
        return run_id

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update the status of a benchmark run."""
        async with aiosqlite.connect(self.db_path) as db:
            if status in ["completed", "failed", "cancelled"]:
                await db.execute("""
                    UPDATE benchmark_runs 
                    SET status = ?, end_time = ?, error_message = ?
                    WHERE id = ?
                """, (status, datetime.utcnow().isoformat(), error_message, run_id))
            else:
                await db.execute("""
                    UPDATE benchmark_runs 
                    SET status = ?
                    WHERE id = ?
                """, (status, run_id))
            await db.commit()

    async def increment_processed_samples(self, run_id: str):
        """Increment the processed samples counter."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE benchmark_runs 
                SET processed_samples = processed_samples + 1
                WHERE id = ?
            """, (run_id,))
            await db.commit()

    async def save_result(
        self,
        run_id: str,
        sample_index: int,
        input_text: str,
        expected_label: str,
        predicted_label: str,
        is_correct: bool,
        result_type: str,
        analysis_details: Dict[str, Any],
        latency_ms: float
    ):
        """Save an individual benchmark result."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO benchmark_results
                (run_id, sample_index, input_text, expected_label, predicted_label,
                 is_correct, result_type, analysis_details, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                sample_index,
                input_text,
                expected_label,
                predicted_label,
                1 if is_correct else 0,
                result_type,
                json.dumps(analysis_details),
                latency_ms,
                datetime.utcnow().isoformat()
            ))
            await db.commit()

    async def save_results_batch(
        self,
        results: List[Dict[str, Any]]
    ):
        """
        Save multiple benchmark results in a single transaction.
        
        Args:
            results: List of result dictionaries with keys:
                - run_id, sample_index, input_text, expected_label, predicted_label,
                  is_correct, result_type, analysis_details, latency_ms
        """
        if not results:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            created_at = datetime.utcnow().isoformat()
            
            # Prepare batch data
            batch_data = []
            for result in results:
                batch_data.append((
                    result["run_id"],
                    result["sample_index"],
                    result["input_text"],
                    result["expected_label"],
                    result["predicted_label"],
                    1 if result["is_correct"] else 0,
                    result["result_type"],
                    json.dumps(result["analysis_details"]),
                    result["latency_ms"],
                    created_at
                ))
            
            # Execute batch insert
            await db.executemany("""
                INSERT INTO benchmark_results
                (run_id, sample_index, input_text, expected_label, predicted_label,
                 is_correct, result_type, analysis_details, latency_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            
            await db.commit()

    async def update_processed_samples_batch(self, run_id: str, count: int):
        """
        Increment the processed samples counter by a specific count.
        
        Args:
            run_id: Benchmark run ID
            count: Number of samples to add to processed count
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE benchmark_runs 
                SET processed_samples = processed_samples + ?
                WHERE id = ?
            """, (count, run_id))
            await db.commit()

    async def save_metrics(
        self,
        run_id: str,
        metrics: Dict[str, Any]
    ):
        """Save aggregate metrics for a benchmark run."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO benchmark_metrics
                (run_id, true_positives, false_positives, true_negatives, false_negatives,
                 precision, recall, f1_score, accuracy, avg_latency_ms, 
                 p50_latency_ms, p95_latency_ms, p99_latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                metrics["true_positives"],
                metrics["false_positives"],
                metrics["true_negatives"],
                metrics["false_negatives"],
                metrics["precision"],
                metrics["recall"],
                metrics["f1_score"],
                metrics["accuracy"],
                metrics.get("avg_latency_ms"),
                metrics.get("p50_latency_ms"),
                metrics.get("p95_latency_ms"),
                metrics.get("p99_latency_ms")
            ))
            await db.commit()

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a benchmark run by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_all_runs(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all benchmark runs with pagination."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM benchmark_runs 
                ORDER BY start_time DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_results(
        self,
        run_id: str,
        result_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get results for a specific run, optionally filtered by type."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if result_type:
                query = """
                    SELECT * FROM benchmark_results 
                    WHERE run_id = ? AND result_type = ?
                    ORDER BY sample_index
                    LIMIT ? OFFSET ?
                """
                params = (run_id, result_type, limit, offset)
            else:
                query = """
                    SELECT * FROM benchmark_results 
                    WHERE run_id = ?
                    ORDER BY sample_index
                    LIMIT ? OFFSET ?
                """
                params = (run_id, limit, offset)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_metrics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific run."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM benchmark_metrics WHERE run_id = ?", (run_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_error_analysis(
        self,
        run_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed error analysis (FP and FN) for a run."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get false positives
            async with db.execute("""
                SELECT * FROM benchmark_results 
                WHERE run_id = ? AND result_type = 'FALSE_POSITIVE'
                ORDER BY sample_index
            """, (run_id,)) as cursor:
                false_positives = [dict(row) for row in await cursor.fetchall()]
            
            # Get false negatives
            async with db.execute("""
                SELECT * FROM benchmark_results 
                WHERE run_id = ? AND result_type = 'FALSE_NEGATIVE'
                ORDER BY sample_index
            """, (run_id,)) as cursor:
                false_negatives = [dict(row) for row in await cursor.fetchall()]
            
            return {
                "false_positives": false_positives,
                "false_negatives": false_negatives
            }

