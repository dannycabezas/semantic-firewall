"""Script para convertir modelos de Hugging Face a ONNX."""

from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def convert_toxicity_model():
    """Convertir modelo de toxicidad a ONNX."""
    model_name = "unitary/toxic-bert"
    output_path = Path("models/toxicity_model.onnx")

    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()

    # Crear directorio si no existe
    output_path.parent.mkdir(exist_ok=True)

    # Crear dummy input
    dummy_input = tokenizer(
        "test", return_tensors="pt", padding=True, truncation=True, max_length=512
    )

    # Exportar a ONNX
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
    """Convertir modelo de PII a ONNX."""
    # Usar un modelo de NER o crear uno personalizado
    # Por ahora, puedes usar un modelo de clasificación de texto
    model_name = "microsoft/deberta-v3-base"
    output_path = Path("models/pii_model.onnx")

    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # Nota: Este es un ejemplo, necesitarías un modelo específico para PII
    # o entrenar uno personalizado

    print(f"PII model conversion - placeholder")
    print("For PII detection, consider using:")
    print("1. spaCy NER models")
    print("2. Custom trained model")
    print("3. Presidio (Microsoft's PII detection library)")


if __name__ == "__main__":
    print("Converting models to ONNX...")
    convert_toxicity_model()
    convert_pii_model()  # Descomentar cuando tengas un modelo de PII
    print("Done!")
