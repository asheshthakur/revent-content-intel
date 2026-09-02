"""
Local SQLite Storage, Rate Limiter & Backup Manager.
Persists daily scrape snapshots into a local SQLite database (data/trend_history.db)
with zero paid services.

Tables:
- social_metrics (platform, handle, metric_name, value, timestamp)
- trend_keywords (keyword, source, metric_name, value, title, url, timestamp)
- competitor_snapshots (competitor_name, platform, handle, metric_name, value, timestamp)
- scraper_state (key, value, updated_at)

Also provides:
- 24-hour rate limit guard (check_rate_limit, record_scrape_success)
- Automatic CSV snapshot export for backup across ephemeral restarts
"""

import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

logger = logging.getLogger(__name__)

DB_PATH = config.SQLITE_DB_PATH


def get_db_connection() -> sqlite3.Connection:
    """Connect to SQLite and ensure directories and tables exist."""
    dir_name = os.path.dirname(DB_PATH)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """Create the metric tables and scraper_state table if not exists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Social metrics (our channels)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                handle TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL,
                timestamp TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_ts ON social_metrics(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_plat ON social_metrics(platform, metric_name);")

        # 2. Trend keywords
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                source TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL,
                title TEXT,
                url TEXT,
                timestamp TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_ts ON trend_keywords(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_kw ON trend_keywords(keyword);")

        # 3. Competitor snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                handle TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL,
                timestamp TEXT NOT NULL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_ts ON competitor_snapshots(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_name ON competitor_snapshots(competitor_name, platform);")

        # 4. Scraper state & rate limiting
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraper_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # 5. Consecutive failure tracker for alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_tracker (
                target TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                consecutive_failures INTEGER DEFAULT 0,
                last_error TEXT,
                last_failure_time TEXT
            );
        """)

        conn.commit()
    finally:
        conn.close()


# ── Insertion Helpers (Append-Only) ──────────────────────────────────

def insert_social_metric(platform: str, handle: str, metric_name: str, value: Optional[float], ts: Optional[str] = None):
    """Insert a metric row into social_metrics."""
    if value is None:
        return
    ts = ts or datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO social_metrics (platform, handle, metric_name, value, timestamp) VALUES (?, ?, ?, ?, ?)",
            (platform, handle, metric_name, float(value), ts)
        )
        conn.commit()
    finally:
        conn.close()


def insert_trend_metric(keyword: str, source: str, metric_name: str, value: Optional[float], title: str = "", url: str = "", ts: Optional[str] = None):
    """Insert a trend signal into trend_keywords."""
    if value is None:
        return
    ts = ts or datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO trend_keywords (keyword, source, metric_name, value, title, url, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (keyword, source, metric_name, float(value), title, url, ts)
        )
        conn.commit()
    finally:
        conn.close()


def insert_competitor_metric(competitor_name: str, platform: str, handle: str, metric_name: str, value: Optional[float], ts: Optional[str] = None):
    """Insert a competitor metric into competitor_snapshots."""
    if value is None:
        return
    ts = ts or datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO competitor_snapshots (competitor_name, platform, handle, metric_name, value, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (competitor_name, platform, handle, metric_name, float(value), ts)
        )
        conn.commit()
    finally:
        conn.close()


# ── Rate Limiting (24 Hours) ─────────────────────────────────────────

def get_last_successful_scrape() -> Optional[datetime]:
    """Retrieve the datetime of the last successful full scrape run."""
    init_sqlite_db()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT value FROM scraper_state WHERE key = 'last_successful_scrape'").fetchone()
        if row and row["value"]:
            try:
                return datetime.fromisoformat(row["value"])
            except Exception:
                return None
        return None
    finally:
        conn.close()


def check_rate_limit(max_frequency_hours: int = 24) -> Tuple[bool, Optional[float]]:
    """
    Check if a full scrape can run now.
    Returns (can_run: bool, hours_since_last: Optional[float]).
    If hours_since_last < max_frequency_hours, can_run is False.
    """
    last_dt = get_last_successful_scrape()
    if not last_dt:
        return True, None

    # Compare in UTC
    now_utc = datetime.now(timezone.utc)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)

    diff = now_utc - last_dt
    hours_elapsed = diff.total_seconds() / 3600.0

    if hours_elapsed < max_frequency_hours:
        return False, hours_elapsed
    return True, hours_elapsed


def record_scrape_success(ts: Optional[datetime] = None):
    """Record that a full scrape run completed successfully."""
    init_sqlite_db()
    ts = ts or datetime.now(timezone.utc)
    ts_str = ts.isoformat()
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO scraper_state (key, value, updated_at) VALUES ('last_successful_scrape', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (ts_str, ts_str)
        )
        conn.commit()
    finally:
        conn.close()


# ── Failure & Consecutive Run Tracking ───────────────────────────────

def record_target_outcome(target: str, platform: str, success: bool, error_msg: Optional[str] = None) -> int:
    """
    Record target outcome and return current consecutive failures count.
    If success, resets counter to 0.
    """
    init_sqlite_db()
    now_str = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT consecutive_failures FROM failure_tracker WHERE target = ?", (target,)).fetchone()
        current_fails = row["consecutive_failures"] if row else 0

        if success:
            new_fails = 0
            err_val = None
        else:
            new_fails = current_fails + 1
            err_val = error_msg or "Unknown scrape failure"

        conn.execute(
            "INSERT INTO failure_tracker (target, platform, consecutive_failures, last_error, last_failure_time) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(target) DO UPDATE SET "
            "consecutive_failures = excluded.consecutive_failures, "
            "last_error = excluded.last_error, "
            "last_failure_time = excluded.last_failure_time",
            (target, platform, new_fails, err_val, now_str)
        )
        conn.commit()
        return new_fails
    finally:
        conn.close()


def get_repeated_failures(min_consecutive: int = 2) -> List[Dict[str, Any]]:
    """Return targets that have failed on 2+ consecutive runs."""
    init_sqlite_db()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT target, platform, consecutive_failures, last_error, last_failure_time "
            "FROM failure_tracker WHERE consecutive_failures >= ?",
            (min_consecutive,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Backup / Export Step (Survivability across restarts) ──────────────

def export_backup_csvs(backup_dir: str = "data/backups") -> Dict[str, str]:
    """
    Export all metric tables to CSV files.
    Ensures that historical snapshots can be backed up or committed to git/storage.
    """
    init_sqlite_db()
    os.makedirs(backup_dir, exist_ok=True)
    conn = get_db_connection()
    exported = {}
    try:
        tables = ["social_metrics", "trend_keywords", "competitor_snapshots", "scraper_state"]
        for tbl in tables:
            df = pd.read_sql_query(f"SELECT * FROM {tbl}", conn)
            filepath = os.path.join(backup_dir, f"{tbl}.csv")
            df.to_csv(filepath, index=False)
            exported[tbl] = filepath
        logger.info(f"[Backup] Exported {len(exported)} metric tables to {backup_dir}")
        return exported
    finally:
        conn.close()


# Initialize on import
init_sqlite_db()
