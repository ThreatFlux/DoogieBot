#!/bin/bash
set -e

# Ensure required directories exist
ensure_directories() {
    echo "Ensuring required directories exist..."
    # Use the persistent data directory for db and indexes
    mkdir -p /app/data/db
    mkdir -p /app/data/indexes
    mkdir -p /app/backend/uploads # Uploads can stay within backend for now
    
    # Set proper permissions for data directories
    chmod -R 777 /app/data/db
    chmod -R 777 /app/data/indexes
    chmod -R 755 /app/backend/uploads
    
    # Create a new UV cache directory with proper permissions from the start
    mkdir -p /tmp/uv-cache-new
    chmod 777 /tmp/uv-cache-new
    
    # Set UV to use our new cache directory
    export UV_CACHE_DIR=/tmp/uv-cache-new
    
    echo "Directories checked and created if needed."
    echo "UV cache directory set to: $UV_CACHE_DIR"
}

# Run database migrations with retry logic
run_migrations() {
    echo "Running database migrations..."
    cd /app/backend # Ensure we are in the correct directory for alembic.ini
    
    # Ensure the database file exists in the persistent location
    DB_FILE="/app/data/db/doogie.db"
    mkdir -p "$(dirname "$DB_FILE")"
    touch "$DB_FILE"
    chmod 666 "$DB_FILE"
    echo "Ensured database file exists at $DB_FILE"
    
    # Ensure UV environment variable is exported here too
    export UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/uv-cache-new}
    echo "Using UV cache directory: $UV_CACHE_DIR for migrations"
    
    # 1. Autogenerate migration based on current models vs current DB state
    echo "Autogenerating migration script..."
    if UV_CACHE_DIR=$UV_CACHE_DIR uv run alembic revision --autogenerate -m "Auto-generated migration on startup"; then
        echo "Migration script generated successfully (or no changes detected)."
    else
        echo "WARNING: Failed to autogenerate migration script. Proceeding with upgrade anyway."
    fi
    
    # 2. Apply all migrations (including the one potentially just generated)
    echo "Applying database migrations..."
    local max_attempts=5
    local attempt=1
    local success=false
    
    while [ $attempt -le $max_attempts ] && [ "$success" = false ]; do
        echo "Attempt $attempt of $max_attempts to apply migrations..."
        # Run upgrade head
        if UV_CACHE_DIR=$UV_CACHE_DIR uv run alembic upgrade head; then
            success=true
            echo "Database migrations applied successfully."
        else
            echo "Migration attempt $attempt failed. Waiting before retry..."
            # Print UV cache directory info for debugging
            echo "UV cache directory contents:"
            ls -la $UV_CACHE_DIR || echo "Cannot list UV cache directory"
            sleep 5
            attempt=$((attempt+1))
        fi
    done
    
    if [ "$success" = false ]; then
        echo "ERROR: Failed to apply migrations after $max_attempts attempts."
        echo "Will continue startup, but application may not work correctly."
    fi
    
    # Verification step is less critical now as autogenerate + upgrade should handle it
    # but we can keep a basic check
    echo "Verifying database connection..."
    if [ -f "$DB_FILE" ]; then
        # Run a simple SQL query to verify connection
        if sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='users';" | grep -q "users"; then
            echo "Database verification successful (users table found)."
        else
            echo "WARNING: Users table not found after migrations. Check Alembic configuration and model definitions."
        fi
    else
        echo "ERROR: Database file $DB_FILE not found after migration attempt."
    fi
}

# Function to start the backend
start_backend() {
    echo "Starting backend server..."
    cd /app/backend
    
    # Ensure UV environment variable is set here too
    export UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/uv-cache-new}
    echo "Using UV cache directory: $UV_CACHE_DIR for backend"
    
    # Use a single worker with memory limits to prevent crashes
    # Set PYTHONMALLOC=debug to help catch memory issues
    export PYTHONMALLOC=debug
    # Set memory limits
    export PYTHONWARNINGS=always
    # Use a single worker with memory limits, run uvicorn directly in foreground
    UV_CACHE_DIR=$UV_CACHE_DIR uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --workers 1 --timeout-keep-alive 300 --timeout-graceful-shutdown 300 --log-level debug --limit-concurrency 20 --backlog 50
    # No backgrounding (&) or PID needed when running in foreground
    echo "Backend server started in foreground."
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
        # mkdir -p node_modules .next # Directory creation moved to Dockerfile
    fi
    
    # Install frontend dependencies if needed
    # Check for a common binary instead of the whole .bin directory
    if [ ! -f "node_modules/.bin/next" ]; then 
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

# Ensure required directories exist
ensure_directories

# Run migrations
run_migrations

# Add a delay to ensure database is ready
echo "Waiting for 3 seconds to ensure database is ready..."
sleep 3

# Prepare frontend before starting services
prepare_frontend # Re-added this call

# Start frontend in background first
start_frontend
echo "Waiting 5 seconds for frontend to potentially build..."
sleep 5

# Start backend in foreground (this will block until stopped)
start_backend

# Shutdown handling might need adjustment if backend runs foreground
# The trap should still work if the container receives SIGTERM/SIGINT
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

# No need for 'wait' when backend runs in foreground
echo "Backend running in foreground. Container will stay alive."
