"""
Formatting utilities.
"""
from typing import Any


def format_number(value: Any, decimal_places: int = 2) -> str:
    """Format number with thousand separators."""
    if value is None:
        return "0"

    try:
        num = float(value)
        if num == int(num):
            return f"{int(num):,}"
        else:
            return f"{num:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: Any, decimal_places: int = 2) -> str:
    """Format value as percentage."""
    if value is None:
        return "0%"

    try:
        num = float(value)
        if num > 1:
            # Assume it's already a percentage
            return f"{num:.{decimal_places}f}%"
        else:
            # Convert to percentage
            return f"{num * 100:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return str(value)


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix