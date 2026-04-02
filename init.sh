#!/bin/bash
set -e

echo "🚀 AI-Data-Agent v4.2 - Environment Initialization Script"
echo "========================================================"
echo "📋 Purpose: Zero-Token environment bootstrap for multi-round context memory fix project"
echo ""

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

# Check curl for health checks
echo "📌 Checking curl..."
if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl for health checks"
    exit 1
fi
echo "✅ curl available"

# Check .env configuration
echo ""
echo "📌 Checking .env configuration..."
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "❌ Please configure your LLM_API_KEY in .env before running this script"
    echo "   Required keys: LLM_API_KEY, DATABASE_URL (optional)"
    exit 1
fi

if ! grep -q "LLM_API_KEY=" .env || grep -q "LLM_API_KEY=$" .env || grep -q "LLM_API_KEY=\"\"" .env; then
    echo "❌ LLM_API_KEY not configured in .env. Please set it before running this script"
    exit 1
fi
echo "✅ .env configuration valid"

# Check port 8002 availability
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

# Navigate to backend directory
cd backend

# Check and install Python dependencies
echo ""
echo "📦 Checking backend dependencies..."
MISSING_DEPS=0
python -c "import fastapi, uvicorn, langchain, langgraph, sqlalchemy, openai, qdrant_client, sentence_transformers" 2>/dev/null
if [ $? -ne 0 ]; then
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo "⚠️  Missing dependencies detected. Installing..."
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed successfully"
else
    echo "✅ All dependencies already installed"
fi

# Initialize database and vector store (if needed)
echo ""
echo "🔧 Checking database initialization..."
if [ ! -f "data/checkpoints.db" ]; then
    echo "⚠️  Database not found. Will be auto-created on first startup"
fi
echo "✅ Database check complete"

# Start backend server
echo ""
echo "🔥 Starting backend server on port 8002..."
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload > ../logs/init_server.log 2>&1 &
SERVER_PID=$!

# Wait for server to be ready with exponential backoff
echo "⏳ Waiting for server to be ready..."
MAX_WAIT=40
WAIT_INTERVAL=1
for i in $(seq 1 $MAX_WAIT); do
    if curl -s http://localhost:8002/docs > /dev/null 2>&1; then
        echo ""
        echo "✅ Backend server ready!"
        echo "   API docs: http://localhost:8002/docs"
        echo "   Health: http://localhost:8002/health"
        echo ""
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo ""
        echo "❌ Server failed to start within $MAX_WAIT seconds"
        echo "   Check logs/init_server.log for details"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    sleep $WAIT_INTERVAL
done

# Frontend information
echo "📱 Frontend:"
echo "   Location: frontend/index.html (static, no build required)"
echo "   Access: Open frontend/index.html directly in browser"
echo "   Or visit: http://localhost:8002 (if backend serves static files)"
echo ""

# Final status
echo "🎯 Application is now in TESTABLE STATE"
echo "📝 Backend PID: $SERVER_PID"
echo "📋 Session memory location: backend/sessions.json"
echo "📊 Vector store: backend/data/qdrant/"
echo ""
echo "To stop server: kill $SERVER_PID"
echo "To monitor logs: tail -f logs/init_server.log"
echo ""

# Save PID for later cleanup
echo "$SERVER_PID" > ../.server_pid

exit 0
