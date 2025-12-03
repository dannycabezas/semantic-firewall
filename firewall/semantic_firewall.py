import asyncio
import logging
import os
import uuid
from typing import Optional, Any

from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
    Request,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from benchmark.dataset_loader import DatasetLoader
from core.gateway import get_default_gateway
from core.realtime import manager
from core.metrics import metrics_service
from core.benchmarks import benchmark_service
from core.api_models import (
    ChatRequest,
    ChatResponse,
    DetectorMetrics,
    PreprocessingMetrics,
    PolicyMetrics,
    BenchmarkStartRequest,
    DatasetUploadResponse,
    CustomDatasetListResponse,
)
from fast_ml_filter.detector_factory import DetectorFactory


DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
if DEBUG_MODE:
    import debugpy

    debugpy.listen(("0.0.0.0", 5678))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TENANT_ID = os.getenv("TENANT_ID", "default")

# Initialize Benchmark components (managed now by BenchmarkService) by default benchmarks.db
BENCHMARK_DB_PATH = os.getenv("BENCHMARK_DB_PATH", "benchmarks.db")


firewall = get_default_gateway()

app = FastAPI(title="SPG Semantic Firewall")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers by context
chat_router = APIRouter()
realtime_router = APIRouter()
metrics_router = APIRouter()
benchmarks_router = APIRouter()


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        Unique request ID
    """
    return str(uuid.uuid4())


@chat_router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Main endpoint for chat with firewall integrated.

    Flow:
    1. Analysis ingress (preprocess + ML + policies)
    2. Proxy to backend (if passes the firewall)
    3. Analysis egress (backend response)
    4. Return response or block

    Args:
        payload: User message
        request: Request object

    Returns:
        Backend response or block message with metrics from detectors

    Raises:
        HTTPException: In case of error
    """
    from core.gateway.chat_service import process_chat_request

    return await process_chat_request(payload, request)


@realtime_router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dictionary with status and service name
    """
    return {"status": "healthy", "service": "semantic-firewall"}


@realtime_router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time dashboard updates.

    Sends:
    - Real-time request events as they are processed
    - Periodic heartbeat pings

    Expects:
    - Pong responses to heartbeat pings
    """
    await manager.connect(websocket)

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(manager.heartbeat_sender(websocket))
    
    try:
        while True:
            # Listen for messages from client (mainly pong responses)
            data = await websocket.receive_json()
            
            if data.get("type") == "pong":
                # Client responded to heartbeat
                logger.debug("Received pong from dashboard client")
            
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
        manager.disconnect(websocket)
        heartbeat_task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        heartbeat_task.cancel()


@metrics_router.get("/api/stats")
async def get_stats() -> dict[str, Any]:
    """
    Get executive KPIs and aggregated statistics.

    Returns:
        Dictionary with:
        - Total prompts
        - Percentage breakdowns (benign, suspicious, malicious)
        - Block/allow ratio
        - Prompts per minute
        - Risk trend
        - Average latencies
        - Risk category breakdown
    """
    try:
        stats = metrics_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        ) from e


@metrics_router.get("/api/models/available")
async def get_available_models() -> dict[str, Any]:
    """
    Get list of available detector models for each category.

    Returns:
        Dictionary with available models for:
        - prompt_injection
        - pii
        - toxicity

        And default models for each category.
    """
    try:
        available = DetectorFactory.get_available_models()
        defaults = DetectorFactory.get_default_models()
        return {
            "available": available,
            "defaults": defaults
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving available models"
        ) from e


@metrics_router.get("/api/models/cache")
async def get_models_cache_status() -> dict[str, Any]:
    """
    Get status of the detector cache.
    
    Returns:
        Dictionary with:
        - cached_detectors: List of detector keys currently in cache
        - cache_size: Number of detectors in cache
        - cache_enabled: Whether caching is enabled
    """
    try:
        # Create a factory instance to access cache
        factory = DetectorFactory()
        cache_stats = factory.get_cache_stats()
        
        return cache_stats
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving cache status"
        ) from e


@metrics_router.post("/api/models/cache/clear")
async def clear_models_cache() -> dict[str, Any]:
    """
    Clear the detector cache.
    
    Returns:
        Number of detectors removed from cache
    """
    try:
        # Create a factory instance to access cache
        factory = DetectorFactory()
        count = factory.clear_cache()
        
        return {
            "message": "Cache cleared successfully",
            "detectors_removed": count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error clearing cache"
        ) from e


@metrics_router.get("/api/recent-requests")
async def get_recent_requests(limit: int = 50) -> dict[str, Any]:
    """
    Get the most recent N requests.
    
    Args:
        limit: Maximum number of requests to return (default: 50, max: 200)
        
    Returns:
        List of recent request events
    """
    try:
        # Limit to max 200
        limit = min(limit, 200)
        recent = metrics_service.get_recent(limit=limit)
        return {"requests": recent, "count": len(recent)}
    except Exception as e:
        logger.error(f"Error getting recent requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving recent requests"
        ) from e


@metrics_router.get("/api/session-analytics")
async def get_session_analytics(top: int = 5) -> dict[str, Any]:
    """
    Get analytics for top sessions with most suspicious activity.
    
    Args:
        top: Number of top sessions to return (default: 5)
        
    Returns:
        List of session analytics
    """
    try:
        analytics = metrics_service.get_session_analytics(top_n=top)
        return {"sessions": analytics, "count": len(analytics)}
    except Exception as e:
        logger.error(f"Error getting session analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving session analytics"
        ) from e


@metrics_router.get("/api/temporal-breakdown")
async def get_temporal_breakdown(minutes: int = 10) -> dict[str, Any]:
    """
    Get temporal breakdown of risk categories.
    
    Args:
        minutes: Number of minutes to analyze (default: 10, max: 60)
        
    Returns:
        Temporal breakdown with timestamps and category counts
    """
    try:
        minutes = min(minutes, 60)
        breakdown = metrics_service.get_temporal_breakdown(minutes=minutes)
        return breakdown
    except Exception as e:
        logger.error(f"Error getting temporal breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving temporal breakdown"
        ) from e


@benchmarks_router.post("/api/benchmarks/start")
async def start_benchmark(request: BenchmarkStartRequest) -> dict[str, Any]:
    """
    Start a new benchmark run.
    
    Args:
        request: Benchmark configuration
        
    Returns:
        Benchmark run ID and initial status
    """
    try:
        if not benchmark_service.runner:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Benchmark system not initialized",
            )

        run_id = await benchmark_service.start_benchmark(
            dataset_name=request.dataset_name,
            dataset_split=request.dataset_split,
            max_samples=request.max_samples,
            tenant_id=request.tenant_id,
            detector_config=request.detector_config,
            custom_dataset_id=request.custom_dataset_id,
        )
        
        return {
            "run_id": run_id,
            "status": "running",
            "message": "Benchmark started successfully"
        }
    except Exception as e:
        logger.error(f"Error starting benchmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start benchmark: {e}"
        ) from e


@benchmarks_router.get("/api/benchmarks/status/{run_id}")
async def get_benchmark_status(run_id: str) -> dict[str, Any]:
    """
    Get the current status of a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Current status and progress information
    """
    try:
        if not benchmark_service.runner:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Benchmark system not initialized",
            )

        status_info = await benchmark_service.get_status(run_id)
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark status"
        ) from e


@benchmarks_router.post("/api/benchmarks/cancel/{run_id}")
async def cancel_benchmark(run_id: str) -> dict[str, Any]:
    """
    Cancel a running benchmark.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Cancellation status
    """
    try:
        if not benchmark_service.runner:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Benchmark system not initialized",
            )

        success = await benchmark_service.cancel_benchmark(run_id)
        
        if success:
            return {"message": "Benchmark cancelled successfully"}
        else:
            return {"message": "Benchmark not found or already completed"}
    except Exception as e:
        logger.error(f"Error cancelling benchmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelling benchmark"
        ) from e


