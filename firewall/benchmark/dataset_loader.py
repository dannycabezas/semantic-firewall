"""Dataset loader for Hugging Face datasets with normalization."""

from datasets import load_dataset
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DatasetSample:
    """Normalized dataset sample."""
    
    def __init__(self, prompt: str, expected_label: str, index: int):
        self.prompt = prompt
        self.expected_label = expected_label  # "jailbreak" or "benign"
        self.index = index


class DatasetLoader:
    """Loads and normalizes datasets from Hugging Face Hub."""
    
    # Mapping configurations for different dataset formats
    DATASET_MAPPINGS = {
        "jackhhao/jailbreak-classification": {
            "prompt_column": "prompt",
            "label_column": "type",
            "label_mapping": {
                "jailbreak": "jailbreak",
                "benign": "benign"
            }
        },
        "jackhhao/jailbreak_llms": {
            "prompt_column": "prompt",
            "label_column": "type",
            "label_mapping": {
                "jailbreak": "jailbreak",
                "benign": "benign"
            }
        },
        # Add more dataset mappings as needed
    }
    
    def __init__(self):
        pass
    
    async def load_dataset_samples(
        self,
        dataset_name: str,
        split: str = "test",
        max_samples: Optional[int] = None
    ) -> List[DatasetSample]:
        """
        Load and normalize dataset samples from Hugging Face.
        
        Args:
            dataset_name: HuggingFace dataset identifier (e.g., "jackhhao/jailbreak-classification")
            split: Dataset split to load (train, test, validation)
            max_samples: Maximum number of samples to load (None for all)
            
        Returns:
            List of normalized DatasetSample objects
        """
        logger.info(f"Loading dataset {dataset_name}, split: {split}, max_samples: {max_samples}")
        
        try:
            # Load dataset from HuggingFace
            dataset = load_dataset(dataset_name, split=split)
            
            # Get mapping configuration
            mapping = self._get_mapping(dataset_name, dataset)
            
            samples = []
            total = len(dataset)
            limit = min(max_samples, total) if max_samples else total
            
            logger.info(f"Processing {limit} samples from {total} total")
            
            for idx in range(limit):
                row = dataset[idx]
                
                # Extract prompt and label using mapping
                prompt = self._extract_prompt(row, mapping)
                expected_label = self._extract_label(row, mapping)
                
                if prompt and expected_label:
                    samples.append(DatasetSample(
                        prompt=prompt,
                        expected_label=expected_label,
                        index=idx
                    ))
            
            logger.info(f"Successfully loaded {len(samples)} samples")
            return samples
            
        except Exception as e:
            logger.error(f"Error loading dataset {dataset_name}: {e}")
            raise
    
    def _get_mapping(self, dataset_name: str, dataset) -> Dict[str, Any]:
        """Get or infer mapping configuration for the dataset."""
        # Check if we have a predefined mapping
        if dataset_name in self.DATASET_MAPPINGS:
            return self.DATASET_MAPPINGS[dataset_name]
        
        # Try to infer mapping from dataset structure
        logger.warning(f"No predefined mapping for {dataset_name}, attempting to infer")
        
        if len(dataset) == 0:
            raise ValueError("Dataset is empty")
        
        first_row = dataset[0]
        columns = list(first_row.keys())
        
        # Common column name patterns
        prompt_columns = ["prompt", "text", "input", "question", "query"]
        label_columns = ["label", "type", "category", "class", "target"]
        
        prompt_col = next((c for c in columns if c.lower() in prompt_columns), None)
        label_col = next((c for c in columns if c.lower() in label_columns), None)
        
        if not prompt_col or not label_col:
            raise ValueError(
                f"Could not infer dataset structure. Available columns: {columns}. "
                f"Please add a mapping for {dataset_name}"
            )
        
        # Infer label mapping
        unique_labels = set(dataset[label_col])
        label_mapping = {}
        
        for label in unique_labels:
            label_lower = str(label).lower()
            if "jailbreak" in label_lower or "attack" in label_lower or "malicious" in label_lower:
                label_mapping[label] = "jailbreak"
            elif "benign" in label_lower or "safe" in label_lower or "normal" in label_lower:
                label_mapping[label] = "benign"
            else:
                # Try to use as-is or default to benign
                label_mapping[label] = label_lower if label_lower in ["jailbreak", "benign"] else "benign"
        
        logger.info(f"Inferred mapping - prompt: {prompt_col}, label: {label_col}, mapping: {label_mapping}")
        
        return {
            "prompt_column": prompt_col,
            "label_column": label_col,
            "label_mapping": label_mapping
        }
    
    def _extract_prompt(self, row: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[str]:
        """Extract prompt text from row."""
        prompt_col = mapping["prompt_column"]
        prompt = row.get(prompt_col)
        
        if prompt is None:
            logger.warning(f"Missing prompt in row")
            return None
        
        return str(prompt).strip()
    
    def _extract_label(self, row: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize label from row."""
        label_col = mapping["label_column"]
        raw_label = row.get(label_col)
        
        if raw_label is None:
            logger.warning(f"Missing label in row")
            return None
        
        # Normalize label using mapping
        label_mapping = mapping["label_mapping"]
        normalized_label = label_mapping.get(raw_label)
        
        if normalized_label is None:
            logger.warning(f"Unknown label value: {raw_label}")
            return None
        
        return normalized_label
    
    def get_available_datasets(self) -> List[Dict[str, str]]:
        """Get list of predefined datasets with metadata."""
        return [
            {
                "name": "jackhhao/jailbreak-classification",
                "description": "Jailbreak prompts classification dataset",
                "splits": ["train", "test"]
            }
        ]

