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

# Function to start the frontend
start_frontend() {
    echo "Starting frontend server..."
    cd /app/frontend
    # Use the --turbo flag for faster refresh and add NODE_OPTIONS to increase memory limit
    NODE_OPTIONS="--max_old_space_size=4096" npm run dev -- --turbo &
    FRONTEND_PID=$!
    echo "Frontend server started with PID: $FRONTEND_PID"
}

# Run migrations
run_migrations

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