@benchmarks_router.get("/api/benchmarks/runs")
async def get_benchmark_runs(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """
    Get list of all benchmark runs with pagination.
    
    Args:
        limit: Maximum number of runs to return
        offset: Number of runs to skip
        
    Returns:
        List of benchmark runs
    """
    try:
        runs = await benchmark_service.get_runs(limit=limit, offset=offset)
        return {"runs": runs, "count": len(runs)}
    except Exception as e:
        logger.error(f"Error getting benchmark runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark runs"
        ) from e


@benchmarks_router.get("/api/benchmarks/results/{run_id}")
async def get_benchmark_results(
    run_id: str,
    result_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> dict[str, Any]:
    """
    Get detailed results for a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        result_type: Optional filter (TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, FALSE_NEGATIVE)
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of benchmark results
    """
    try:
        results = await benchmark_service.get_results(
            run_id=run_id, result_type=result_type, limit=limit, offset=offset
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting benchmark results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark results"
        ) from e


@benchmarks_router.get("/api/benchmarks/metrics/{run_id}")
async def get_benchmark_metrics(run_id: str) -> dict[str, Any]:
    """
    Get calculated metrics for a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Benchmark metrics including confusion matrix and performance stats
    """
    try:
        metrics = await benchmark_service.get_metrics(run_id)
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark metrics"
        ) from e


@benchmarks_router.get("/api/benchmarks/errors/{run_id}")
async def get_benchmark_errors(run_id: str) -> dict[str, Any]:
    """
    Get detailed error analysis (false positives and false negatives).
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Error analysis with false positives and false negatives
    """
    try:
        error_analysis = await benchmark_service.get_error_analysis(run_id)
        return error_analysis
    except Exception as e:
        logger.error(f"Error getting benchmark error analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving error analysis"
        ) from e


@benchmarks_router.get("/api/benchmarks/compare")
async def compare_benchmarks(
    baseline_run_id: str,
    candidate_run_ids: str,
) -> dict[str, Any]:
    """
    Compare a baseline benchmark against one or more candidate benchmarks.

    Guardrails:
    - baseline_run_id is required
    - At least one candidate_run_id is required
    - All runs must exist and be completed
    - All runs must share the same dataset_name and dataset_split
    """
    try:
        if not baseline_run_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="baseline_run_id is required",
            )

        if not candidate_run_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one candidate_run_id is required",
            )

        # Parse comma-separated candidate_run_ids
        candidate_ids = [
            run_id.strip()
            for run_id in candidate_run_ids.split(",")
            if run_id.strip()
        ]

        if not candidate_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid candidate_run_ids provided",
            )

        # Delegate heavy logic and guardrails to the service
        comparison = await benchmark_service.compare_benchmarks(
            baseline_run_id=baseline_run_id,
            candidate_run_ids=candidate_ids,
        )
        return comparison
    except HTTPException:
        # Re-raise FastAPI HTTP errors as-is
        raise
    except KeyError as e:
        # Run not found
        logger.error(f"Benchmark comparison failed (missing run): {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        # Guardrail violations (datasets, status, metrics missing, etc.)
        logger.warning(f"Benchmark comparison validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error comparing benchmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing benchmarks",
        ) from e


@benchmarks_router.post(
    "/api/benchmarks/datasets/upload",
    response_model=DatasetUploadResponse,
)
async def upload_custom_dataset(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
) -> DatasetUploadResponse:
    """
    Upload a new custom dataset for benchmarks.

    Accepts CSV or JSON files with the following structure:
    - column/field \"prompt\"
    - column/field \"type\" (\"benign\" or \"jailbreak\")
    """
    try:
        content_type = file.content_type or ""
        if content_type not in {"text/csv", "application/json"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}. Use CSV or JSON.",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        # Validar estructura y obtener total de samples usando DatasetLoader
        loader = DatasetLoader()
        samples = loader.load_custom_dataset_from_content(
            content=file_bytes,
            file_type=content_type,
            max_samples=None,
        )

        dataset_id, created = await benchmark_service.register_custom_dataset(
            name=name,
            description=description,
            file_content=file_bytes,
            file_type=content_type,
            total_samples=len(samples),
        )

        return DatasetUploadResponse(
            dataset_id=dataset_id,
            name=name,
            description=description,
            file_type=content_type,
            total_samples=len(samples),
            created_at=created,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading custom dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading custom dataset",
        ) from e


@benchmarks_router.get(
    "/api/benchmarks/datasets",
    response_model=CustomDatasetListResponse,
)
async def list_custom_datasets(
    limit: int = 100,
    offset: int = 0,
) -> CustomDatasetListResponse:
    """List available custom datasets."""
    try:
        datasets = await benchmark_service.list_custom_datasets(
            limit=limit,
            offset=offset,
        )
        return CustomDatasetListResponse(datasets=datasets)
    except Exception as e:
        logger.error(f"Error listing custom datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing custom datasets",
        ) from e


@benchmarks_router.delete("/api/benchmarks/datasets/{dataset_id}")
async def delete_custom_dataset(dataset_id: str) -> dict[str, Any]:
    """
    Delete a custom dataset.

    Note: this does not affect already executed benchmarks; it only deletes
    the file in MinIO and the metadata.
    """
    try:
        await benchmark_service.delete_custom_dataset(dataset_id)
        return {"message": "Custom dataset deleted successfully"}
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )
    except Exception as e:
        logger.error(f"Error deleting custom dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting custom dataset",
        ) from e


# Register routers in the main app
app.include_router(chat_router)
app.include_router(realtime_router)
app.include_router(metrics_router)
app.include_router(benchmarks_router)
