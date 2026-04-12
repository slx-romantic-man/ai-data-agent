#!/bin/bash
##############################################################################
# AI-Data-Agent v4.3 — Performance Optimization Project
# Zero-Token Environment Bootstrap Script
#
# Purpose: Any AI coding agent runs `bash init.sh` to reach TESTABLE STATE.
# Guarantees: Python deps installed → Qdrant lock cleared → server started
#             → health check passed → port 8002 ready.
#
# Exit codes:
#   0 = success (application is testable)
#   1 = fatal error (dependency / config / port issue)
##############################################################################
set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOG_DIR="${PROJECT_ROOT}/logs"
BACKEND_LOG_DIR="${BACKEND_DIR}/logs"
SERVER_PORT=8002
PID_FILE="${PROJECT_ROOT}/.server_pid"
SERVER_LOG="${LOG_DIR}/init_server.log"
MAX_WAIT=60
HEALTH_ENDPOINT="http://localhost:${SERVER_PORT}/docs"

# ── Colours (safe for non-tty) ───────────────────────────────────────────────
if [ -t 1 ]; then
  GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; NC=''
fi
ok()   { echo -e "${GREEN}✅ $*${NC}"; }
fail() { echo -e "${RED}❌ $*${NC}"; exit 1; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
info() { echo "📌 $*"; }

# ── Cleanup trap ─────────────────────────────────────────────────────────────
cleanup_on_error() {
  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    echo ""
    warn "init.sh exited with code ${exit_code}. Cleaning up..."
    # Kill server if we started one
    if [ -f "${PID_FILE}" ]; then
      local pid
      pid=$(cat "${PID_FILE}" 2>/dev/null || true)
      if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}" 2>/dev/null || true
        warn "Killed server process ${pid}"
      fi
      rm -f "${PID_FILE}"
    fi
  fi
}
trap cleanup_on_error EXIT

echo ""
echo "🚀 AI-Data-Agent v4.3 — Performance Optimization Bootstrap"
echo "============================================================"
echo ""

# ── 1. Python Detection ─────────────────────────────────────────────────────
info "Checking Python version..."
PYTHON_CMD=""
for candidate in python3 python; do
  if command -v "${candidate}" &>/dev/null; then
    PYTHON_CMD="${candidate}"
    break
  fi
done
[ -z "${PYTHON_CMD}" ] && fail "Python not found. Please install Python 3.8+"

