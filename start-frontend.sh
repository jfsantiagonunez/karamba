#!/bin/bash

echo "🎨 Starting Karamba Frontend..."

cd "$(dirname "$0")/frontend" || exit 1

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ node_modules not found. Run setup.sh first!"
    exit 1
fi

echo "✅ Dependencies found"
echo "🚀 Starting Vite dev server..."
echo ""

npm run dev