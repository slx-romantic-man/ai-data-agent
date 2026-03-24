"""
Helper utility functions.

This module re-exports utilities from domain-specific modules
for backward compatibility.
"""
# ID utilities
from app.utils.id_utils import generate_session_id, generate_task_id

# DateTime utilities
from app.utils.datetime_utils import parse_time_range

# Formatting utilities
from app.utils.format_utils import (
    format_number,
    format_percentage,
    truncate_string,
)

# Serialization utilities
from app.utils.serialization import safe_json_serialize, flatten_dict

# Export all
__all__ = [
    "generate_session_id",
    "generate_task_id",
    "parse_time_range",
    "format_number",
    "format_percentage",
    "truncate_string",
    "safe_json_serialize",
    "flatten_dict",
]