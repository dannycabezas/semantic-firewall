"""Ollama + ONNX-based prompt injection detector adapter.

Supports two embedding modes:
- Local: Uses SentenceTransformers for fast local embeddings (~50-200ms)
- Ollama: Uses Ollama API with connection pooling (~2-5s)
"""

import threading
from typing import Any, Optional

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.request_context import RequestContext
from core.utils.decorators import log_execution_time
from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector


class CustomONNXPromptInjectionDetector(IPromptInjectionDetector):
    """Ollama + ONNX implementation for prompt injection detection.
    
    Supports local embeddings via SentenceTransformers for improved performance.
    Uses class-level model caching to avoid loading models multiple times.
    """
    
    # Class-level shared model cache (singleton pattern)
    _shared_local_embedding_model: Any = None
    _shared_local_embedding_model_name: Optional[str] = None
    _model_load_lock = threading.Lock()
    _local_model_failed = False

    def __init__(
        self,
        model_path: str,
        ollama_base_url: str = "http://ollama:11434",
        ollama_model: str = "nomic-embed-text:v1.5",
        threshold: float = 0.5,
        use_local_embeddings: bool = True,
        local_embedding_model: str = "nomic-ai/nomic-embed-text-v1.5",
    ) -> None:
        """
        Initialize Ollama + ONNX prompt injection detector.

        Args:
            model_path: Path to ONNX model file (SF_model_v1.onnx)
            ollama_base_url: Base URL for Ollama API
            ollama_model: Ollama embedding model to use
            threshold: Threshold for blocking (0.0 to 1.0)
            use_local_embeddings: If True, use SentenceTransformers locally (faster)
            local_embedding_model: Model name for local embeddings
        """
        self.model_path = model_path
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model
        self.threshold = threshold
        self._onnx_model = None
        self._use_model = False
        
        # Local embeddings configuration
        self._use_local_embeddings = use_local_embeddings
        self._local_embedding_model_name = local_embedding_model
        
        # HTTP Session with connection pooling and retry logic
        self._session = self._create_http_session()
    
    def _create_http_session(self) -> requests.Session:
        """Create an optimized HTTP session with connection pooling and retries."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        
        # Configure connection pool
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=retry_strategy,
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @log_execution_time()
    def _load_local_embedding_model(self) -> bool:
        """Lazy load local SentenceTransformer model with class-level caching.
        
        Uses a lock to prevent multiple threads from loading the model simultaneously.
        The model is shared across all instances of this class.
        """
        # Fast path: check if model is already loaded (no lock needed for read)
        if (
            CustomONNXPromptInjectionDetector._shared_local_embedding_model is not None
            and CustomONNXPromptInjectionDetector._shared_local_embedding_model_name == self._local_embedding_model_name
        ):
            return True
        
        # Check if we already failed to load the model
        if CustomONNXPromptInjectionDetector._local_model_failed:
            return False
        
        # Slow path: acquire lock and load model
        with CustomONNXPromptInjectionDetector._model_load_lock:
            # Double-check after acquiring lock
            if (
                CustomONNXPromptInjectionDetector._shared_local_embedding_model is not None
                and CustomONNXPromptInjectionDetector._shared_local_embedding_model_name == self._local_embedding_model_name
            ):
                return True
            
            if CustomONNXPromptInjectionDetector._local_model_failed:
                return False
            
            try:
                from sentence_transformers import SentenceTransformer
                
                print(f"Loading local embedding model: {self._local_embedding_model_name}")
                CustomONNXPromptInjectionDetector._shared_local_embedding_model = SentenceTransformer(
                    self._local_embedding_model_name,
                    trust_remote_code=True,
                )
                CustomONNXPromptInjectionDetector._shared_local_embedding_model_name = self._local_embedding_model_name
                print("✓ Local embedding model loaded successfully")
                return True
            except Exception as e:
                print(f"Failed to load local embedding model: {e}. Falling back to Ollama.")
                CustomONNXPromptInjectionDetector._local_model_failed = True
                self._use_local_embeddings = False
                return False

    @log_execution_time()
    def _load_onnx_model(self) -> None:
        """Lazy load ONNX model."""
        if self.model_path and not self._use_model:
            try:
                import onnxruntime as ort

                self._onnx_model = ort.InferenceSession(
                    self.model_path,
                    providers=["CPUExecutionProvider"],
                )
                self._use_model = True
                print(f"Loaded ONNX prompt injection model from {self.model_path}")
            except Exception as e:
                print(f"Failed to load ONNX model: {e}. Using fallback.")
                self._use_model = False

    @log_execution_time()
    def _format_text_with_context(
        self, text: str, context: RequestContext | None = None
    ) -> str:
        """
        Format text with metadata for embedding generation.

        Args:
            text: Input text
            context: Request context

        Returns:
            Formatted text string
        """
        ctx = context.to_dict() if context else {}
        return (
            f"text: {text} || "
            f"UserID: {ctx.get('user_id', 'runtime_user')} || "
            f"Temperature: {ctx.get('temperature', 0.5)} || "
            f"Tokens: {ctx.get('max_tokens', 20)} || "
            f"Turn_Count: {ctx.get('turn_count', 1)} || "
            f"Rate_Limit: {ctx.get('rate_limit', 0)} || "
            f"Device: {ctx.get('device', 'Unknown')} || "
            f"Endpoint: {ctx.get('endpoint', '/threat/query')}"
        )


    @log_execution_time()
    def _get_local_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding using local SentenceTransformer model.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array with embedding or None if failed
        """
        try:
            if not self._load_local_embedding_model():
                return None
            
            # Use the shared class-level model
            model = CustomONNXPromptInjectionDetector._shared_local_embedding_model
            
            # SentenceTransformers encode returns numpy array directly
            embedding = model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return embedding.astype(np.float32)
        except Exception as e:
            print(f"Failed to get local embedding: {e}")
            return None
    
    @log_execution_time()
    def _get_ollama_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding from Ollama API using connection pooling.

        Args:
            text: Text to embed

        Returns:
            Numpy array with embedding or None if failed
        """
        try:
            print(f"Getting embedding from Ollama API for the text size {len(text)}")
            # Use session with connection pooling instead of creating new connection each time
            response = self._session.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={"model": self.ollama_model, "prompt": text},
                timeout=30,
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            if embedding is None and "embeddings" in response:
                embedding = response["embeddings"][0]
            if embedding is None or len(embedding) == 0:
                raise ValueError(f"Empty embedding from Ollama. Response: {response}")
            print(f"Got embedding from Ollama API for the text size {len(text)}")
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            print(f"Failed to get Ollama embedding: {e}")
            return None
    
    @log_execution_time()
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding using the configured method (local or Ollama).
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array with embedding or None if failed
        """
        if self._use_local_embeddings:
            embedding = self._get_local_embedding(text)
            if embedding is not None:
                return embedding
            # Fallback to Ollama if local fails
            print("Local embedding failed, falling back to Ollama")
        
        return self._get_ollama_embedding(text)

    @log_execution_time()
    def _apply_softmax(self, logits: np.ndarray) -> np.ndarray:
        """Apply softmax to logits to get probabilities.

        Args:
            logits: Model output logits

        Returns:
            Probability distribution
        """
        logits = np.asarray(logits)
        x_shift = logits - np.max(logits, axis=-1, keepdims=True)
        exp_logits = np.exp(x_shift)
        return exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)


    @log_execution_time()
    def _run_onnx_inference(self, embedding: np.ndarray) -> float:
        """
        Run ONNX model inference on embedding.

        Args:
            embedding: Input embedding vector

        Returns:
            Prompt injection probability (0.0 to 1.0)
        """
        try:
            outputs = self._run_model(embedding)

            # Apply softmax to get probabilities
            # probs shape: [2] (prob_benign, prob_malign)
            probs = self._apply_softmax(outputs[0][0])

            # Binary classification:
            # - Index 0: Probability of being benign (Safe/No injection)
            # - Index 1: Probability of being malign (Prompt injection detected)

            if len(probs) >= 2:
                # Return the probability of malign (index 1)
                injection_prob = float(probs[1])
            else:
                # Fallback: if there is only one output, use that probability
                injection_prob = float(probs[0])

            return min(max(injection_prob, 0.0), 1.0)

        except Exception as e:
            print(f"Error during ONNX inference: {e}")
            raise

    @log_execution_time()
    def _run_model(self, embedding: np.ndarray) -> np.ndarray:
        """Run ONNX model inference and return the outputs."""
        # Ensure embedding has the correct shape for the model
        # Reshape to (batch_size, embedding_dim)
        if embedding.ndim == 1:
            embedding = embedding[np.newaxis, :]

        # Get input and output names from model
        input_name = self._onnx_model.get_inputs()[0].name
        output_name = self._onnx_model.get_outputs()[0].name

        # Run inference
        outputs = self._onnx_model.run([output_name], {input_name: embedding.astype(np.float32)})
        return outputs

    @log_execution_time()
    def detect(self, text: str, context: RequestContext | None = None) -> float:
        """
        Detect prompt injection in text using embeddings + ONNX model.

        Pipeline:
        1. Format text with context
        2. Get embedding (local SentenceTransformer or Ollama)
        3. Send embedding to ONNX model
        4. Apply softmax → get probabilities
        5. Return injection score

        Args:
            text: Text to analyze
            context: Request context

        Returns:
            Prompt injection score between 0.0 and 1.0 (1.0 = high confidence injection)
        """
        # Load model if not already loaded
        self._load_onnx_model()

        if self._use_model and self._onnx_model:
            try:
                # Step 1: Format text with context
                formatted_text = self._format_text_with_context(text, context)

                # Step 2: Get embedding (local or Ollama based on configuration)
                embedding = self._get_embedding(formatted_text)
                
                if embedding is not None:
                    print(f"Embedding obtained: text_size={len(formatted_text)}, embedding_shape={embedding.shape}")
                    # Step 3-5: Run ONNX inference with softmax
                    injection_score = self._run_onnx_inference(embedding)
                    return injection_score
                else:
                    print("Failed to get embedding, using fallback detection")

            except Exception as e:
                print(f"Error in full pipeline: {e}. Using fallback.")

        # Fallback: keyword-based detection
        return self._fallback_detection(text)

    def _fallback_detection(self, text: str) -> float:
        """
        Fallback keyword-based prompt injection detection.

        Args:
            text: Text to analyze

        Returns:
            Injection score based on keyword matches
        """
        injection_keywords = [
            "ignore previous",
            "ignore all previous",
            "forget instructions",
            "disregard instructions",
            "system prompt",
            "override",
            "new instructions",
            "disregard",
            "pretend you are",
            "act as if",
            "you are now",
            "new role",
            "roleplay",
            "forget everything",
            "ignore everything",
        ]

        text_lower = text.lower()
        matches = sum(1 for keyword in injection_keywords if keyword in text_lower)

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.6
        else:
            return min(0.9, 0.3 + (matches - 1) * 0.2)