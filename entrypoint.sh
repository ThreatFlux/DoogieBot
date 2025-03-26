#!/bin/bash
set -e

# Run database migrations
run_migrations() {
    echo "Running database migrations..."
    cd /app/backend
    python -m alembic upgrade head
    
    echo "Database migrations completed."
}

# Function to start the backend
start_backend() {
    echo "Starting backend server..."
    cd /app/backend
    # Use a single worker with memory limits to prevent crashes
    # Set PYTHONMALLOC=debug to help catch memory issues
    export PYTHONMALLOC=debug
    # Set memory limits
    export PYTHONWARNINGS=always
    # Use a single worker with memory limits
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload --workers 1 --timeout-keep-alive 300 --timeout-graceful-shutdown 300 --log-level debug --limit-concurrency 20 --backlog 50 &
    BACKEND_PID=$!
    echo "Backend server started with PID: $BACKEND_PID"
}

# Function to prepare frontend dependencies
prepare_frontend() {
    cd /app/frontend
    
    # Configure pnpm to use a specific store directory with proper permissions
    echo "Configuring pnpm store..."
    pnpm config set store-dir /app/.pnpm-store
    
    # Check if we have write permissions
    if [ ! -w "." ] || [ ! -w "/app/.pnpm-store" ]; then
        echo "Warning: Permission issues detected. Attempting to fix..."
        mkdir -p node_modules .next
    fi
    
    # Install frontend dependencies if needed
    if [ ! -d "node_modules/.bin" ]; then
        echo "Installing frontend dependencies..."
        # Use --shamefully-hoist for better compatibility in Docker
        # Use --no-strict-peer-dependencies to avoid peer dependency issues
        pnpm install --shamefully-hoist --no-strict-peer-dependencies
    else
        echo "Frontend dependencies already installed."
    fi
}

# Function to start the frontend
start_frontend() {
    echo "Starting frontend server..."
    cd /app/frontend
    
    # Start Next.js development server with turbo mode
    NODE_OPTIONS="--max_old_space_size=4096" pnpm dev --turbo &
    FRONTEND_PID=$!
    echo "Frontend server started with PID: $FRONTEND_PID"
}

# Run migrations
run_migrations

# Prepare frontend before starting services
prepare_frontend

# Start services
start_backend
start_frontend

# Handle shutdown
shutdown() {
    echo "Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill -TERM $BACKEND_PID
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill -TERM $FRONTEND_PID
    fi
    exit 0
}

# Trap SIGTERM and SIGINT
trap shutdown SIGTERM SIGINT

# Keep the container running
echo "All services started. Container is now running..."
wait