"""
GCC B2B/SME best-time-to-post heuristics.

These are editable defaults based on published GCC B2B benchmarks.
The dashboard UI flags them as heuristic defaults to be refined later
using real engagement data from Tab 1.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GCC_BEST_TIMES


def get_best_time(platform: str, target_date: datetime) -> str:
    """
    Return the best posting time for a platform on a given date.
    Returns a human-readable string like '10:00 AM GST'.
    """
    config = GCC_BEST_TIMES.get(platform)
    if not config:
        return "10:00 AM GST"

    day_name = target_date.strftime("%A")
    best_days = config.get("best_days", [])
    best_times = config.get("best_times", [])

    # If this day isn't a recommended day, it's a gap day
    if best_days and day_name not in best_days:
        return None  # signals a gap day

    if not best_times:
        return "10:00 AM GST"

    # Pick a time (rotate based on date to add variety)
    idx = target_date.day % len(best_times)
    time_str = best_times[idx]

    # Convert 24h to 12h format
    try:
        hour = int(time_str.split(":")[0])
        minute = time_str.split(":")[1] if ":" in time_str else "00"
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute} {period} GST"
    except (ValueError, IndexError):
        return f"{time_str} GST"


def get_display_schedule(platform: str) -> str:
    """Return the human-readable schedule string for a platform."""
    config = GCC_BEST_TIMES.get(platform)
    if not config:
        return "No schedule data"
    return config.get("display", "No schedule data")


def is_good_posting_day(platform: str, target_date: datetime) -> bool:
    """Check if target_date is a recommended posting day for the platform."""
    config = GCC_BEST_TIMES.get(platform)
    if not config:
        return True
    day_name = target_date.strftime("%A")
    best_days = config.get("best_days", [])
    if not best_days:
        return True
    return day_name in best_days
