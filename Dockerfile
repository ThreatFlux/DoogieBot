# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm, and other dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    python3-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN npm install -g pnpm

# Copy backend requirements first (this rarely changes)
COPY backend/requirements.txt /app/backend/

# Install Python dependencies with cache enabled
RUN pip install -r backend/requirements.txt

# Copy frontend package.json (this rarely changes)
COPY frontend/package.json frontend/pnpm-lock.yaml* /app/frontend/

# Install frontend dependencies
WORKDIR /app/frontend
RUN pnpm install

# Back to app directory
WORKDIR /app

# Create a .gitconfig that doesn't try to use credentials
RUN git config --global user.email "docker@example.com" && \
    git config --global user.name "Docker Container" && \
    git config --global credential.helper store

# Expose ports
EXPOSE 3000 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=development
ENV FASTAPI_ENV=development