#!/bin/bash
set -e

# Install backend dependencies
install_backend_deps() {
    echo "Installing backend dependencies..."
    cd /app/backend
    pip install -r requirements.txt
    echo "Backend dependencies installed."
}

# Install frontend dependencies
install_frontend_deps() {
    echo "Installing frontend dependencies..."
    cd /app/frontend
    npm install
    echo "Frontend dependencies installed."
}

# Run database migrations
run_migrations() {
    echo "Running database migrations..."
    cd /app/backend
    python -m alembic upgrade head
    echo "Database migrations completed."
}

# Build frontend for production
build_frontend() {
    echo "Building frontend for production..."
    cd /app/frontend
    npm run build
    echo "Frontend build completed."
}

# Function to start the backend in production mode
start_backend() {
    echo "Starting backend server in production mode..."
    cd /app/backend
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 300 &
    BACKEND_PID=$!
    echo "Backend server started with PID: $BACKEND_PID"
}

# Function to start the frontend in production mode
start_frontend() {
    echo "Starting frontend server in production mode..."
    cd /app/frontend
    npm run start &
    FRONTEND_PID=$!
    echo "Frontend server started with PID: $FRONTEND_PID"
}

# Install dependencies
install_backend_deps
install_frontend_deps

# Run migrations
run_migrations

# Build frontend for production
build_frontend

# Start services in production mode
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
echo "All services started in production mode. Container is now running..."
wait