PYTHON_VERSION=$("${PYTHON_CMD}" --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

if [ "${PYTHON_MAJOR}" -lt 3 ] || { [ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -lt 8 ]; }; then
  fail "Python 3.8+ required, found ${PYTHON_VERSION}"
fi
ok "Python ${PYTHON_VERSION} detected (${PYTHON_CMD})"

# ── 2. pip Detection ────────────────────────────────────────────────────────
info "Checking pip..."
PIP_CMD=""
for candidate in pip3 pip; do
  if command -v "${candidate}" &>/dev/null; then
    PIP_CMD="${candidate}"
    break
  fi
done
[ -z "${PIP_CMD}" ] && fail "pip not found. Please install pip"
ok "pip available (${PIP_CMD})"

# ── 3. curl Detection ───────────────────────────────────────────────────────
info "Checking curl..."
command -v curl &>/dev/null || fail "curl not found. Required for health checks"
ok "curl available"

# ── 4. .env Configuration ───────────────────────────────────────────────────
info "Checking .env configuration..."
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
  if [ -f "${PROJECT_ROOT}/.env.example" ]; then
    warn ".env not found. Copying from .env.example..."
    cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
    fail "Please configure LLM_API_KEY in .env before re-running"
  else
    fail ".env and .env.example both missing"
  fi
fi

# Validate LLM_API_KEY is set and non-empty
LLM_KEY=$(grep -E '^LLM_API_KEY=' "${PROJECT_ROOT}/.env" | head -1 | cut -d= -f2-)
if [ -z "${LLM_KEY}" ] || [ "${LLM_KEY}" = '""' ] || [ "${LLM_KEY}" = "''" ]; then
  fail "LLM_API_KEY not configured in .env"
fi
ok ".env configuration valid (LLM_API_KEY set)"

# ── 5. Log Directories ──────────────────────────────────────────────────────
info "Ensuring log directories exist..."
mkdir -p "${LOG_DIR}" "${BACKEND_LOG_DIR}" "${BACKEND_DIR}/data"
ok "Log directories ready"

# ── 6. Kill Previous Server ─────────────────────────────────────────────────
info "Checking port ${SERVER_PORT} availability..."
if [ -f "${PID_FILE}" ]; then
  OLD_PID=$(cat "${PID_FILE}" 2>/dev/null || true)
  if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
    warn "Killing previous server (PID ${OLD_PID})..."
    kill "${OLD_PID}" 2>/dev/null || true
    sleep 2
  fi
  rm -f "${PID_FILE}"
fi

# Also try to free port if still occupied
if lsof -Pi ":${SERVER_PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
  warn "Port ${SERVER_PORT} still in use. Attempting pkill..."
  pkill -f "uvicorn app.main:app.*${SERVER_PORT}" 2>/dev/null || true
  sleep 2
  if lsof -Pi ":${SERVER_PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
    fail "Port ${SERVER_PORT} still in use. Please manually stop the process"
  fi
fi
ok "Port ${SERVER_PORT} available"

# ── 7. Clear Qdrant Lock Files ──────────────────────────────────────────────
info "Clearing Qdrant lock files (prevent stale lock conflicts)..."
QDRANT_DIR="${BACKEND_DIR}/data/qdrant"
if [ -d "${QDRANT_DIR}" ]; then
  find "${QDRANT_DIR}" -name ".lock" -delete 2>/dev/null || true
  find "${QDRANT_DIR}" -name "*.lock" -delete 2>/dev/null || true
  ok "Qdrant lock files cleared"
else
  ok "Qdrant directory does not exist yet (will be created on startup)"
fi

# ── 8. Install Python Dependencies ──────────────────────────────────────────
info "Checking backend dependencies..."
REQUIREMENTS="${BACKEND_DIR}/requirements.txt"
if [ ! -f "${REQUIREMENTS}" ]; then
  fail "requirements.txt not found at ${REQUIREMENTS}"
fi

# Quick import check for core packages
MISSING_DEPS=0
"${PYTHON_CMD}" -c "
import fastapi, uvicorn, sqlalchemy, httpx, qdrant_client, sentence_transformers
" 2>/dev/null || MISSING_DEPS=1

if [ "${MISSING_DEPS}" -eq 1 ]; then
  warn "Missing dependencies detected. Installing from requirements.txt..."
  "${PIP_CMD}" install -r "${REQUIREMENTS}" --quiet 2>&1 | tail -5 || {
    warn "Standard install failed, retrying with trusted-host fallback..."
    "${PIP_CMD}" install -r "${REQUIREMENTS}" \
      --trusted-host pypi.org --trusted-host files.pythonhosted.org --quiet || {
      fail "Failed to install Python dependencies"
    }
  }
  ok "Dependencies installed successfully"
else
  ok "All Python dependencies already installed"
fi

# ── 9. Database Check ───────────────────────────────────────────────────────
info "Checking database readiness..."
CHECKPOINT_DB="${BACKEND_DIR}/data/checkpoints.db"
if [ ! -f "${CHECKPOINT_DB}" ]; then
  warn "checkpoints.db not found — will be auto-created on first startup"
else
  ok "checkpoints.db exists"
fi

# ── 10. Start Backend Server ────────────────────────────────────────────────
echo ""
echo "🔥 Starting backend server on port ${SERVER_PORT}..."

cd "${BACKEND_DIR}"
uvicorn app.main:app --host 0.0.0.0 --port "${SERVER_PORT}" --reload \
  > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${PID_FILE}"

# ── 11. Health Check (exponential backoff) ──────────────────────────────────
echo "⏳ Waiting for server to be ready (max ${MAX_WAIT}s)..."
ELAPSED=0
INTERVAL=1

while [ "${ELAPSED}" -lt "${MAX_WAIT}" ]; do
  if curl -s -o /dev/null -w "%{http_code}" "${HEALTH_ENDPOINT}" 2>/dev/null | grep -qE "^(200|307)$"; then
    echo ""
    ok "Backend server ready! (took ~${ELAPSED}s)"
    echo ""
    echo "   📖 API docs : http://localhost:${SERVER_PORT}/docs"
    echo "   💚 Health   : http://localhost:${SERVER_PORT}/health"
    echo "   📝 PID      : ${SERVER_PID}"
    echo ""
    break
  fi

  # Check if process died
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo ""
    fail "Server process died. Check ${SERVER_LOG}"
  fi

  sleep "${INTERVAL}"
  ELAPSED=$((ELAPSED + INTERVAL))

  # Exponential backoff: 1,1,2,2,4,4,...
  if [ "${ELAPSED}" -gt 10 ]; then
    INTERVAL=2
  fi
  if [ "${ELAPSED}" -gt 20 ]; then
    INTERVAL=4
  fi
done

if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
  fail "Server failed to start within ${MAX_WAIT}s. Check ${SERVER_LOG}"
fi

# ── 12. Final Summary ───────────────────────────────────────────────────────
echo "📱 Frontend:"
echo "   Location: frontend/index.html (static, no build required)"
echo "   Access  : Open frontend/index.html directly in browser"
echo ""
echo "🎯 Application is now in TESTABLE STATE"
echo "   Server PID : ${SERVER_PID}"
echo "   Server log : ${SERVER_LOG}"
echo "   Sessions   : backend/sessions.json"
echo "   Vector DB  : backend/data/qdrant/"
echo ""
echo "To stop server : kill ${SERVER_PID}"
echo "To monitor logs: tail -f ${SERVER_LOG}"
echo ""

exit 0
