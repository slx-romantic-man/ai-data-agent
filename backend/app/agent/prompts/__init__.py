"""Prompts module."""
from app.agent.prompts.system_prompt import (
    SYSTEM_PROMPT,
    get_system_prompt,
    get_system_prompt_with_history,
)
from app.agent.prompts.intent_prompt import (
    INTENT_PROMPT,
    get_intent_prompt,
    get_clarification_prompt,
)
from app.agent.prompts.sql_prompt import (
    SQL_PROMPT,
    get_sql_prompt,
    get_sql_validation_prompt,
    get_sql_fix_prompt,
)
from app.agent.prompts.analysis_prompt import (
    ANALYSIS_PROMPT,
    get_analysis_prompt,
    get_trend_analysis_prompt,
    get_comparison_analysis_prompt,
    get_anomaly_analysis_prompt,
)

__all__ = [
    # System prompt
    "SYSTEM_PROMPT",
    "get_system_prompt",
    "get_system_prompt_with_history",
    # Intent prompt
    "INTENT_PROMPT",
    "get_intent_prompt",
    "get_clarification_prompt",
    # SQL prompt
    "SQL_PROMPT",
    "get_sql_prompt",
    "get_sql_validation_prompt",
    "get_sql_fix_prompt",
    # Analysis prompt
    "ANALYSIS_PROMPT",
    "get_analysis_prompt",
    "get_trend_analysis_prompt",
    "get_comparison_analysis_prompt",
    "get_anomaly_analysis_prompt",
]