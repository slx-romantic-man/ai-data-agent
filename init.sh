#!/bin/bash
set -e

echo "🚀 AI-Data-Agent v4 - Environment Initialization Script"
echo "========================================================"

# Check Python version
echo "📌 Checking Python version..."
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION detected"

# Navigate to backend directory
cd backend

# Install Python dependencies
echo ""
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt --quiet

# Check if .env exists
cd ..
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "⚠️  Please configure your LLM_API_KEY in .env before starting the server"
fi

# Start backend server
echo ""
echo "🔥 Starting backend server on port 8002..."
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload &
SERVER_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8002/docs > /dev/null 2>&1; then
        echo "✅ Server is ready! API docs: http://localhost:8002/docs"
        echo "✅ Frontend: Open frontend/index.html in browser"
        echo ""
        echo "🎯 Application is now in TESTABLE STATE"
        echo "📝 Server PID: $SERVER_PID"
        exit 0
    fi
    sleep 1
done

echo "❌ Server failed to start within 30 seconds"
kill $SERVER_PID 2>/dev/null || true
exit 1
