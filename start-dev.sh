#!/bin/bash
# start-dev.sh — quick dev server startup
set -e

cd "$(dirname "$0")"

echo "🚀 Starting Trestle backend..."
cd backend

# Try venv first
if [ -f .venv/bin/uvicorn ]; then
    .venv/bin/uvicorn app.main:app --reload --port 8000
# Try global uvicorn
elif command -v uvicorn > /dev/null 2>&1; then
    uvicorn app.main:app --reload --port 8000
else
    echo "❌ uvicorn not found. Run: make install"
    exit 1
fi
