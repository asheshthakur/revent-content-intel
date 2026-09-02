"""
Trend scraper: aggregates trending topics/keywords from free sources.

Sources:
1. Google Trends via pytrends (free, unofficial)
2. Google News via RSS/feedparser
3. YouTube search via yt-dlp
4. Reddit public JSON endpoints

Writes to the trend_snapshots table in Supabase.
"""

import json
import logging
import subprocess
import time
import random
from datetime import datetime, date
from typing import Dict, List, Optional

import feedparser
import requests

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import NICHE_KEYWORDS, PYTRENDS_GEO, REDDIT_SUBREDDITS, USER_AGENTS

logger = logging.getLogger(__name__)


def scrape_google_trends(keywords: List[str], geo_codes: List[str]) -> List[Dict]:
    """
    Fetch interest_over_time for keywords from Google Trends via pytrends.
    Returns list of {keyword, source, score, metadata} dicts.
    """
    results = []
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=240, timeout=(10, 25))

        # pytrends supports max 5 keywords per request
        for i in range(0, len(keywords), 5):
            batch = keywords[i : i + 5]
            try:
                for geo in geo_codes:
                    pytrends.build_payload(batch, cat=0, timeframe="now 7-d", geo=geo)
                    iot = pytrends.interest_over_time()

                    if iot.empty:
                        continue

                    for kw in batch:
                        if kw in iot.columns:
                            avg_score = float(iot[kw].mean())
                            max_score = float(iot[kw].max())
                            results.append({
                                "keyword": kw,
                                "source": "google_trends",
                                "score": round(avg_score, 2),
                                "title": f"Trend score for '{kw}' in {geo}",
                                "url": None,
                                "metadata": {
                                    "geo": geo,
                                    "avg_score": avg_score,
                                    "max_score": max_score,
                                    "timeframe": "now 7-d",
                                },
                            })

                    # Respect rate limits
                    time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.warning(f"[GoogleTrends] Error for batch {batch}: {e}")
                time.sleep(10)  # Back off on rate limit
                continue

    except ImportError:
        logger.error("[GoogleTrends] pytrends not installed")
    except Exception as e:
        logger.error(f"[GoogleTrends] Unexpected error: {e}")

    return results


def scrape_google_news(keywords: List[str]) -> List[Dict]:
    """
    Fetch recent news articles via Google News RSS for each keyword.
    """
    results = []
    for kw in keywords:
        try:
            rss_url = (
                f"https://news.google.com/rss/search?"
                f"q={kw.replace(' ', '+')}&hl=en&gl=AE&ceid=AE:en"
            )
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:5]:  # top 5 articles per keyword
                results.append({
                    "keyword": kw,
                    "source": "google_news",
                    "score": 50.0,  # normalize later based on recency
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "metadata": {
                        "published": entry.get("published", ""),
                        "source_name": entry.get("source", {}).get("title", ""),
                    },
                })

            time.sleep(random.uniform(1, 3))

        except Exception as e:
            logger.warning(f"[GoogleNews] Error for keyword '{kw}': {e}")
            continue

    return results


def scrape_youtube_search(keywords: List[str]) -> List[Dict]:
    """
    Search YouTube for each keyword via native yt-dlp library, extract top video titles/tags.
    """
    results = []
    try:
        import yt_dlp
    except ImportError:
        logger.warning("[YouTubeSearch] yt_dlp library not installed.")
        return results

    import math

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlist_items": "1:5",
        "ignoreerrors": True,
    }

    for kw in keywords:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_query = f"ytsearch5:{kw}"
                info = ydl.extract_info(search_query, download=False)
                entries = (info.get("entries") or []) if info else []

                for vid in entries:
                    if not vid:
                        continue
                    view_count = vid.get("view_count") or 0
                    score = min(100.0, math.log10(max(view_count, 1)) * 15.0) if view_count > 0 else 50.0

                    results.append({
                        "keyword": kw,
                        "source": "youtube",
                        "score": round(score, 2),
                        "title": vid.get("title", ""),
                        "url": vid.get("url") or (f"https://www.youtube.com/watch?v={vid.get('id')}" if vid.get("id") else ""),
                        "metadata": {
                            "views": view_count,
                            "channel": vid.get("channel") or vid.get("uploader", ""),
                            "tags": vid.get("tags") or [],
                        },
                    })

            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            logger.warning(f"[YouTubeSearch] Error for keyword '{kw}': {e}")
            continue

    return results


