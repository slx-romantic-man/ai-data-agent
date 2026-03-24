"""
History API endpoints - User chat history and search.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import UserContext
from app.api.dependencies import get_user_context
from app.services.conversation_service import get_conversation_service
from app.services.user_service import get_user_service
from app.utils.logger import get_logger


router = APIRouter(prefix="/history", tags=["history"])
logger = get_logger()


@router.get("")
async def get_history(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get all conversations for the current user."""
    conversation_service = get_conversation_service()

    conversations = conversation_service.get_conversations(user.user_id)

    return {
        "conversations": conversations,
        "total": len(conversations)
    }


@router.get("/{session_id}")
async def get_conversation(
    session_id: str,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get a specific conversation."""
    conversation_service = get_conversation_service()

    conversation = conversation_service.get_conversation(user.user_id, session_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return conversation


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Delete a conversation."""
    conversation_service = get_conversation_service()

    success = conversation_service.delete_conversation(user.user_id, session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return {"status": "success", "message": "Conversation deleted"}


@router.get("/search/query")
async def search_history(
    keyword: str = Query(..., min_length=1, description="Search keyword"),
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Search user's conversations by keyword."""
    conversation_service = get_conversation_service()

    results = conversation_service.search_conversations(user.user_id, keyword)

    return {
        "keyword": keyword,
        "results": results,
        "total": len(results)
    }