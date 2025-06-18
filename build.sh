#!/usr/bin/env bash
# Build script for Render deployment
# This runs during the build phase before starting the app

set -e  # Exit on error

echo "=== Starting build process ==="

# Install dependencies
echo "Installing dependencies with UV..."
uv sync --frozen

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

echo "=== Build complete! ==="