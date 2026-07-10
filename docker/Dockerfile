# syntax=docker/dockerfile:1.7

# ===================================
# A-share Watchlist Intelligent Analysis System - Docker Image
# ===================================
# Multi-stage build: frontend packaging + backend runtime

FROM node:20-slim AS web-builder

WORKDIR /app/apps/dsa-web

COPY apps/dsa-web/package.json apps/dsa-web/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY apps/dsa-web/ ./
RUN npm run build

# Pin to bookworm: wkhtmltopdf was removed from Debian testing (2025)
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Set timezone to Shanghai
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies (wkhtmltopdf includes wkhtmltoimage, used for Markdown-to-image, Issue #289)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    git \
    gosu \
    wkhtmltopdf \
    fontconfig \
    libjpeg62-turbo \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000)
RUN groupadd -g 1000 dsa && \
    useradd -u 1000 -g dsa -m dsa

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Copy application code
COPY *.py ./
COPY api/ ./api/
COPY data_provider/ ./data_provider/
COPY bot/ ./bot/
COPY src/ ./src/
COPY strategies/ ./strategies/
COPY --from=web-builder /app/static ./static/
COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Verify the bundled AlphaSift adapter from requirements.
RUN python -c "import alphasift.dsa_adapter"

# Ensure data directories exist and grant ownership to non-root user
RUN mkdir -p /app/data /app/logs /app/reports && \
    chown -R dsa:dsa /app && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# efinance writes its search cache (search-cache.json) to the data directory inside its own package,
# which is owned by root by default; when the container runs as non-root user dsa, writes fail with PermissionError,
# causing the efinance data source to fail and degrade on every A-share fetch. Pre-setting the directory owner to dsa fixes this.
# Resolve the path dynamically to avoid hardcoding the Python version directory.
RUN EF_DATA_DIR="$(python -c 'import efinance, pathlib; print(pathlib.Path(efinance.__file__).parent / "data")')" && \
    mkdir -p "$EF_DATA_DIR" && \
    chown -R dsa:dsa "$EF_DATA_DIR"

# Set default environment variable values
ENV PYTHONUNBUFFERED=1
ENV LOG_DIR=/app/logs
ENV DATABASE_PATH=/app/data/stock_analysis.db
# Web/API service
ENV WEBUI_HOST=0.0.0.0
ENV API_PORT=8000

# Expose API port
EXPOSE 8000

# Data volumes (persisted data)
VOLUME ["/app/data", "/app/logs", "/app/reports"]

# Healthcheck (FastAPI mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || curl -f http://localhost:8000/health \
    || python -c "import sys; sys.exit(0)"

# Entrypoint first fixes bind mount directory permissions, then drops privileges to run the app as dsa;
# document that docker-compose exec must explicitly use -u dsa to avoid manual processes writing root-owned files.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["python", "main.py", "--schedule"]
