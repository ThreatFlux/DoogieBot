#!/bin/bash

# Doogie6 Sync Script
# This script syncs the Doogie6 codebase to another machine while
# ignoring installation-specific files like database and index files

# Usage:
# ./sync-doogie.sh [destination] [options]
# Example: ./sync-doogie.sh user@remote-server:/path/to/doogie6 --dry-run

# Default destination if not provided
DESTINATION=${1:-user@remote-server:/path/to/doogie6}

# Check if destination is provided
if [[ "$DESTINATION" == --* ]]; then
  echo "Error: No destination specified"
  echo "Usage: ./sync-doogie.sh [destination] [options]"
  exit 1
fi

# Shift the first argument (destination) so that remaining args are options
shift

# Default options
OPTIONS="-avz --progress"

# Add any additional options passed to the script
OPTIONS="$OPTIONS $@"

# Run rsync with the specified options and exclusions
rsync $OPTIONS \
  --exclude=".git/" \
  --exclude="backend/indexes/*.pkl" \
  --exclude="backend/indexes/*.bin" \
  --exclude="*.db" \
  --exclude="*.sqlite" \
  --exclude="*.sqlite3" \
  --exclude="__pycache__/" \
  --exclude="*.pyc" \
  --exclude="node_modules/" \
  --exclude=".next/" \
  --exclude="uploads/*" \
  --exclude=".env" \
  --exclude=".DS_Store" \
  ./ $DESTINATION

# Exit with rsync's exit code
exit $?