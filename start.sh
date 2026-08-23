#!/bin/bash
set -e

echo "========================================"
echo "  RedSite AI — Mars Site Intelligence"
echo "  Starting up..."
echo "========================================"

# Ensure data directory exists
mkdir -p ./data

# Start FastAPI backend
# FastAPI will serve the static frontend files from /frontend/out
cd backend
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
