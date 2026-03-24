"""
Tool models for Agent tool execution.
"""
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Tool types."""
    SQL_QUERY = "sql_query"
    API_FETCH = "api_fetch"
    DATA_ANALYSIS = "data_analysis"
    EXPORT_EXCEL = "export_excel"


class ToolStatus(str, Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ToolInput(BaseModel):
    """Tool input model."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class ToolResult(BaseModel):
    """Tool execution result."""
    tool_name: str
    status: ToolStatus = ToolStatus.SUCCESS
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolStep(BaseModel):
    """A single step in the execution plan."""
    step_id: int
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[int] = Field(default_factory=list, description="Steps this depends on")


class ToolExecutionPlan(BaseModel):
    """Full tool execution plan."""
    steps: List[ToolStep] = Field(default_factory=list)
    parallel: bool = False


class SQLQueryInput(BaseModel):
    """Input for SQL query tool."""
    sql: str = Field(..., description="SQL query to execute")
    table_name: Optional[str] = Field(None, description="Target table name")


class AnalysisInput(BaseModel):
    """Input for data analysis tool."""
    data: List[Dict[str, Any]] = Field(..., description="Data to analyze")
    analysis_type: str = Field(default="summary", description="Type of analysis")
    dimensions: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)


class ExportInput(BaseModel):
    """Input for export tool."""
    data: List[Dict[str, Any]] = Field(..., description="Data to export")
    filename: Optional[str] = None
    format: str = Field(default="xlsx", description="Export format: xlsx, csv")