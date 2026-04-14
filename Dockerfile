FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Hugging Face Spaces expects port 7860
EXPOSE 7860

# Environment defaults (override at runtime or via HF secrets)
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT="7860"
ENV API_BASE_URL="https://openrouter.ai/api/v1"
ENV MODEL_NAME="google/gemma-3-27b-it:free"

# Start FastAPI + Gradio server
CMD ["python", "server.py"]
