"""
Serialization utilities.
"""
from datetime import datetime
from typing import Any, Dict


def safe_json_serialize(obj: Any) -> Any:
    """Safely serialize object to JSON-compatible format."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return str(obj)


def flatten_dict(d: Dict[str, Any], parent_key: str = "",
                 sep: str = "_") -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)