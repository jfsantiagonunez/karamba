#!/bin/bash

echo "🚀 Starting Karamba Backend..."

cd "$(dirname "$0")/backend" || exit 1

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup.sh first!"
    exit 1
fi

source venv/bin/activate

# Check if in correct directory
if [ ! -f "src/api/main.py" ]; then
    echo "❌ Cannot find api/main.py. Are you in the right directory?"
    exit 1
fi

echo "✅ Virtual environment activated"
echo "🔌 Starting uvicorn server..."
echo ""

cd src
uvicorn api.main:app --reload