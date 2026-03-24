"""
Export API endpoints.
"""
from typing import Dict, Any
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.models.user import UserContext
from app.agent.tools.export_tool import get_export_tool, ExportTool
from app.api.dependencies import get_user_context
from app.utils.logger import get_logger


router = APIRouter(prefix="/export", tags=["export"])
logger = get_logger()


@router.get("/{filename}")
async def download_export(
    filename: str,
    user: UserContext = Depends(get_user_context),
) -> FileResponse:
    """
    Download exported file.

    - **filename**: Export filename (e.g., export_20240101_abc123.xlsx)
    """
    try:
        export_tool = get_export_tool()

        # Get file path
        file_path = export_tool.get_file_path(filename)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )

        # Determine media type
        if filename.endswith(".xlsx"):
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.endswith(".csv"):
            media_type = "text/csv"
        else:
            media_type = "application/octet-stream"

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}",
        )


@router.post("")
async def create_export(
    data: Dict[str, Any],
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Create a new export from data.

    Request body:
    - **data**: Array of data rows to export
    - **format**: Export format (xlsx or csv, default: xlsx)
    - **filename**: Optional custom filename
    """
    try:
        # Check export permission
        if "export" not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Export permission required",
            )

        export_tool = get_export_tool()

        # Import permission context
        from app.models.permission import PermissionContext
        permission = PermissionContext(
            user_id=user.user_id,
            role=user.role,
            permissions=["export"],
        )

        # Execute export
        result = await export_tool.execute(
            params=data,
            permission=permission,
        )

        if result.status != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Export failed",
            )

        return {
            "status": "success",
            "filename": result.data.get("filename"),
            "download_url": f"/api/v1/export/{result.data.get('filename')}",
            "row_count": result.data.get("row_count"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating export: {str(e)}",
        )


@router.get("")
async def list_exports(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """List available exports."""
    try:
        export_tool = get_export_tool()
        export_dir = export_tool._export_dir

        files = []
        if os.path.exists(export_dir):
            for filename in os.listdir(export_dir):
                file_path = os.path.join(export_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        "filename": filename,
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "download_url": f"/api/v1/export/{filename}",
                    })

        # Sort by created_at descending
        files.sort(key=lambda x: x["created_at"], reverse=True)

        return {
            "files": files,
            "total": len(files),
        }

    except Exception as e:
        logger.error(f"Export list error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing exports: {str(e)}",
        )