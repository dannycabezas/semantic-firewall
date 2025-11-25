"""Initialize benchmark database schema."""

import asyncio
import os
import sys

# Add parent directory to path to import benchmark modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.database import BenchmarkDatabase


async def main():
    """Initialize the benchmark database."""
    db_path = os.getenv("BENCHMARK_DB_PATH", "benchmarks.db")
    
    print(f"Initializing benchmark database at: {db_path}")
    
    db = BenchmarkDatabase(db_path)
    await db.initialize()
    
    print("✅ Database initialized successfully!")
    print(f"   - benchmark_runs table created")
    print(f"   - benchmark_results table created")
    print(f"   - benchmark_metrics table created")
    print(f"   - Indices created")


if __name__ == "__main__":
    asyncio.run(main())

