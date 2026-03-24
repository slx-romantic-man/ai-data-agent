"""
Export Tool - Exports data to Excel format.
"""
from typing import Any, Dict, Optional
import os
from datetime import datetime
import uuid

from app.agent.tools.base_tool import BaseTool
from app.models.permission import PermissionContext
from app.models.tool import ToolResult


class ExportTool(BaseTool):
    """
    Tool for exporting data to Excel format.
    """

    def __init__(self, export_dir: str = "exports"):
        self._export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    @property
    def name(self) -> str:
        return "export_excel"

    @property
    def description(self) -> str:
        return "Export data to Excel file for download."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Data rows to export",
                    "items": {"type": "object"},
                },
                "filename": {
                    "type": "string",
                    "description": "Export filename (without extension)",
                },
                "format": {
                    "type": "string",
                    "description": "Export format",
                    "enum": ["xlsx", "csv"],
                    "default": "xlsx",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet name for Excel",
                    "default": "Data",
                },
            },
            "required": ["data"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """
        Execute data export.

        Args:
            params: Dict with 'data', 'filename', 'format'
            permission: Permission context (checks export permission)

        Returns:
            ToolResult with export file path
        """
        try:
            # Check export permission
            if not permission.has_permission("export"):
                return self._error("User does not have export permission")

            self.validate_params(params)

            data = params.get("data", [])
            filename = params.get("filename", self._generate_filename())
            format_type = params.get("format", "xlsx")
            sheet_name = params.get("sheet_name", "Data")

            if not data:
                return self._error("No data to export")

            # Export based on format
            if format_type == "xlsx":
                file_path = await self._export_xlsx(data, filename, sheet_name)
            elif format_type == "csv":
                file_path = await self._export_csv(data, filename)
            else:
                return self._error(f"Unsupported format: {format_type}")

            # Calculate row count
            row_count = 0
            if isinstance(data, dict):
                row_count = len(data.get("rows", []))
            else:
                row_count = len(data)

            return self._success(
                data={
                    "file_path": file_path,
                    "filename": os.path.basename(file_path),
                    "row_count": row_count,
                    "format": format_type,
                    "preview": self._generate_preview(data)
                },
                metadata={
                    "export_time": datetime.now().isoformat(),
                    "user_id": permission.user_id,
                },
            )

        except Exception as e:
            return self._error(f"Export failed: {str(e)}")

    async def _export_xlsx(
        self,
        data: Any,
        filename: str,
        sheet_name: str,
    ) -> str:
        """Export data to Excel format."""
        try:
            import pandas as pd
            import json

            # Normalize and Deep Flatten data format
            columns_hint = None
            if isinstance(data, dict):
                input_rows = data.get("rows", [])
                columns_hint = data.get("columns")
            else:
                input_rows = data

            # Deep Flattening Logic
            flattened_rows = []
            for row in input_rows:
                if not isinstance(row, dict):
                    continue
                
                # Check for nested lists to expand
                expand_key = None
                for k, v in row.items():
                    if (isinstance(v, list) and len(v) > 0 and 
                        isinstance(v[0], dict)):
                        expand_key = k
                        break
                
                if expand_key:
                    # Exclude other complex objects from parent
                    base_data = {
                        k: v for k, v in row.items() 
                        if k != expand_key and 
                        not isinstance(v, (dict, list))
                    }
                    for item in row[expand_key]:
                        new_row = base_data.copy()
                        new_row.update(item)
                        flattened_rows.append(new_row)
                else:
                    # Simple flattening 
                    new_row = {}
                    for k, v in row.items():
                        if isinstance(v, (dict, list)):
                            new_row[k] = json.dumps(v, ensure_ascii=False)
                        else:
                            new_row[k] = v
                    flattened_rows.append(new_row)

            if not flattened_rows:
                return await self._export_csv(data, filename)

            # Create DataFrame
            df = pd.DataFrame(flattened_rows)

            # Header handling: If we have a columns hint 
            if columns_hint:
                num_cols = len(df.columns)
                num_hints = len(columns_hint)
                
                if num_hints == num_cols:
                    df.columns = columns_hint
                elif num_hints > num_cols:
                    # Filter known summary headers
                    summary_indices = [i for i, h in enumerate(columns_hint) 
                                       if any(w in h.lower() for w in 
                                              ['summary', '总结', '汇总'])]
                    filtered_hints = [h for i, h in enumerate(columns_hint) 
                                      if i not in summary_indices]
                    
                    if len(filtered_hints) == num_cols:
                        df.columns = filtered_hints
                    elif num_hints - num_cols <= 2: 
                        # Best effort: use last N
                        df.columns = columns_hint[-num_cols:]

            # Generate file path
            file_path = os.path.join(self._export_dir, f"{filename}.xlsx")

            # Export to Excel
            df.to_excel(
                file_path,
                sheet_name=sheet_name,
                index=False,
                engine="openpyxl"
            )
            return file_path

        except ImportError:
            return await self._export_csv(data, filename)

    async def _export_csv(
        self,
        data: Any,
        filename: str,
    ) -> str:
        """Export data to CSV format."""
        import csv
        import json

        # Normalize and Deep Flatten
        columns_hint = None
        if isinstance(data, dict):
            input_rows = data.get("rows", [])
            columns_hint = data.get("columns")
        else:
            input_rows = data

        if not input_rows:
            return ""

        flattened_rows = []
        for row in input_rows:
            if not isinstance(row, dict):
                continue
            
            expand_key = None
            for k, v in row.items():
                if (isinstance(v, list) and len(v) > 0 and 
                    isinstance(v[0], dict)):
                    expand_key = k
                    break
            
            if expand_key:
                base_data = {
                    k: v for k, v in row.items() 
                    if k != expand_key and 
                    not isinstance(v, (dict, list))
                }
                for item in row[expand_key]:
                    new_row = base_data.copy()
                    new_row.update(item)
                    flattened_rows.append(new_row)
            else:
                new_row = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        new_row[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        new_row[k] = v
                flattened_rows.append(new_row)

        if not flattened_rows:
            return ""

        # Generate file path
        file_path = os.path.join(self._export_dir, f"{filename}.csv")

        # Determine columns/headers
        keys = list(flattened_rows[0].keys())
        num_cols = len(keys)
        headers = keys
        
        if columns_hint:
            num_hints = len(columns_hint)
            if num_hints == num_cols:
                headers = columns_hint
            elif num_hints > num_cols:
                summary_indices = [i for i, h in enumerate(columns_hint) 
                                   if any(w in h.lower() for w in 
                                          ['summary', '总结', '汇总'])]
                filtered_hints = [h for i, h in enumerate(columns_hint) 
                                  if i not in summary_indices]
                if len(filtered_hints) == num_cols:
                    headers = filtered_hints
                else:
                    headers = columns_hint[-num_cols:]

        # Write CSV
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in flattened_rows:
                writer.writerow([r.get(k) for k in keys])

        return file_path

    def _generate_filename(self) -> str:
        """Generate unique filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"export_{timestamp}_{unique_id}"

    def _generate_preview(self, data: Any, limit: int = 5) -> list:
        """Generate a small preview of the data for AI review."""
        if isinstance(data, dict):
            rows = data.get("rows", [])
        else:
            rows = data
        
        if not rows or not isinstance(rows, list):
            return []
            
        return rows[:limit]

    def get_file_path(self, filename: str) -> Optional[str]:
        """Get full path for an exported file."""
        file_path = os.path.join(self._export_dir, filename)
        if os.path.exists(file_path):
            return file_path
        return None


# Global export tool instance
_export_tool: Optional[ExportTool] = None


def get_export_tool() -> ExportTool:
    """Get export tool instance."""
    global _export_tool
    if _export_tool is None:
        _export_tool = ExportTool()
    return _export_tool