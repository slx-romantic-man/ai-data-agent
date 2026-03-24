"""
ID generation utilities.
"""
import uuid
from datetime import datetime


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def generate_task_id() -> str:
    """Generate a unique task ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique = str(uuid.uuid4())[:8]
    return f"task_{timestamp}_{unique}"