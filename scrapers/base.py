"""
Base scraper class with retry logic, random delays, UA rotation,
and try/except wrappers. All platform scrapers inherit from this.
"""

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    SCRAPE_DELAY_RANGE,
    SCRAPE_TIMEOUT,
    MAX_RETRIES,
    PLAYWRIGHT_HEADLESS,
    USER_AGENTS,
    DEFAULT_HEADERS,
)

logger = logging.getLogger(__name__)


class ScraperResult:
    """Standard result object returned by every scraper."""

    def __init__(
        self,
        platform: str,
        handle: str,
        followers: Optional[int] = None,
        likes_avg: Optional[float] = None,
        comments_avg: Optional[float] = None,
        shares_avg: Optional[float] = None,
        engagement_rate: Optional[float] = None,
        posts_scraped: int = 0,
        post_frequency: Optional[float] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        hashtags: Optional[list] = None,
        captions: Optional[list] = None,
    ):
        self.platform = platform
        self.handle = handle
        self.followers = followers
        self.likes_avg = likes_avg
        self.comments_avg = comments_avg
        self.shares_avg = shares_avg
        self.engagement_rate = engagement_rate
        self.posts_scraped = posts_scraped
        self.post_frequency = post_frequency
        self.raw_data = raw_data or {}
        self.hashtags = hashtags or []
        self.captions = captions or []

    def compute_engagement_rate(self) -> Optional[float]:
        """Compute engagement rate if we have the data."""
        if not self.followers or self.followers == 0:
            return None
        total = (self.likes_avg or 0) + (self.comments_avg or 0) + (self.shares_avg or 0)
        if total == 0:
            return None
        self.engagement_rate = round(total / self.followers * 100, 4)
        return self.engagement_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "handle": self.handle,
            "followers": self.followers,
            "likes_avg": self.likes_avg,
            "comments_avg": self.comments_avg,
            "shares_avg": self.shares_avg,
            "engagement_rate": self.engagement_rate,
            "posts_scraped": self.posts_scraped,
            "post_frequency": self.post_frequency,
            "raw_data": self.raw_data,
        }


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers.

    Provides:
    - Random UA rotation
    - Random delay between requests
    - Playwright browser context management
    - Retry logic with exponential backoff
    - Top-level try/except so failures never crash the pipeline
    """

    platform: str = "unknown"

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def _random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    async def _random_delay(self):
        """Wait a random time between requests to reduce block risk."""
        delay = random.uniform(*SCRAPE_DELAY_RANGE)
        logger.debug(f"[{self.platform}] Sleeping {delay:.1f}s between requests")
        await asyncio.sleep(delay)

    async def _create_context(self, pw) -> BrowserContext:
        """Launch a headless Chromium browser with stealth-ish settings."""
        self._browser = await pw.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
        ua = self._random_ua()
        self._context = await self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="Asia/Dubai",
            extra_http_headers={
                k: v for k, v in DEFAULT_HEADERS.items()
                if k not in ("Accept-Encoding",)   # let Playwright handle encoding
            },
        )
        # Block images / fonts / media to speed up loads
        await self._context.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,eot,mp4,webm}",
            lambda route: route.abort(),
        )
        return self._context

    async def _close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()

    @abstractmethod
    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        """Platform-specific scraping logic. Implement in subclass."""
        ...

    async def scrape(self, url: str) -> Optional[ScraperResult]:
        """
        Public entry point. Wraps _scrape() with retries and error handling.
        Returns ScraperResult on success, None on failure.
        """
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    f"[{self.platform}] Attempt {attempt}/{MAX_RETRIES} for {url}"
                )
                start = time.time()
                result = await self._scrape(url)
                elapsed = time.time() - start
                if result:
                    result.compute_engagement_rate()
                    logger.info(
                        f"[{self.platform}] Success for {url} in {elapsed:.1f}s — "
                        f"followers={result.followers}"
                    )
                    return result
                else:
                    logger.warning(
                        f"[{self.platform}] Returned None for {url} on attempt {attempt}"
                    )
            except Exception as e:
                last_error = e
                logger.error(
                    f"[{self.platform}] Error on attempt {attempt} for {url}: {e}"
                )
            # Exponential backoff between retries
            if attempt < MAX_RETRIES:
                backoff = 2 ** attempt + random.uniform(0, 1)
                await asyncio.sleep(backoff)

        logger.error(
            f"[{self.platform}] All {MAX_RETRIES} attempts failed for {url}. "
            f"Last error: {last_error}"
        )
        return None


def parse_count(text: str) -> Optional[int]:
    """
    Parse human-readable follower/like counts.
    Examples: '12.5K' -> 12500, '1.2M' -> 1200000, '3,456' -> 3456
    """
    if not text:
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    try:
        multiplier = 1
        if text.upper().endswith("K"):
            multiplier = 1_000
            text = text[:-1]
        elif text.upper().endswith("M"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.upper().endswith("B"):
            multiplier = 1_000_000_000
            text = text[:-1]
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return None
