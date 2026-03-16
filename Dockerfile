FROM python:3.11-slim

WORKDIR /app

# Ensure we have our requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run both the FastAPI server and the LiveKit agent worker in the background
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${PORT:-8080} & python agent.py start"]
