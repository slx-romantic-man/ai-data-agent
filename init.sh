#!/bin/bash
set -e

echo "🚀 AI-Data-Agent v4.2 - Environment Initialization Script"
echo "========================================================"

# Check Python version
echo "📌 Checking Python version..."
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"

# Check pip
echo "📌 Checking pip..."
if ! command -v pip &> /dev/null; then
    echo "❌ pip not found. Please install pip"
    exit 1
fi
echo "✅ pip available"

# Check curl
echo "📌 Checking curl..."
if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl"
    exit 1
fi
echo "✅ curl available"

# Check if .env exists and has required keys
echo ""
echo "📌 Checking .env configuration..."
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "❌ Please configure your LLM_API_KEY in .env before running this script"
    exit 1
fi

if ! grep -q "LLM_API_KEY=" .env || grep -q "LLM_API_KEY=$" .env || grep -q "LLM_API_KEY=\"\"" .env; then
    echo "❌ LLM_API_KEY not configured in .env. Please set it before running this script"
    exit 1
fi
echo "✅ .env configuration valid"

# Check if port 8002 is available
echo ""
echo "📌 Checking port 8002 availability..."
if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":8002.*LISTEN"; then
    echo "⚠️  Port 8002 is already in use. Attempting to free it..."
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 2
    if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":8002.*LISTEN"; then
        echo "❌ Port 8002 still in use. Please manually stop the process"
        exit 1
    fi
fi
echo "✅ Port 8002 available"

# Create/activate virtual environment
echo ""
echo "📦 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ Cannot find virtual environment activation script"
    exit 1
fi
echo "✅ Virtual environment activated"

# Navigate to backend directory
cd backend

# Install Python dependencies
echo ""
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo "✅ Dependencies installed"

# Start backend server
echo ""
echo "🔥 Starting backend server on port 8002..."
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload &
SERVER_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8002/docs > /dev/null 2>&1; then
        echo ""
        echo "✅ Server is ready! API docs: http://localhost:8002/docs"
        echo "✅ Frontend: Open frontend/index.html in browser"
        echo ""
        echo "🎯 Application is now in TESTABLE STATE"
        echo "📝 Server PID: $SERVER_PID"
        echo ""
        echo "To stop the server: kill $SERVER_PID"
        exit 0
    fi
    sleep 1
done

echo ""
echo "❌ Server failed to start within 30 seconds"
echo "Check backend/logs/app.log for details"
kill $SERVER_PID 2>/dev/null || true
exit 1
