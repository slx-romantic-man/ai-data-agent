"""
Approval API endpoints for human-in-the-loop workflow.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from app.models.user import UserContext
from app.api.dependencies import get_user_context, get_permission_context
from app.models.permission import PermissionContext
from app.agent.graph import create_graph
from app.utils.logger import get_logger

router = APIRouter(prefix="/approval", tags=["approval"])
logger = get_logger(__name__)


@router.get("/pending/{thread_id}")
async def get_pending_approval(
    thread_id: str,
    user: UserContext = Depends(get_user_context),
    permission: PermissionContext = Depends(get_permission_context),
) -> Dict[str, Any]:
    """Get pending approval task for a thread."""
    try:
        graph = await create_graph(permission)
        config = {"configurable": {"thread_id": thread_id}}

        state = await graph.aget_state(config)

        if not state.next:
            return {"status": "no_pending", "message": "无待审批任务"}

        return {
            "status": "pending",
            "thread_id": thread_id,
            "next_node": state.next[0] if state.next else None,
            "plan": state.values.get("plan", []),
            "current_step": state.values.get("current_step", 0)
        }
    except Exception as e:
        logger.error(f"Get pending approval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/approve")
async def approve_execution(
    thread_id: str,
    user: UserContext = Depends(get_user_context),
    permission: PermissionContext = Depends(get_permission_context),
) -> Dict[str, Any]:
    """Approve and resume execution."""
    try:
        graph = await create_graph(permission)
        config = {"configurable": {"thread_id": thread_id}}

        # Resume with None input
        result = None
        async for event in graph.astream(None, config, stream_mode="updates"):
            result = event

        return {"status": "approved", "thread_id": thread_id, "result": result}
    except Exception as e:
        logger.error(f"Approve execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{thread_id}/reject")
async def reject_execution(
    thread_id: str,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Reject execution and clear state."""
    try:
        # Simply return rejection status
        # The frontend will handle clearing the session
        return {"status": "rejected", "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Reject execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
