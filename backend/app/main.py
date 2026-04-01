"""
AI Data Agent - FastAPI Main Entry Point.

Enterprise-level AI data analysis agent system supporting:
- Natural language database queries
- Three-tier permission control (role/row/column level)
- Intelligent SQL generation and execution
- Data analysis and visualization
- Excel export
"""
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.config.llm_config import get_llm
from app.api.v1 import router as v1_router
from app.access.database import get_db, close_db
from app.agent.router import get_tool_router
from app.utils.logger import get_logger, setup_logger
from app.utils.exceptions import AIAgentException


# Setup logger
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        db = await get_db()
        logger.info("Database connection established")

        # Initialize tool router
        logger.info("Initializing tool router...")
        tool_router = await get_tool_router()
        logger.info(f"Tools registered: {list(tool_router.list_tools().keys())}")

        # Initialize LLM client
        logger.info("Initializing LLM client...")
        logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
        logger.info(f"LLM Model: {settings.LLM_MODEL}")
        llm = get_llm()
        logger.info(f"LLM client initialized: {llm.__class__.__name__}")

        # Build API vector index
        logger.info("Building API vector index...")
        from app.services.api_retrieval_service import get_api_retrieval_service
        from app.services.api_permission_service import get_api_permission_service
        retrieval_service = get_api_retrieval_service()
        permission_service = await get_api_permission_service()
        all_apis = await permission_service.get_all_apis()
        for api in all_apis:
            await retrieval_service.build_index_for_api(api.id)
        logger.info(f"API vector index built: {retrieval_service.get_indexed_count()} APIs indexed")

        logger.info(f"{settings.APP_NAME} started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_db()
    logger.info("Database connection closed")
    logger.info(f"{settings.APP_NAME} shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## AI Data Agent API

Enterprise-level AI data analysis agent system.

### Features
- **Natural Language Queries**: Query databases using natural language
- **Permission Control**: Three-tier permission system (role/row/column)
- **SQL Generation**: Intelligent and safe SQL generation
- **Data Analysis**: Automated data analysis and insights
- **Export**: Excel and CSV export capabilities

### Authentication
Use the `/api/v1/auth/login` endpoint to get an access token.
Include the token in the `Authorization` header as `Bearer <token>`.

### Demo Credentials
- Admin: admin / admin123
- Manager: manager1 / manager123
- Employee: user1 / user123
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(AIAgentException)
async def ai_agent_exception_handler(request: Request, exc: AIAgentException):
    """Handle custom AI Agent exceptions."""
    logger.error(f"AI Agent exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    import traceback
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": str(exc) if settings.DEBUG else None,
        },
    )


# Include API routers
app.include_router(v1_router, prefix="/api")

# Mount static files for frontend - MUST be after router inclusion
import os
from pathlib import Path

# Get frontend directory path
frontend_path = Path(__file__).parent.parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Frontend static files mounted at /frontend from {frontend_path}")
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns the current status of the application.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    Returns basic API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    logger.info(f"Response: {request.method} {request.url} - Status: {response.status_code}")

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )