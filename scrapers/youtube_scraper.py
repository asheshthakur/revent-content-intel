"""
YouTube channel scraper using native yt-dlp Python library (no API key needed).

This is the most reliable scraper in the suite because yt-dlp interacts
directly with YouTube's public endpoints natively without browser overhead.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from scrapers.base import BaseScraper, ScraperResult, parse_count

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    platform = "YouTube"

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        """
        Use native yt_dlp library to extract channel info and recent video stats.
        """
        try:
            import yt_dlp
        except ImportError:
            logger.error("[YouTube] yt_dlp library is not installed.")
            return None

        channel_url = url.rstrip("/")
        videos_url = f"{channel_url}/videos"

        subscribers = None
        views_list: List[int] = []
        likes_list: List[int] = []
        comments_list: List[int] = []
        captions: List[str] = []
        video_data: List[Dict[str, Any]] = []

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,  # fetch individual video metadata
            "playlist_items": "1:8",
            "ignoreerrors": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(videos_url, download=False)
                if not info:
                    # Fallback to base channel URL
                    info = ydl.extract_info(channel_url, download=False)

                if not info:
                    logger.error(f"[YouTube] No info returned for {url}")
                    return None

                # Extract subscriber count
                subscribers = info.get("channel_follower_count")

                entries = info.get("entries") or []
                for vid in entries:
                    if not vid:
                        continue
                    if not subscribers and vid.get("channel_follower_count"):
                        subscribers = vid["channel_follower_count"]

                    views = vid.get("view_count")
                    likes = vid.get("like_count")
                    comments = vid.get("comment_count")

                    if views is not None:
                        views_list.append(views)
                    if likes is not None:
                        likes_list.append(likes)
                    if comments is not None:
                        comments_list.append(comments)

                    title = vid.get("title", "")
                    desc = (vid.get("description") or "")[:200]
                    captions.append(f"{title} | {desc}")

                    video_data.append({
                        "title": title,
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "upload_date": vid.get("upload_date"),
                        "tags": vid.get("tags") or [],
                        "url": vid.get("webpage_url") or vid.get("url"),
                    })

        except Exception as e:
            logger.warning(f"[YouTube] Direct extraction error for {url}: {e}")
            # Try flat extraction fallback for subscriber count
            try:
                flat_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
                with yt_dlp.YoutubeDL(flat_opts) as ydl:
                    flat_info = ydl.extract_info(channel_url, download=False)
                    if flat_info:
                        subscribers = flat_info.get("channel_follower_count")
            except Exception:
                pass

        likes_avg = float(sum(likes_list) / len(likes_list)) if likes_list else None
        comments_avg = float(sum(comments_list) / len(comments_list)) if comments_list else None
        views_avg = float(sum(views_list) / len(views_list)) if views_list else None

        # Estimate post frequency (videos per week)
        post_frequency = None
        if len(video_data) >= 2:
            try:
                dates = []
                for vid in video_data:
                    upload_date = vid.get("upload_date")
                    if upload_date:
                        dates.append(datetime.strptime(str(upload_date), "%Y%m%d"))
                if len(dates) >= 2:
                    dates.sort()
                    span_days = (dates[-1] - dates[0]).days
                    if span_days > 0:
                        post_frequency = round(len(dates) / span_days * 7, 2)
            except Exception:
                pass

        return ScraperResult(
            platform=self.platform,
            handle=url,
            followers=subscribers,
            likes_avg=likes_avg,
            comments_avg=comments_avg,
            shares_avg=None,
            posts_scraped=len(video_data),
            post_frequency=post_frequency,
            raw_data={
                "videos": video_data,
                "views_avg": views_avg,
                "subscribers": subscribers,
                "url": url,
            },
            captions=captions,
        )
