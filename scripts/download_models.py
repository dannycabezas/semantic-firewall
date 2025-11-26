#!/usr/bin/env python3
"""
Script to pre-download all ML models to local cache.
This should be run at container startup or during Docker build.

Models are downloaded to:
- HuggingFace models: ~/.cache/huggingface/
- Detoxify models: ~/.cache/torch/
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_huggingface_models():
    """Download all HuggingFace models used by the application."""
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError:
        logger.error("transformers library not installed")
        return False
    
    models = [
        "meta-llama/Llama-Prompt-Guard-2-86M",
        "meta-llama/Llama-Prompt-Guard-2-22M",
        "ProtectAI/deberta-v3-base-prompt-injection-v2",
    ]
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        logger.warning("HF_TOKEN not found. Some models may fail to download.")
    
    logger.info("=" * 70)
    logger.info("DOWNLOADING HUGGINGFACE MODELS")
    logger.info("=" * 70)
    
    success_count = 0
    for model_name in models:
        logger.info(f"Downloading: {model_name}")
        try:
            # Download tokenizer
            AutoTokenizer.from_pretrained(model_name, token=hf_token)
            
            # Download model
            AutoModelForSequenceClassification.from_pretrained(
                model_name, 
                token=hf_token
            )
            
            logger.info(f"✓ Successfully downloaded: {model_name}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"✗ Failed to download {model_name}: {e}")
    
    logger.info(f"\nHuggingFace Models: {success_count}/{len(models)} downloaded successfully")
    return success_count == len(models)


def download_detoxify_models():
    """Download Detoxify models."""
    try:
        from detoxify import Detoxify
    except ImportError:
        logger.error("detoxify library not installed")
        return False
    
    logger.info("=" * 70)
    logger.info("DOWNLOADING DETOXIFY MODELS")
    logger.info("=" * 70)
    
    variants = ["original"]  # Can add: "unbiased", "multilingual"
    
    success_count = 0
    for variant in variants:
        logger.info(f"Downloading Detoxify {variant} model")
        try:
            # This downloads the model to cache
            model = Detoxify(variant)
            del model  # Free memory
            
            logger.info(f"✓ Successfully downloaded: Detoxify {variant}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"✗ Failed to download Detoxify {variant}: {e}")
    
    logger.info(f"\nDetoxify Models: {success_count}/{len(variants)} downloaded successfully")
    return success_count == len(variants)


def download_presidio_models():
    """Download Presidio models (SpaCy)."""
    try:
        import spacy
    except ImportError:
        logger.warning("spacy not installed, skipping Presidio models")
        return True
    
    logger.info("=" * 70)
    logger.info("DOWNLOADING PRESIDIO/SPACY MODELS")
    logger.info("=" * 70)
    
    models = ["en_core_web_lg"]  # Presidio uses this
    
    success_count = 0
    for model_name in models:
        logger.info(f"Downloading SpaCy model: {model_name}")
        try:
            # Check if already downloaded
            try:
                spacy.load(model_name)
                logger.info(f"✓ Already downloaded: {model_name}")
                success_count += 1
            except OSError:
                # Download using spacy CLI
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "spacy", "download", model_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.info(f"✓ Successfully downloaded: {model_name}")
                    success_count += 1
                else:
                    logger.error(f"✗ Failed to download {model_name}: {result.stderr}")
        except Exception as e:
            logger.error(f"✗ Failed to download {model_name}: {e}")
    
    logger.info(f"\nSpaCy Models: {success_count}/{len(models)} downloaded successfully")
    return success_count == len(models)


def main():
    """Download all models."""
    logger.info("\n" + "=" * 70)
    logger.info("MODEL PRE-DOWNLOAD SCRIPT")
    logger.info("=" * 70 + "\n")
    
    results = {}
    
    # Download HuggingFace models
    results['huggingface'] = download_huggingface_models()
    
    # Download Detoxify models
    results['detoxify'] = download_detoxify_models()
    
    # Download Presidio/SpaCy models
    results['presidio'] = download_presidio_models()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 70)
    
    for component, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{status}: {component}")
    
    all_success = all(results.values())
    
    if all_success:
        logger.info("\n✓ All models downloaded successfully!")
        return 0
    else:
        logger.warning("\n⚠ Some models failed to download. Application will use fallbacks.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

