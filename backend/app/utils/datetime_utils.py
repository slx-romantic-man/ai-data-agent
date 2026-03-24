"""
DateTime parsing utilities.
"""
import re
from datetime import datetime, timedelta
from typing import Dict


def parse_time_range(time_str: str) -> Dict[str, str]:
    """
    Parse time range string to start and end dates.

    Supports formats like:
    - "最近7天" -> {start: 7 days ago, end: today}
    - "本月" -> {start: first day of month, end: today}
    - "2024-01-01至2024-01-31" -> explicit range
    """
    now = datetime.now()

    # Match "最近N天"
    match = re.match(r"最近(\d+)天", time_str)
    if match:
        days = int(match.group(1))
        start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    # Match "最近N周"
    match = re.match(r"最近(\d+)周", time_str)
    if match:
        weeks = int(match.group(1))
        start = (now - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    # Match "最近N月"
    match = re.match(r"最近(\d+)月", time_str)
    if match:
        months = int(match.group(1))
        # Approximate months as 30 days
        start = (now - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    # Match "今天"
    if time_str == "今天":
        today = now.strftime("%Y-%m-%d")
        return {"start": today, "end": today}

    # Match "昨天"
    if time_str == "昨天":
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return {"start": yesterday, "end": yesterday}

    # Match "本周"
    if time_str == "本周":
        start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    # Match "本月"
    if time_str == "本月":
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    # Match explicit date range "YYYY-MM-DD至YYYY-MM-DD"
    match = re.match(r"(\d{4}-\d{2}-\d{2})至(\d{4}-\d{2}-\d{2})", time_str)
    if match:
        return {"start": match.group(1), "end": match.group(2)}

    # Default: return as-is
    return {"start": time_str, "end": time_str}