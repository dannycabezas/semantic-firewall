FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Agregar transformers y scipy para los modelos
RUN pip install --no-cache-dir transformers torch scipy

# Copy application code
COPY . /app

# Crear directorio para modelos
RUN mkdir -p /app/models

# Los modelos ONNX deben copiarse aquí o descargarse en runtime
# COPY models/*.onnx /app/models/

EXPOSE 8080
CMD ["uvicorn", "semantic_firewall:app", "--host", "0.0.0.0", "--port", "8080"]