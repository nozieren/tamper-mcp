FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/ data/

# Set the PORT environment variable (default for Cloud Run)
ENV PORT=8000
EXPOSE $PORT

# Start the SSE server using Uvicorn
CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT}"]
