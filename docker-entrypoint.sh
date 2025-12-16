#!/bin/bash
set -e

echo "Setting up database..."

# Run setup script to create tables and populate data
uv run python setup_database.py

echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000