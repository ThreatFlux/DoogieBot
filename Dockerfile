# Stage 0: Base image
FROM python:3.12-slim AS base

# User configuration with defaults
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USER_NAME=appuser

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with configurable UID/GID
RUN groupadd -g ${GROUP_ID} ${USER_NAME} && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash -m ${USER_NAME} && \
    mkdir -p /app && \
    chown -R ${USER_ID}:${GROUP_ID} /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Stage 1: Builder stage for backend
FROM base AS backend-builder

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt /app/backend/

# Install Python dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r backend/requirements.txt

# Stage 2: Builder stage for frontend
FROM base AS frontend-builder

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy frontend package files
COPY frontend/package.json frontend/pnpm-lock.yaml* /app/frontend/

# Install frontend dependencies
WORKDIR /app/frontend
RUN pnpm install

# Temporarily move node_modules out of the way
RUN mv /app/frontend/node_modules /tmp/node_modules

# Copy frontend code (will respect .dockerignore for node_modules)
WORKDIR /app
COPY frontend/ /app/frontend/

# Restore node_modules
RUN rm -rf /app/frontend/node_modules && \
    mv /tmp/node_modules /app/frontend/node_modules

# Build frontend for production
WORKDIR /app/frontend
RUN NODE_ENV=production pnpm run build

# Stage 3: Test stage
FROM backend-builder AS test

# Install test dependencies
RUN pip install pytest pytest-cov black pylint mypy

# Copy backend code and test files
COPY backend/ /app/backend/
COPY tests/ /app/tests/

# Set test entrypoint
ENTRYPOINT ["pytest"]
CMD ["backend/tests"]

# Stage 4: Development stage
FROM base AS development

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy backend dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Install development tools
RUN pip install pylint black isort pytest pytest-cov bandit

# Create test directories and config files
RUN mkdir -p /app/backend/tests && \
    echo 'exclude_dirs: ["/venv", "/tests"]' > /app/backend/bandit.yaml

# Copy entrypoint scripts
COPY entrypoint.sh /app/
COPY entrypoint.prod.sh /app/
RUN chmod +x /app/entrypoint.sh && \
    chmod +x /app/entrypoint.prod.sh

# Ensure directories exist with correct permissions
RUN mkdir -p /app/frontend/node_modules /app/frontend/.next && \
    mkdir -p /app/.pnpm-store && \
    chown -R ${USER_ID}:${GROUP_ID} /app

# Environment variables for development
ENV NODE_ENV=development \
    FASTAPI_ENV=development \
    PNPM_HOME=".local/share/pnpm"

# Add pnpm to PATH
ENV PATH="${PNPM_HOME}:${PATH}"

# Switch to configured user
USER ${USER_ID}:${GROUP_ID}

# Development-specific command
CMD ["/app/entrypoint.sh"]

# Stage 5: Production stage
FROM base AS production

# Build arguments for metadata
ARG BUILD_DATE
ARG VERSION=1.0.0

# Add metadata with correct author information
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="Mike Reeves" \
      org.opencontainers.image.url="https://github.com/TOoSmOotH/DoogieBot" \
      org.opencontainers.image.source="https://github.com/TOoSmOotH/DoogieBot" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.vendor="TOoSmOotH" \
      org.opencontainers.image.title="DoogieBot" \
      org.opencontainers.image.description="DoogieBot"

# Set working directory
WORKDIR /app

# Install Node.js and pnpm
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    npm install -g pnpm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy backend dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy frontend build from builder
COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/public /app/frontend/public
COPY --from=frontend-builder /app/frontend/node_modules /app/frontend/node_modules
COPY frontend/package.json frontend/next.config.js /app/frontend/

# Copy backend code
COPY backend/ /app/backend/
RUN chown -R ${USER_ID}:${GROUP_ID} /app/backend

# Copy entrypoint scripts
COPY entrypoint.prod.sh /app/
RUN chmod +x /app/entrypoint.prod.sh && \
    chown ${USER_ID}:${GROUP_ID} /app/entrypoint.prod.sh

# Ensure frontend build files have correct ownership
RUN chown -R ${USER_ID}:${GROUP_ID} /app/frontend/.next && \
    chown -R ${USER_ID}:${GROUP_ID} /app/frontend/public && \
    chown -R ${USER_ID}:${GROUP_ID} /app/frontend/node_modules

# Environment variables for production
ENV NODE_ENV=production \
    FASTAPI_ENV=production

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose ports
EXPOSE 3000 8000

# Switch to configured user
USER ${USER_ID}:${GROUP_ID}

# Run the application
ENTRYPOINT ["/app/entrypoint.prod.sh"]
