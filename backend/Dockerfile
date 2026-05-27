FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (Docker layer caching: this layer only
# rebuilds if requirements.txt changes, not on every code change)
COPY backend/requirements.txt .
COPY agent/requirements.txt agent_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r agent_requirements.txt

# Copy application code
COPY . .

# Install the workspace packages (app, agent)
RUN pip install -e .

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Start the server
# --host 0.0.0.0 makes it reachable from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
