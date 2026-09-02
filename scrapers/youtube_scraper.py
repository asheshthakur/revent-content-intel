"""
YouTube scraper with hybrid architecture:
1. Primary: Official YouTube Data API v3 (free-tier quota) using st.secrets["youtube_api_key"]
2. Fallback: Native yt-dlp library extraction (no API key required)

Ensures zero breakage whether an API key is provided or not.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import streamlit as st
from scrapers.base import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


def get_youtube_api_key() -> Optional[str]:
    """Retrieve YouTube Data API v3 key from Streamlit secrets or environment."""
    key = None
    try:
        key = st.secrets.get("youtube_api_key") or st.secrets.get("YOUTUBE_API_KEY")
    except Exception:
        pass
    if not key:
        key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("youtube_api_key")
    return key if key and not key.startswith("your-") else None


class YouTubeScraper(BaseScraper):
    platform = "YouTube"

    def _extract_channel_identifier(self, url: str) -> Dict[str, str]:
        """Extract handle, custom URL, or channel ID from YouTube channel URL."""
        clean_url = url.rstrip("/")
        # Matches https://www.youtube.com/@revent
        handle_match = re.search(r"@([a-zA-Z0-9_\-\.]+)", clean_url)
        if handle_match:
            return {"type": "handle", "value": handle_match.group(1)}
        
        # Matches https://www.youtube.com/channel/UC...
        channel_id_match = re.search(r"/channel/(UC[a-zA-Z0-9_\-]+)", clean_url)
        if channel_id_match:
            return {"type": "id", "value": channel_id_match.group(1)}
            
        parts = clean_url.split("/")
        return {"type": "custom", "value": parts[-1]}

    def _scrape_via_api(self, url: str, api_key: str) -> Optional[ScraperResult]:
        """Fetch subscriber count and recent videos via YouTube Data API v3 (free tier)."""
        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
            
            ident = self._extract_channel_identifier(url)
            channel_id = None

            if ident["type"] == "handle":
                req = youtube.channels().list(part="snippet,statistics,contentDetails", forHandle=ident["value"])
                res = req.execute()
                items = res.get("items", [])
                if items:
                    channel_id = items[0]["id"]
                    channel_info = items[0]
                else:
                    # Search by query fallback
                    s_req = youtube.search().list(part="snippet", q=ident["value"], type="channel", maxResults=1)
                    s_res = s_req.execute()
                    if s_res.get("items"):
                        channel_id = s_res["items"][0]["snippet"]["channelId"]
                        res = youtube.channels().list(part="snippet,statistics,contentDetails", id=channel_id).execute()
                        items = res.get("items", [])
                        channel_info = items[0] if items else None
                    else:
                        channel_info = None
            elif ident["type"] == "id":
                channel_id = ident["value"]
                res = youtube.channels().list(part="snippet,statistics,contentDetails", id=channel_id).execute()
                items = res.get("items", [])
                channel_info = items[0] if items else None
            else:
                res = youtube.channels().list(part="snippet,statistics,contentDetails", forUsername=ident["value"]).execute()
                items = res.get("items", [])
                channel_info = items[0] if items else None

            if not channel_info:
                logger.warning(f"[YouTube API] Channel not found for {url}")
                return None

            stats = channel_info.get("statistics", {})
            subscribers = int(stats.get("subscriberCount", 0)) if "subscriberCount" in stats else None

            # Get uploads playlist ID to inspect recent videos
            uploads_playlist_id = channel_info.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            video_data = []
            likes_list = []
            comments_list = []
            views_list = []
            captions = []

            if uploads_playlist_id:
                playlist_items = youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=8
                ).execute()

                video_ids = [item["contentDetails"]["videoId"] for item in playlist_items.get("items", [])]
                if video_ids:
                    v_res = youtube.videos().list(part="snippet,statistics", id=",".join(video_ids)).execute()
                    for v in v_res.get("items", []):
                        v_stats = v.get("statistics", {})
                        v_snippet = v.get("snippet", {})
                        views = int(v_stats.get("viewCount", 0)) if "viewCount" in v_stats else 0
                        likes = int(v_stats.get("likeCount", 0)) if "likeCount" in v_stats else 0
                        comments = int(v_stats.get("commentCount", 0)) if "commentCount" in v_stats else 0

                        views_list.append(views)
                        likes_list.append(likes)
                        comments_list.append(comments)

                        title = v_snippet.get("title", "")
                        desc = (v_snippet.get("description", "") or "")[:200]
                        captions.append(f"{title} | {desc}")

                        video_data.append({
                            "title": title,
                            "views": views,
                            "likes": likes,
                            "comments": comments,
                            "upload_date": v_snippet.get("publishedAt"),
                            "tags": v_snippet.get("tags", []),
                            "url": f"https://www.youtube.com/watch?v={v['id']}"
                        })

            likes_avg = float(sum(likes_list) / len(likes_list)) if likes_list else None
            comments_avg = float(sum(comments_list) / len(comments_list)) if comments_list else None
            views_avg = float(sum(views_list) / len(views_list)) if views_list else None

            logger.info(f"[YouTube API] Successfully scraped {url} via Data API v3 (Subscribers: {subscribers})")
            return ScraperResult(
                platform=self.platform,
                handle=url,
                followers=subscribers,
                likes_avg=likes_avg,
                comments_avg=comments_avg,
                shares_avg=None,
                posts_scraped=len(video_data),
                post_frequency=None,
                raw_data={
                    "videos": video_data,
                    "views_avg": views_avg,
                    "subscribers": subscribers,
                    "url": url,
                    "source": "youtube_api_v3"
                },
                captions=captions,
            )

        except Exception as e:
            logger.warning(f"[YouTube API] Failed for {url}: {e}. Falling back to yt-dlp.")
            return None

    def _scrape_via_ytdlp(self, url: str) -> Optional[ScraperResult]:
        """Fallback scraper using native yt-dlp library."""
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
            "extract_flat": False,
            "playlist_items": "1:8",
            "ignoreerrors": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(videos_url, download=False)
                if not info:
                    info = ydl.extract_info(channel_url, download=False)

                if not info:
                    return None

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
            logger.warning(f"[YouTube yt-dlp] Direct extraction error for {url}: {e}")
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
                "source": "yt_dlp"
            },
            captions=captions,
        )

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        """
        Scrape YouTube channel: checks for YouTube Data API v3 key first,
        otherwise falls back seamlessly to yt-dlp.
        """
        api_key = get_youtube_api_key()
        if api_key:
            res = self._scrape_via_api(url, api_key)
            if res:
                return res

        # Fallback to yt-dlp
        return self._scrape_via_ytdlp(url)
