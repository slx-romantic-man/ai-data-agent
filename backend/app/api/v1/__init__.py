"""API v1 module."""
from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.auth import router as auth_router
from app.api.v1.export import router as export_router
from app.api.v1.api_management import router as api_management_router
from app.api.v1.history import router as history_router
from app.api.v1.user_management import router as user_management_router
from app.api.v1.api_permission import router as api_permission_router


router = APIRouter(prefix="/v1")

router.include_router(chat_router)
router.include_router(auth_router)
router.include_router(export_router)
router.include_router(api_management_router)
router.include_router(history_router)
router.include_router(user_management_router)
router.include_router(api_permission_router)


__all__ = ["router"]