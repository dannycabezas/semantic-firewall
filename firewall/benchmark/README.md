# Benchmark System - Semantic Firewall

Benchmark system for evaluating the semantic firewall's performance against Hugging Face datasets.

## Features

- ✅ Automatic dataset loading from Hugging Face Hub
- ✅ Asynchronous benchmark execution
- ✅ Detailed metrics: Precision, Recall, F1-Score, Accuracy
- ✅ Confusion matrix (TP, FP, TN, FN)
- ✅ Error analysis: False Positives and False Negatives
- ✅ Persistent storage in SQLite
- ✅ Interactive React dashboard
- ✅ Benchmark cancellation support
- ✅ CSV results export

## Architecture

### Backend

```
firewall/benchmark/
├── __init__.py
├── database.py              # SQLite schema and DB operations
├── dataset_loader.py        # HuggingFace dataset loading
├── benchmark_runner.py      # Benchmark orchestration
├── metrics_calculator.py    # Metrics calculation
├── init_db.py              # Initialization script
└── README.md
```

### Frontend

```
frontend/src/components/benchmarks/
├── BenchmarkDashboard.jsx      # Main component
├── BenchmarkExecutor.jsx       # Form to start benchmarks
├── BenchmarkHistory.jsx        # Execution history
├── BenchmarkMetricsView.jsx    # Metrics visualization
└── ErrorAnalysisView.jsx       # FP/FN analysis
```

## Usage

### 1. Initialize the Database

```bash
cd firewall
python -m benchmark.init_db
```

### 2. Start the Firewall

The benchmark system initializes automatically when starting the firewall:

```bash
python semantic_firewall.py
```

### 3. Access the Dashboard

Navigate to `http://localhost:5173/benchmarks` in the frontend.

### 4. Run a Benchmark

1. Go to the "New Execution" tab
2. Enter the dataset name (e.g., `jackhhao/jailbreak-classification`)
3. Select the split (test/train/validation)
4. Optionally, limit the number of samples
5. Click "Start Benchmark"

### 5. View Results

- **Metrics**: View F1-Score, Accuracy, Confusion Matrix
- **Error Analysis**: Explore false positives and negatives with ML score details
- **History**: Compare multiple executions

## Supported Datasets

The system automatically maps these datasets:

### jackhhao/jailbreak-classification
- **Prompt column**: `prompt`
- **Label column**: `type`
- **Values**: `"jailbreak"` (malicious) or `"benign"` (safe)

### Custom Datasets

To add support for other datasets, edit `dataset_loader.py`:

```python
DATASET_MAPPINGS = {
    "your-user/your-dataset": {
        "prompt_column": "text",
        "label_column": "label",
        "label_mapping": {
            "attack": "jailbreak",
            "safe": "benign"
        }
    }
}
```

## API Endpoints

### POST /api/benchmarks/start
Starts a new benchmark.

**Request:**
```json
{
  "dataset_name": "jackhhao/jailbreak-classification",
  "dataset_split": "test",
  "max_samples": 100,
  "tenant_id": "benchmark"
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "status": "running",
  "message": "Benchmark started successfully"
}
```

### GET /api/benchmarks/status/{run_id}
Gets the current status of a benchmark.

**Response:**
```json
{
  "run_id": "uuid",
  "status": "running",
  "total_samples": 100,
  "processed_samples": 45,
  "progress_percent": 45.0,
  "elapsed_time_seconds": 67.5,
  "estimated_remaining_seconds": 82.5
}
```

### GET /api/benchmarks/metrics/{run_id}
Gets calculated metrics.

**Response:**
```json
{
  "true_positives": 85,
  "false_positives": 5,
  "true_negatives": 90,
  "false_negatives": 20,
  "precision": 0.9444,
  "recall": 0.8095,
  "f1_score": 0.8717,
  "accuracy": 0.8750,
  "avg_latency_ms": 125.5
}
```

### GET /api/benchmarks/errors/{run_id}
Gets detailed error analysis.

**Response:**
```json
{
  "false_positives": [
    {
      "id": 1,
      "input_text": "prompt incorrectly blocked",
      "expected_label": "benign",
      "predicted_label": "blocked",
      "analysis_details": {
        "reason": "High toxicity score",
        "ml_signals": {
          "prompt_injection_score": 0.65,
          "toxicity_score": 0.82,
          "pii_score": 0.12
        }
      }
    }
  ],
  "false_negatives": [...]
}
```

## Metrics Interpretation

### Confusion Matrix

- **True Positive (TP)**: Attacks correctly detected ✅
- **False Negative (FN)**: Attacks that passed through ❌ (CRITICAL - security risk)
- **False Positive (FP)**: Legitimate users blocked ⚠️ (UX impact)
- **True Negative (TN)**: Legitimate users allowed ✅

### Classification Metrics

- **Precision** = TP / (TP + FP) - Of everything blocked, how much was actually malicious
- **Recall** = TP / (TP + FN) - Of all attacks, how many we detected
- **F1-Score** = 2 * (Precision * Recall) / (Precision + Recall) - Balance between Precision and Recall
- **Accuracy** = (TP + TN) / Total - Overall percentage of correct predictions

### Use Cases for Tuning

#### High FN (False Negatives)
- **Problem**: Attacks passing through the firewall
- **Solution**: 
  - Increase detector sensitivity
  - Reduce thresholds
  - Train models with new examples

#### High FP (False Positives)
- **Problem**: Legitimate users blocked
- **Solution**:
  - Reduce sensitivity
  - Increase thresholds
  - Refine heuristic rules

## Environment Variables

```bash
# Benchmark database path
BENCHMARK_DB_PATH=/data/benchmarks.db
```

## Dependencies

Backend:
- `datasets` - Hugging Face datasets library
- `aiosqlite` - SQLite async
- `numpy` - Statistical calculations

Frontend:
- `react-router-dom` - Routing
- `recharts` - Visualizations

## Troubleshooting

### Error: "Benchmark system not initialized"
- Verify that the database was initialized correctly
- Check server logs for startup errors

### Benchmark stuck in "running" indefinitely
- Check server logs for exceptions
- Verify connectivity with Hugging Face Hub
- Ensure the dataset exists and is accessible

### Metrics not available
- Metrics are only calculated when the benchmark completes
- Wait for the status to be "completed"
- If the benchmark failed, there will be no metrics

## Contributing

To add support for new dataset types:

1. Edit `DATASET_MAPPINGS` in `dataset_loader.py`
2. Add tests for the new format
3. Update this documentation
