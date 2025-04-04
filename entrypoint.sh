#!/bin/bash
set -e

# Ensure required directories exist
ensure_directories() {
    echo "Ensuring required directories exist..."
    mkdir -p /app/backend/db
    mkdir -p /app/backend/indexes
    mkdir -p /app/backend/uploads
    mkdir -p /app/.uv-cache
    
    # Set proper permissions
    chmod -R 755 /app/backend/db
    chmod -R 755 /app/backend/indexes
    chmod -R 755 /app/backend/uploads
    chmod -R 777 /app/.uv-cache # Make UV cache writable for everyone
    
    # Remove .git directory from UV cache if it exists (causing permission errors)
    if [ -d "/app/.uv-cache/sdists-v9/.git" ]; then
        echo "Removing problematic .git directory from UV cache..."
        rm -rf /app/.uv-cache/sdists-v9/.git
    fi
    
    echo "Directories checked and created if needed."
}

# Run database migrations with retry logic
run_migrations() {
    echo "Running database migrations..."
    cd /app/backend
    
    # Create database directory if it doesn't exist
    mkdir -p "$PWD/db"
    touch "$PWD/db/doogie.db"
    chmod 666 "$PWD/db/doogie.db"
    
    # Try to run migrations with retries
    local max_attempts=5
    local attempt=1
    local success=false
    
    while [ $attempt -le $max_attempts ] && [ "$success" = false ]; do
        echo "Attempt $attempt of $max_attempts to run migrations..."
        if uv run alembic upgrade head; then
            success=true
            echo "Database migrations completed successfully."
        else
            echo "Migration attempt $attempt failed. Waiting before retry..."
            sleep 5
            attempt=$((attempt+1))
        fi
    done
    
    if [ "$success" = false ]; then
        echo "ERROR: Failed to run migrations after $max_attempts attempts."
        echo "Will continue startup, but application may not work correctly."
    fi
    
    # Verify database tables exist
    echo "Verifying database tables..."
    if [ -f "db/doogie.db" ]; then
        # Run a simple SQL query to verify the database file exists and has tables
        sqlite3 db/doogie.db "SELECT name FROM sqlite_master WHERE type='table';"
        if ! sqlite3 db/doogie.db ".tables" | grep -q "users"; then
            echo "WARNING: Users table not found in database. Using SQLAlchemy initialization."
            echo "Initializing database schema with SQLAlchemy..."
            # Create a simple script to initialize the database
            cat > init_db.py << EOF
from app.db.base import init_db
init_db()
EOF
            # Run the script
            uv run python init_db.py
            echo "Database initialization completed."
        else
            echo "Database verification successful."
        fi
    else
        echo "WARNING: Database file not found. Using SQLAlchemy initialization."
        echo "Initializing database schema with SQLAlchemy..."
        # Create a simple script to initialize the database
        cat > init_db.py << EOF
from app.db.base import init_db
init_db()
EOF
        # Run the script
        uv run python init_db.py
        echo "Database initialization completed."
    fi
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
    # Use a single worker with memory limits, run uvicorn directly in foreground
    uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --workers 1 --timeout-keep-alive 300 --timeout-graceful-shutdown 300 --log-level debug --limit-concurrency 20 --backlog 50
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
