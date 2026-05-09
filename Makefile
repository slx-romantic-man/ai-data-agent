# AI Data Agent — Makefile
# Unified task entrypoint for development, testing, and deployment

.PHONY: help install dev lint format typecheck test test-cov clean docker-build docker-up docker-down

# ── Default target ─────────────────────────────────────────────────────────
help:
	@echo "AI Data Agent — Available commands:"
	@echo ""
	@echo "  make install      Install Python dependencies"
	@echo "  make dev          Start development server (backend + frontend)"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Format code with ruff"
	@echo "  make typecheck    Run mypy type checker"
	@echo "  make test         Run pytest test suite"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make security     Run bandit security scan"
	@echo "  make clean        Remove cache files and temp data"
	@echo "  make docker-build Build Docker images"
	@echo "  make docker-up    Start services with Docker Compose"
	@echo "  make docker-down  Stop Docker services"
	@echo ""

# ── Development ────────────────────────────────────────────────────────────
install:
	cd backend && pip install -r requirements.txt
	cd backend && pip install -e ".[dev]"

dev:
	@echo "Starting backend on http://localhost:8000"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Code Quality ───────────────────────────────────────────────────────────
lint:
	cd backend && ruff check app/ scripts/

format:
	cd backend && ruff format app/ scripts/

format-check:
	cd backend && ruff format --check app/ scripts/

typecheck:
	cd backend && mypy app/ --ignore-missing-imports

security:
	cd backend && bandit -r app/ -f json -o bandit-report.json || true
	cd backend && bandit -r app/ -ll

# ── Testing ────────────────────────────────────────────────────────────────
test:
	cd backend && pytest tests/ -v

test-cov:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# ── Cleaning ───────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/bandit-report.json

# ── Docker ─────────────────────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

# ── Database ───────────────────────────────────────────────────────────────
db-init:
	cd backend && python scripts/init_database.py

db-migrate:
	@echo "Alembic migration — coming soon"

# ── Release ────────────────────────────────────────────────────────────────
version:
	@cd backend && python -c "from app import __version__; print(__version__)"
