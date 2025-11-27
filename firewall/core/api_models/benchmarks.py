from typing import Optional

from pydantic import BaseModel


class BenchmarkStartRequest(BaseModel):
    """Request to start a new benchmark."""

    dataset_name: str
    dataset_split: str = "test"
    max_samples: Optional[int] = None
    tenant_id: str = "benchmark"
    detector_config: Optional[dict[str, str]] = None



