#!/bin/bash
# fix-permissions.sh - Fix permissions for Docker volumes

# Get the current user and group
USER_ID=$(id -u)
GROUP_ID=$(id -g)

echo "Fixing permissions for Docker volumes..."

# Fix permissions for frontend directories
echo "Fixing frontend directory permissions..."
sudo chown -R $USER_ID:$GROUP_ID ./frontend

# Fix permissions for data directory if it exists
if [ -d "./data" ]; then
  echo "Fixing data directory permissions..."
  sudo chown -R $USER_ID:$GROUP_ID ./data
fi

# Create node_modules directory with correct permissions if it doesn't exist
if [ ! -d "./frontend/node_modules" ]; then
    echo "Creating node_modules directory with correct permissions..."
    mkdir -p ./frontend/node_modules
    chmod 755 ./frontend/node_modules
fi

# Create .next directory with correct permissions if it doesn't exist
if [ ! -d "./frontend/.next" ]; then
    echo "Creating .next directory with correct permissions..."
    mkdir -p ./frontend/.next
    chmod 755 ./frontend/.next
fi

echo "All permissions fixed successfully."
echo "You can now run 'docker compose up' to start the application."