#!/bin/bash
# fix-docker-compose.sh - Fix Docker Compose file formatting issues

echo "Fixing Docker Compose file formatting..."

# Backup the original file
cp docker-compose.yml docker-compose.yml.bak
echo "Original file backed up to docker-compose.yml.bak"

# Check if the volumes section already contains the proper format
if grep -q "pnpm-store: {}" docker-compose.yml; then
  echo "Docker Compose file already has the correct format."
else
  # Find the line with "pnpm-store:" and modify it
  sed -i.tmp 's/^\(  pnpm-store\):$/\1: {}/' docker-compose.yml
  rm -f docker-compose.yml.tmp
  echo "Updated volumes section to use proper formatting."
fi

echo "Done! You can now run 'docker compose build' to build the image."
