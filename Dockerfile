FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
