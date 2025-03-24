#!/bin/bash
# fix-all.sh - Fix all Docker environment issues

echo "Fixing all Docker environment issues..."

# Run the fix-permissions script
echo "Step 1: Fixing permissions..."
chmod +x ./scripts/fix-permissions.sh
./scripts/fix-permissions.sh

# Run the fix-docker-compose script
echo "Step 2: Fixing Docker Compose file..."
chmod +x ./scripts/fix-docker-compose.sh
./scripts/fix-docker-compose.sh

echo "All fixes completed successfully!"
echo "You can now run 'docker compose build' followed by 'docker compose up' to start the application."
echo ""
echo "If you still encounter issues, please check the documentation in docs/docker-permissions-fix.md"
