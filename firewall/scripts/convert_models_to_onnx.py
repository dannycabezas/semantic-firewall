from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def convert_toxicity_model():
    """Convert the toxicity model to ONNX."""
    model_name = "unitary/toxic-bert"
    output_path = Path("models/toxicity_model.onnx")

    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()

    # Create directory if it doesn't exist
    output_path.parent.mkdir(exist_ok=True)

    # Create dummy input
    dummy_input = tokenizer(
        "test", return_tensors="pt", padding=True, truncation=True, max_length=512
    )

    # Export to ONNX
    torch.onnx.export(
        model,
        (dummy_input["input_ids"], dummy_input["attention_mask"]),
        str(output_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        opset_version=18,
    )
    print(f"Model saved to {output_path}")


def convert_pii_model():
    """Convert the PII model to ONNX."""
    # Use a NER model or create a custom one
    # For now, you can use a text classification model
    model_name = "microsoft/deberta-v3-base"
    output_path = Path("models/pii_model.onnx")

    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # Note: This is an example, you would need a specific model for PII
    # or train a custom one

    print(f"PII model conversion - placeholder")
    print("For PII detection, consider using:")
    print("1. spaCy NER models")
    print("2. Custom trained model")
    print("3. Presidio (Microsoft's PII detection library)")


if __name__ == "__main__":
    print("Converting models to ONNX...")
    convert_toxicity_model()
    convert_pii_model()  # Uncomment when you have a PII model
    print("Done!")
