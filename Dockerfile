# Dockerfile — portable CPNP deployment (works on any Docker host)
#
# BUILD:  docker build -t cpnp .
# RUN:    docker run -p 8000:8000 cpnp
# OPEN:   http://localhost:8000/dashboard
#
# Works on: local Docker, Fly.io, Railway, Google Cloud Run, AWS, Azure,
# DigitalOcean App Platform, or any container host.

FROM python:3.11-slim

# System deps for cryptography wheels (usually prebuilt, but safe to have)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# The server listens on $PORT (default 8000)
ENV PORT=8000
EXPOSE 8000

# Health check so orchestrators know the app is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the server
CMD uvicorn app.server:app --host 0.0.0.0 --port ${PORT}
