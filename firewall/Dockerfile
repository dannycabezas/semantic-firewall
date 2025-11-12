FROM python:3.11-slim

# Install system dependencies required for sentence-transformers and torch
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
# Use --no-cache-dir to avoid cache issues
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app
EXPOSE 8080
CMD ["uvicorn", "semantic_firewall:app", "--host", "0.0.0.0", "--port", "8080"]