def _get_reddit_client():
    """Attempt to instantiate a PRAW Reddit client from secrets or environment."""
    import streamlit as st
    client_id = None
    client_secret = None
    user_agent = None
    
    try:
        client_id = st.secrets.get("reddit_client_id") or st.secrets.get("REDDIT_CLIENT_ID")
        client_secret = st.secrets.get("reddit_client_secret") or st.secrets.get("REDDIT_CLIENT_SECRET")
        user_agent = st.secrets.get("reddit_user_agent") or st.secrets.get("REDDIT_USER_AGENT")
    except Exception:
        pass

    if not client_id:
        client_id = os.environ.get("REDDIT_CLIENT_ID") or os.environ.get("reddit_client_id")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET") or os.environ.get("reddit_client_secret")
        user_agent = os.environ.get("REDDIT_USER_AGENT") or os.environ.get("reddit_user_agent")

    if client_id and client_secret:
        try:
            import praw
            return praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent or "revent-content-intel:v1.0 (by /u/revent_intel)",
                check_for_async=False
            )
        except Exception as e:
            logger.warning(f"[Reddit PRAW] Initialization failed: {e}")
    return None


def scrape_reddit(keywords: List[str], subreddits: List[str]) -> List[Dict]:
    """
    Search Reddit for niche keywords across target subreddits.
    1. Uses official Reddit API via PRAW if client_id/secret are configured in Streamlit secrets.
    2. Gracefully falls back to public JSON endpoints with rate-limit handling.
    """
    reddit_client = _get_reddit_client()
    results = []

    # ── Strategy 1: Official Reddit API via PRAW ──────────────────
    if reddit_client:
        logger.info("[Reddit] Using official Reddit API via PRAW client")
        for sub_name in subreddits:
            try:
                sub = reddit_client.subreddit(sub_name)
                for kw in keywords:
                    try:
                        # Search top recent posts in subreddit
                        search_posts = list(sub.search(query=kw, sort="new", time_filter="week", limit=5))
                        for post in search_posts:
                            score = max(0, int(getattr(post, "score", 0)))
                            results.append({
                                "keyword": kw,
                                "source": "reddit",
                                "score": min(100, score),
                                "title": getattr(post, "title", ""),
                                "url": f"https://reddit.com{getattr(post, 'permalink', '')}",
                                "metadata": {
                                    "subreddit": sub_name,
                                    "score": score,
                                    "num_comments": getattr(post, "num_comments", 0),
                                    "created_utc": getattr(post, "created_utc", None),
                                    "author": str(getattr(post, "author", "")),
                                    "via": "praw_api"
                                },
                            })
                        time.sleep(random.uniform(0.5, 1.2))
                    except Exception as e:
                        logger.warning(f"[Reddit PRAW] Error searching r/{sub_name} for '{kw}': {e}")
            except Exception as e:
                logger.warning(f"[Reddit PRAW] Error accessing r/{sub_name}: {e}")
        if results:
            logger.info(f"[Reddit PRAW] Harvested {len(results)} signals via PRAW")
            return results

    # ── Strategy 2: Public JSON Endpoints Fallback ────────────────
    logger.info("[Reddit] PRAW not configured or returned empty. Using public JSON endpoint fallback.")
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for sub in subreddits:
        for kw in keywords:
            try:
                url = (
                    f"https://www.reddit.com/r/{sub}/search.json"
                    f"?q={kw.replace(' ', '+')}&sort=new&t=week&restrict_sr=1&limit=5"
                )
                resp = requests.get(url, headers=headers, timeout=15)

                if resp.status_code == 429:
                    logger.warning("[Reddit] Rate limited, backing off")
                    time.sleep(15)
                    continue

                if resp.status_code != 200:
                    continue

                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    pdata = post.get("data", {})
                    score = pdata.get("score", 0)
                    results.append({
                        "keyword": kw,
                        "source": "reddit",
                        "score": min(100, score),
                        "title": pdata.get("title", ""),
                        "url": f"https://reddit.com{pdata.get('permalink', '')}",
                        "metadata": {
                            "subreddit": sub,
                            "score": score,
                            "num_comments": pdata.get("num_comments", 0),
                            "created_utc": pdata.get("created_utc"),
                            "via": "public_json"
                        },
                    })

                time.sleep(random.uniform(1.5, 3.5))

            except Exception as e:
                logger.warning(f"[Reddit] Error for r/{sub} + '{kw}': {e}")
                continue

    return results


def scrape_all_trends() -> List[Dict]:
    """
    Run all trend scrapers and return a combined list of trend results.
    Each result is a dict ready to be inserted into trend_snapshots.
    """
    all_results = []

    logger.info("=== Starting Google Trends scrape ===")
    all_results.extend(scrape_google_trends(NICHE_KEYWORDS, PYTRENDS_GEO))

    logger.info("=== Starting Google News scrape ===")
    all_results.extend(scrape_google_news(NICHE_KEYWORDS))

    logger.info("=== Starting YouTube search scrape ===")
    all_results.extend(scrape_youtube_search(NICHE_KEYWORDS))

    logger.info("=== Starting Reddit scrape ===")
    all_results.extend(scrape_reddit(NICHE_KEYWORDS, REDDIT_SUBREDDITS))

    logger.info(f"=== Total trend results: {len(all_results)} ===")
    return all_results
