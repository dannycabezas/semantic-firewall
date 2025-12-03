from typing import Optional, Any, Dict, List

from pydantic import BaseModel


class BenchmarkStartRequest(BaseModel):
    """Request to start a new benchmark."""

    dataset_name: Optional[str] = None
    dataset_split: str = "test"
    max_samples: Optional[int] = None
    tenant_id: str = "benchmark"
    detector_config: Optional[dict[str, str]] = None
    custom_dataset_id: Optional[str] = None


class DatasetUploadResponse(BaseModel):
    """Response to upload a custom dataset."""

    dataset_id: str
    name: str
    description: Optional[str] = None
    file_type: str
    total_samples: int
    created_at: str


class CustomDatasetInfo(BaseModel):
    """Information of a custom dataset."""

    id: str
    name: str
    description: Optional[str] = None
    file_type: str
    total_samples: int
    created_at: str


class CustomDatasetListResponse(BaseModel):
    """List of available custom datasets."""

    datasets: List[CustomDatasetInfo]


class BenchmarkDelta(BaseModel):
    """Delta information for a single metric."""

    value: Optional[float]
    percent: Optional[float]
    polarity: str  # 'positive', 'negative', 'neutral'


class BenchmarkSampleChange(BaseModel):
    """Represents how a single sample changed between baseline and candidate."""

    sample_index: int
    input_text: str
    expected_label: str
    baseline_result_type: str
    candidate_result_type: str
    baseline_analysis: Optional[Dict[str, Any]] = None
    candidate_analysis: Optional[Dict[str, Any]] = None


class BenchmarkCandidateComparison(BaseModel):
    """Comparison details for a single candidate run."""

    run_id: str
    start_time: Optional[str] = None
    detector_config: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any]
    deltas: Dict[str, BenchmarkDelta]
    sample_changes: Dict[str, Any]


class BenchmarkComparisonResponse(BaseModel):
    """High-level response for benchmark comparison with explicit baseline."""

    dataset_info: Dict[str, Any]
    baseline: Dict[str, Any]
    candidates: List[BenchmarkCandidateComparison]

