"""
Template-based 7-day rolling content calendar generator.

Hard rules enforced:
- YouTube: max 1 long-form, max 2 short-form per week
- Instagram/LinkedIn/X/Facebook: max 2 short-form, 1-2 carousel, 2 static per week each
- Deliberate gap days per platform
- Instagram Stories: every alternate day, independent track
- No repeated topic across the 7-day window on any platform
"""

import logging
import random
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Set, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CALENDAR_CADENCE, STORIES_CADENCE_DAYS, NICHE_KEYWORDS
from calendar_engine.posting_times import get_best_time, is_good_posting_day
from calendar_engine.templates import get_templates, fill_template

logger = logging.getLogger(__name__)


def _get_trending_topics(trend_data: List[Dict]) -> List[str]:
    """
    Extract unique topic strings from trend_snapshots data,
    ranked by score (highest first).
    """
    if not trend_data:
        # Fallback to niche keywords if no trend data
        return list(NICHE_KEYWORDS)

    # Aggregate scores per keyword
    scores: Dict[str, float] = {}
    for item in trend_data:
        kw = item.get("keyword", "")
        score = item.get("score", 0) or 0
        # Also add titles as potential topics
        title = item.get("title", "")
        scores[kw] = scores.get(kw, 0) + score
        if title and len(title) > 10:
            scores[title[:60]] = scores.get(title[:60], 0) + score * 0.5

    # Sort by score descending, return unique topics
    sorted_topics = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
    return sorted_topics[:30]  # top 30 topics


def generate_calendar(
    trend_data: List[Dict],
    existing_calendar: List[Dict],
    target_date: Optional[date] = None,
) -> List[Dict]:
    """
    Generate a 7-day rolling content calendar.

    Rolling logic: if existing_calendar has entries, keep entries for
    future days and only generate new entries for the newest day being added.
    If no existing calendar, generate all 7 days fresh.

    Returns list of dicts ready for content_calendar table insertion.
    """
    if target_date is None:
        target_date = date.today()

    topics = _get_trending_topics(trend_data)
    if not topics:
        topics = list(NICHE_KEYWORDS)

    # ── Determine which days need generation ─────────────────────
    start_date = target_date
    end_date = target_date + timedelta(days=6)

    # Check which dates already have entries
    existing_dates: Set[date] = set()
    existing_topics: Set[str] = set()
    kept_entries: List[Dict] = []

    for entry in existing_calendar:
        entry_date = entry.get("date")
        if isinstance(entry_date, str):
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d").date()

        # Keep entries within the 7-day window
        if start_date <= entry_date <= end_date:
            existing_dates.add(entry_date)
            existing_topics.add(entry.get("topic", "").lower())
            kept_entries.append(entry)

    # Days that need new content
    days_to_generate = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        if d not in existing_dates:
            days_to_generate.append(d)

    if not days_to_generate:
        logger.info("Calendar is already complete for the 7-day window")
        return kept_entries

    # ── Track usage to enforce cadence limits ────────────────────
    # Count existing entries per platform per format
    usage: Dict[str, Dict[str, int]] = {}
    for entry in kept_entries:
        platform = entry.get("platform", "")
        fmt = entry.get("format", "")
        if platform not in usage:
            usage[platform] = {}
        usage[platform][fmt] = usage[platform].get(fmt, 0) + 1

    used_topics = set(existing_topics)
    new_entries: List[Dict] = []
    topic_idx = 0

    # ── Generate content for each new day ────────────────────────
    platforms = ["LinkedIn", "Instagram", "X", "Facebook", "YouTube"]

    for day in days_to_generate:
        for platform in platforms:
            cadence = CALENDAR_CADENCE.get(platform, {})

            # Check if this is a good posting day for the platform
            if not is_good_posting_day(platform, datetime.combine(day, datetime.min.time())):
                continue  # Gap day — skip this platform

            # Determine which formats still have budget
            available_formats = []
            for fmt, max_count in cadence.items():
                current = usage.get(platform, {}).get(fmt, 0)
                if current < max_count:
                    available_formats.append(fmt)

            if not available_formats:
                continue  # All format budgets exhausted for this platform

            # Pick a format (rotate through available ones)
            fmt = available_formats[day.day % len(available_formats)]

            # Pick a topic that hasn't been used yet
            topic = None
            for _ in range(len(topics)):
                candidate = topics[topic_idx % len(topics)]
                topic_idx += 1
                if candidate.lower() not in used_topics:
                    topic = candidate
                    break

            if not topic:
                # All topics used — reset and pick anyway
                topic = topics[random.randint(0, min(len(topics) - 1, 9))]

            used_topics.add(topic.lower())

            # Get best time
            best_time = get_best_time(
                platform, datetime.combine(day, datetime.min.time())
            )
            if best_time is None:
                continue  # Gap day

            # Fill template
            templates = get_templates(fmt)
            template = templates[random.randint(0, len(templates) - 1)]
            filled = fill_template(template, topic)

            entry = {
                "date": day.isoformat(),
                "platform": platform,
                "format": fmt,
                "topic": topic,
                "hook": filled["hook"],
                "body": filled["body"],
                "cta": filled["cta"],
                "best_time": best_time,
                "source_keyword": topic,
                "is_manual_override": False,
            }
            new_entries.append(entry)

            # Update usage tracking
            if platform not in usage:
                usage[platform] = {}
            usage[platform][fmt] = usage[platform].get(fmt, 0) + 1

    # ── Generate Instagram Stories (independent track) ───────────
    story_entries = [e for e in kept_entries if e.get("format") == "story"]
    story_dates = {
        (datetime.strptime(e["date"], "%Y-%m-%d").date()
         if isinstance(e["date"], str) else e["date"])
        for e in story_entries
    }

    for i in range(7):
        d = start_date + timedelta(days=i)
        if d in story_dates:
            continue
        # Every alternate day
        if i % STORIES_CADENCE_DAYS != 0:
            continue

        # Pick a unique topic for stories
        story_topic = None
        for _ in range(len(topics)):
            candidate = topics[topic_idx % len(topics)]
            topic_idx += 1
            if candidate.lower() not in used_topics:
                story_topic = candidate
                break
        if not story_topic:
            story_topic = topics[random.randint(0, min(len(topics) - 1, 9))]

        used_topics.add(story_topic.lower())

        story_templates = get_templates("story")
        template = story_templates[random.randint(0, len(story_templates) - 1)]
        filled = fill_template(template, story_topic)

        new_entries.append({
            "date": d.isoformat(),
            "platform": "Instagram",
            "format": "story",
            "topic": story_topic,
            "hook": filled["hook"],
            "body": filled["body"],
            "cta": filled["cta"],
            "best_time": get_best_time(
                "Instagram", datetime.combine(d, datetime.min.time())
            ) or "12:00 PM GST",
            "source_keyword": story_topic,
            "is_manual_override": False,
        })

    all_entries = kept_entries + new_entries
    logger.info(
        f"Calendar: kept {len(kept_entries)} existing, "
        f"generated {len(new_entries)} new entries"
    )
    return all_entries
