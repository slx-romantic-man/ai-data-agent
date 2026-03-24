"""
Chat models for conversation and message handling.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(str, Enum):
    """Intent types for user queries."""
    DATA_DETAIL = "data_detail"
    DATA_STATISTIC = "data_statistic"
    DATA_ANALYSIS = "data_analysis"
    DATA_EXPORT = "data_export"
    API_QUERY = "api_query"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """A single chat message."""
    role: MessageType
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Chat request model."""
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation continuity"
    )
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="User context"
    )


class ChartConfig(BaseModel):
    """Chart configuration for visualization."""
    type: str = Field(..., description="Chart type: line, bar, pie, etc.")
    x: Optional[str] = Field(None, description="X-axis field")
    y: Optional[str] = Field(None, description="Y-axis field")
    title: Optional[str] = Field(None, description="Chart title")
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional chart options"
    )


class DataResult(BaseModel):
    """Data result model."""
    columns: List[str] = Field(default_factory=list, description="Column names")
    rows: List[Dict[str, Any]] = Field(
        default_factory=list, description="Data rows"
    )
    total: Optional[int] = Field(None, description="Total rows (for pagination)")


class ReasoningStep(BaseModel):
    """Single reasoning step in ReAct loop."""
    step_number: int = Field(..., description="Step number in reasoning chain")
    thought: Optional[str] = Field(None, description="Agent's thought process")
    action: Optional[Dict[str, Any]] = Field(
        None, description="Action: {tool, parameters}"
    )
    observation: Optional[str] = Field(
        None, description="Result from tool execution"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class ReasoningLog(BaseModel):
    """Complete reasoning log for a query."""
    steps: List[ReasoningStep] = Field(
        default_factory=list, description="List of reasoning steps"
    )
    final_answer: Optional[str] = Field(None, description="Final answer text")
    total_steps: int = Field(0, description="Total number of reasoning steps")
    is_complete: bool = Field(False, description="Whether reasoning is complete")

    def add_step(self, step: ReasoningStep):
        """Add a new reasoning step."""
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def get_last_step(self) -> Optional[ReasoningStep]:
        """Get the last reasoning step."""
        return self.steps[-1] if self.steps else None

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert reasoning steps to message list for LLM context."""
        messages = []
        for step in self.steps:
            if step.thought:
                content = f"Thought: {step.thought}"
                if step.action:
                    import json
                    action_json = json.dumps(step.action, ensure_ascii=False)
                    content += f"\nAction: {action_json}"
                messages.append({"role": "assistant", "content": content})
            
            if step.observation:
                messages.append({"role": "user", "content": f"Observation: {step.observation}"})
        return messages


class AgentResponse(BaseModel):
    """Agent response model."""
    text: str = Field(..., description="Text response")
    data: Optional[DataResult] = Field(None, description="Data result")
    chart_config: Optional[ChartConfig] = Field(
        None, description="Chart configuration"
    )
    sql: Optional[str] = Field(
        None, description="Generated SQL or API call info"
    )
    intent: Optional[IntentType] = Field(None, description="Detected intent")
    entities: Optional[Dict[str, Any]] = Field(
        None, description="Extracted entities"
    )
    confidence: Optional[float] = Field(None, description="Confidence score")
    reasoning_log: Optional[ReasoningLog] = Field(
        None, description="ReAct reasoning steps"
    )


class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str = Field(..., description="Session ID")
    response: AgentResponse
    excel_url: Optional[str] = Field(None, description="Excel export URL")


class Session(BaseModel):
    """Chat session model."""
    session_id: str
    user_id: str
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    """Intent recognition result."""
    intent_type: IntentType
    entities: Dict[str, Any] = Field(default_factory=dict)
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    time_range: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    missing_info: Optional[List[str]] = Field(None, description="Missing required information")
    clarification_question: Optional[str] = Field(None, description="Question to ask user for missing info")


class ConversationState(str, Enum):
    """Conversation state for multi-turn dialogue."""
    NORMAL = "normal"
    WAITING_FOR_INFO = "waiting_for_info"


class ConversationContext(BaseModel):
    """Context for multi-turn conversation."""
    state: ConversationState = ConversationState.NORMAL
    pending_query: Optional[str] = Field(None, description="Original query waiting for info")
    missing_fields: Optional[List[str]] = Field(None, description="Fields that need to be provided")
    partial_intent: Optional[IntentResult] = Field(None, description="Partially recognized intent")
    api_id: Optional[str] = Field(None, description="Target API for the query")
    endpoint: Optional[str] = Field(None, description="Target endpoint for the query")
    created_at: datetime = Field(default_factory=datetime.now)


class QueryPlan(BaseModel):
    """Query execution plan."""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    needs_analysis: bool = False
    needs_export: bool = False
    target_tables: List[str] = Field(default_factory=list)