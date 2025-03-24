#!/bin/bash
# fix-docker-compose.sh - Fix Docker Compose file formatting issues

echo "Fixing Docker Compose file formatting..."

# Backup the original file
cp docker-compose.yml docker-compose.yml.bak
echo "Original file backed up to docker-compose.yml.bak"

# Replace with the fixed version
cp docker-compose.fixed.yml docker-compose.yml
echo "Docker Compose file replaced with fixed version"

echo "Done! You can now run 'docker compose build' to build the image."
