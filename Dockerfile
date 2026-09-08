FROM python:3.12-slim

WORKDIR /app

# Install git (required if repositories or packages need VCS)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (layer-cached)
COPY backend/requirements.txt backend_requirements.txt
COPY agent/requirements.txt agent_requirements.txt
RUN pip install --no-cache-dir -r backend_requirements.txt -r agent_requirements.txt

# Copy project files and install editable workspace
COPY . .
RUN pip install -e .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
