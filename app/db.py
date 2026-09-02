"""
Supabase client helper for the Streamlit dashboard.

Reads connection config from Streamlit secrets (when running as app)
or from environment variables (when running the scraper).
Includes seamless fallback to realistic seed data when Supabase credentials
are not yet configured, allowing instant local testing and preview.
"""

import os
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)

# ── Module-level client cache ────────────────────────────────────────
_client = None
_using_fallback = False


def is_supabase_configured() -> bool:
    """Checks whether Supabase credentials are provided."""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if url and key and "YOUR_PROJECT" not in url:
            return True
    except Exception:
        pass
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    return bool(url and key and "YOUR_PROJECT" not in url)


def get_client():
    """
    Get or create a Supabase client.
    Returns None if credentials are not configured or connection fails.
    """
    global _client, _using_fallback
    if _client is not None:
        return _client

    url = None
    key = None

    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

    if not url or not key:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key or "YOUR_PROJECT" in url:
        _using_fallback = True
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        _using_fallback = False
        return _client
    except Exception as e:
        logger.warning(f"Could not connect to Supabase: {e}. Using fallback data.")
        _using_fallback = True
        return None


def get_scraper_client():
    """
    Get a Supabase client for the scraper (uses service_role key for writes).
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise ValueError(
            "Supabase credentials not found in environment. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY."
        )
    from supabase import create_client
    return create_client(url, key)


# ── In-Memory / Session State Store for Demo Mode ─────────────────────

def _get_demo_store() -> Dict[str, Any]:
    """Provides an in-memory session store when Supabase is not yet linked."""
    from app.mock_data import generate_seed_snapshots, generate_seed_trends, generate_seed_hashtags
    from calendar_engine.generator import generate_calendar

    if "demo_store" not in st.session_state:
        seed_trends = generate_seed_trends(days=60)
        seed_snaps = generate_seed_snapshots(days=90)
        seed_cal = generate_calendar(trend_data=seed_trends, existing_calendar=[], target_date=date.today())
        seed_tags = generate_seed_hashtags()

        st.session_state["demo_store"] = {
            "snapshots": seed_snaps,
            "trends": seed_trends,
            "calendar": seed_cal,
            "hashtags": seed_tags,
            "scrape_log": [
                {"date": date.today().isoformat(), "platform": "YouTube", "status": "success", "duration_seconds": 2.1},
                {"date": date.today().isoformat(), "platform": "LinkedIn", "status": "success", "duration_seconds": 4.5},
                {"date": date.today().isoformat(), "platform": "X", "status": "success", "duration_seconds": 3.8},
                {"date": date.today().isoformat(), "platform": "Instagram", "status": "success", "duration_seconds": 4.2},
                {"date": date.today().isoformat(), "platform": "Facebook", "status": "success", "duration_seconds": 3.9},
            ]
        }
    return st.session_state["demo_store"]


# ── Read helpers ─────────────────────────────────────────────────────

def read_snapshots(
    days: int = 30,
    is_competitor: Optional[bool] = None,
    platform: Optional[str] = None,
    handle: Optional[str] = None,
) -> List[Dict]:
    """Read social_snapshots with date and optional filters."""
    client = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    if client:
        try:
            query = client.table("social_snapshots").select("*").gte("date", cutoff)
            if is_competitor is not None:
                query = query.eq("is_competitor", is_competitor)
            if platform:
                query = query.eq("platform", platform)
            if handle:
                query = query.eq("handle", handle)
            query = query.order("date", desc=False)
            response = query.execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase read_snapshots failed: {e}. Falling back to demo data.")

    # Fallback to local session store
    store = _get_demo_store()
    results = []
    for s in store["snapshots"]:
        if s["date"] >= cutoff:
            if is_competitor is not None and s.get("is_competitor") != is_competitor:
                continue
            if platform and s.get("platform") != platform:
                continue
            if handle and s.get("handle") != handle:
                continue
            results.append(s)
    return results


def read_calendar(days: int = 7) -> List[Dict]:
    """Read content_calendar entries for the upcoming window."""
    return read_all_calendar()


def read_all_calendar() -> List[Dict]:
    """Read all content_calendar entries (for the rolling 7-day window)."""
    client = get_client()
    cutoff = (date.today() - timedelta(days=1)).isoformat()
    end = (date.today() + timedelta(days=7)).isoformat()

    if client:
        try:
            response = (
                client.table("content_calendar")
                .select("*")
                .gte("date", cutoff)
                .lte("date", end)
                .order("date", desc=False)
                .execute()
            )
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase read_all_calendar failed: {e}")

    store = _get_demo_store()
    return [c for c in store["calendar"] if cutoff <= str(c.get("date", "")) <= end]


def read_trends(days: int = 7) -> List[Dict]:
    """Read trend_snapshots for the last N days."""
    client = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    if client:
        try:
            response = (
                client.table("trend_snapshots")
                .select("*")
                .gte("date", cutoff)
                .order("score", desc=True)
                .execute()
            )
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase read_trends failed: {e}")

    store = _get_demo_store()
    return [t for t in store["trends"] if t.get("date", "") >= cutoff]


def read_hashtags(days: int = 30) -> List[Dict]:
    """Read hashtag_tracking for the last N days."""
    client = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    if client:
        try:
            response = (
                client.table("hashtag_tracking")
                .select("*")
                .gte("date", cutoff)
                .order("frequency", desc=True)
                .execute()
            )
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase read_hashtags failed: {e}")

    store = _get_demo_store()
    return store.get("hashtags", [])


def read_scrape_log(days: int = 7) -> List[Dict]:
    """Read recent scrape log entries."""
    client = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    if client:
        try:
            response = (
                client.table("scrape_log")
                .select("*")
                .gte("date", cutoff)
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase read_scrape_log failed: {e}")

    store = _get_demo_store()
    return store.get("scrape_log", [])


# ── Write helpers ────────────────────────────────────────────────────

def upsert_snapshot(data: Dict) -> bool:
    """Upsert a row into social_snapshots."""
    client = get_client()
    if client:
        try:
            client.table("social_snapshots").upsert(
                data,
                on_conflict="platform,handle,date",
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to upsert snapshot in Supabase: {e}")

    # Also update demo store
    store = _get_demo_store()
    # Replace existing if matches (platform, handle, date)
    replaced = False
    for idx, s in enumerate(store["snapshots"]):
        if s.get("platform") == data.get("platform") and s.get("handle") == data.get("handle") and s.get("date") == data.get("date"):
            store["snapshots"][idx] = {**s, **data}
            replaced = True
            break
    if not replaced:
        if "id" not in data:
            data["id"] = len(store["snapshots"]) + 1
        store["snapshots"].append(data)
    return True


def upsert_calendar_entry(data: Dict) -> bool:
    """Upsert a row into content_calendar."""
    client = get_client()
    if client:
        try:
            client.table("content_calendar").upsert(
                data,
                on_conflict="date,platform,format,topic",
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to upsert calendar entry in Supabase: {e}")

    store = _get_demo_store()
    replaced = False
    for idx, c in enumerate(store["calendar"]):
        if c.get("date") == data.get("date") and c.get("platform") == data.get("platform") and c.get("topic") == data.get("topic"):
            store["calendar"][idx] = {**c, **data}
            replaced = True
            break
    if not replaced:
        if "id" not in data:
            data["id"] = len(store["calendar"]) + 1
        store["calendar"].append(data)
    return True


def insert_trend(data: Dict) -> bool:
    client = get_client()
    if client:
        try:
            client.table("trend_snapshots").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to insert trend: {e}")
    return True


def insert_hashtags(data_list: List[Dict]) -> bool:
    client = get_client()
    if client:
        try:
            client.table("hashtag_tracking").insert(data_list).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to insert hashtags: {e}")
    return True


def insert_scrape_log(data: Dict) -> bool:
    client = get_client()
    if client:
        try:
            client.table("scrape_log").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to insert scrape log: {e}")
    return True


def update_snapshot(row_id: int, updates: Dict) -> bool:
    """Update a specific social_snapshots row by ID (for manual edits)."""
    client = get_client()
    if client:
        try:
            client.table("social_snapshots").update(updates).eq("id", row_id).execute()
        except Exception as e:
            logger.warning(f"Supabase update_snapshot error: {e}")

    store = _get_demo_store()
    for s in store["snapshots"]:
        if s.get("id") == row_id:
            s.update(updates)
            return True
    return True


def update_calendar_entry(row_id: int, updates: Dict) -> bool:
    """Update a specific content_calendar row by ID (for manual edits)."""
    updates["is_manual_override"] = True
    client = get_client()
    if client:
        try:
            client.table("content_calendar").update(updates).eq("id", row_id).execute()
        except Exception as e:
            logger.warning(f"Supabase update_calendar_entry error: {e}")

    store = _get_demo_store()
    for c in store["calendar"]:
        if c.get("id") == row_id:
            c.update(updates)
            return True
    return True


def delete_old_calendar(before_date: str) -> bool:
    client = get_client()
    if client:
        try:
            client.table("content_calendar").delete().lt("date", before_date).eq("is_manual_override", False).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase delete_old_calendar error: {e}")
    return True
