# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial open-source release with MIT License
- GitHub Actions CI workflow for linting and testing
- GitHub Issue/PR templates
- `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `pyproject.toml` with modern Python packaging configuration
- `Makefile` for unified task management
- Open-source README with badges, architecture diagram, and quick start

### Security

- Removed all hardcoded internal domain names and replaced with placeholders
- Removed proprietary SDK (`common-login-ultra.umd.js`)
- Sanitized all `.env` files with real credentials
- Removed runtime data files (sessions, conversations, user configs)

## [1.0.0] - 2026-05-09

### Added

- LangGraph-based Plan-and-Execute Agent workflow
- Intent Clarification → API Retrieval → Planner → Approval Gateway → Executor → Analyzer pipeline
- SSE streaming for real-time reasoning visualization
- SQLite checkpointer for multi-turn conversation persistence
- Six agent tools: SQL Query, API Fetch, Python Execution, Data Analysis, Excel Export
- Vector-based API retrieval with Qdrant + Embedding
- Three-tier permission control: role-based, row-level filtering, column-level masking
- Manual approval gateway for sensitive operations
- FastAPI backend with JWT authentication
- Vue 3 frontend with Tailwind CSS, Chart.js, Markdown rendering
- Docker Compose deployment with Nginx reverse proxy
- CIA/SSO login integration framework (configurable)

### Technical

- Python 3.12 + FastAPI + SQLAlchemy 2.0 async ORM
- Pydantic v2 for data validation
- LangGraph >= 0.2.0 for agent orchestration
- Qdrant for vector storage
- RestrictedPython for sandboxed code execution
- Circuit breaker pattern for ReAct loop protection
