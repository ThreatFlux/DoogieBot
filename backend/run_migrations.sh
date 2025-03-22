#!/bin/bash
# Script to run database migrations

cd /app/backend
alembic upgrade head

echo "Database migrations completed successfully!"