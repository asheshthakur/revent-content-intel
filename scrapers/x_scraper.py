"""
X (Twitter) public profile scraper.

Uses Nitter instances as primary (more scraping-friendly), with direct
X.com Playwright scrape as fallback.

FRAGILITY NOTE: Nitter instances go up and down frequently. X.com itself
is very aggressive with anti-bot measures. This scraper maintains a list
of fallback Nitter instances and tries them in order.
"""

import logging
import re
from typing import Optional, List

from playwright.async_api import async_playwright

from scrapers.base import BaseScraper, ScraperResult, parse_count

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import NITTER_INSTANCES

logger = logging.getLogger(__name__)


class XScraper(BaseScraper):
    platform = "X"

    def _extract_handle(self, url: str) -> str:
        """Extract @handle from X URL."""
        # https://x.com/Revent_Lab -> Revent_Lab
        parts = url.rstrip("/").split("/")
        return parts[-1]

    async def _try_nitter(self, handle: str) -> Optional[ScraperResult]:
        """Try scraping via Nitter instances (more reliable for public data)."""
        for instance in NITTER_INSTANCES:
            try:
                nitter_url = f"{instance}/{handle}"
                async with async_playwright() as pw:
                    ctx = await self._create_context(pw)
                    page = await ctx.new_page()
                    await page.goto(nitter_url, timeout=15_000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
                    page_text = await page.evaluate("() => document.body?.innerText || ''")

                    # Check if instance is actually up
                    if "not found" in page_text.lower() or len(page_text) < 50:
                        await self._close()
                        continue

                    followers = None
                    likes_list = []
                    retweets_list = []
                    comments_list = []
                    captions = []

                    # ── Extract follower count ───────────────────
                    # Nitter shows "X Followers" in the profile stats
                    match = re.search(
                        r'([\d,\.]+[KMB]?)\s*Followers',
                        page_text,
                        re.IGNORECASE,
                    )
                    if match:
                        followers = parse_count(match.group(1))

                    # ── Extract tweets ───────────────────────────
                    tweets = await page.query_selector_all(".timeline-item, .tweet-body")
                    for tweet in tweets[:10]:
                        try:
                            tweet_text = await tweet.inner_text()

                            # Likes (Nitter shows as hearts/favs)
                            like_match = re.search(r'(\d+)\s*$', tweet_text)
                            fav_els = await tweet.query_selector_all(
                                ".icon-heart, .tweet-stat"
                            )
                            for el in fav_els:
                                text = await el.inner_text()
                                count = parse_count(text.strip())
                                if count is not None:
                                    likes_list.append(count)
                                    break

                            # Retweets
                            rt_els = await tweet.query_selector_all(
                                ".icon-retweet, .tweet-stat"
                            )
                            for el in rt_els:
                                text = await el.inner_text()
                                count = parse_count(text.strip())
                                if count is not None:
                                    retweets_list.append(count)
                                    break

                            # Caption
                            content_el = await tweet.query_selector(
                                ".tweet-content, .tweet-body"
                            )
                            if content_el:
                                caption = await content_el.inner_text()
                                captions.append(caption[:500])
                        except Exception:
                            continue

                    await self._close()

                    if followers is not None:
                        likes_avg = sum(likes_list) / len(likes_list) if likes_list else None
                        comments_avg = sum(comments_list) / len(comments_list) if comments_list else None
                        shares_avg = sum(retweets_list) / len(retweets_list) if retweets_list else None

                        return ScraperResult(
                            platform=self.platform,
                            handle=f"https://x.com/{handle}",
                            followers=followers,
                            likes_avg=likes_avg,
                            comments_avg=comments_avg,
                            shares_avg=shares_avg,
                            posts_scraped=len(likes_list),
                            raw_data={
                                "source": "nitter",
                                "instance": instance,
                                "likes_list": likes_list,
                                "retweets_list": retweets_list,
                                "captions": captions,
                            },
                            captions=captions,
                        )
            except Exception as e:
                logger.debug(f"[X] Nitter instance {instance} failed: {e}")
                try:
                    await self._close()
                except Exception:
                    pass
                continue
        return None

    async def _try_xcom(self, url: str, handle: str) -> Optional[ScraperResult]:
        """Fallback: scrape directly from X.com."""
        async with async_playwright() as pw:
            ctx = await self._create_context(pw)
            page = await ctx.new_page()
            try:
                await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)

                page_text = await page.evaluate("() => document.body?.innerText || ''")
                content = await page.content()

                followers = None
                likes_list = []
                retweets_list = []
                captions = []

                # ── Extract follower count ───────────────────────
                # X shows followers in aria-labels or visible text
                match = re.search(
                    r'([\d,\.]+[KMB]?)\s*Followers',
                    page_text,
                    re.IGNORECASE,
                )
                if match:
                    followers = parse_count(match.group(1))

                # Try aria-label approach
                if not followers:
                    links = await page.query_selector_all('a[href*="followers"]')
                    for link in links:
                        text = await link.inner_text()
                        match = re.search(r'([\d,\.]+[KMB]?)', text)
                        if match:
                            followers = parse_count(match.group(1))
                            break

                # ── Extract tweet engagement ─────────────────────
                # Look for tweet articles
                articles = await page.query_selector_all('article[data-testid="tweet"]')
                for article in articles[:10]:
                    try:
                        article_text = await article.inner_text()
                        # Like counts often in aria-labels
                        groups = await article.query_selector_all('[role="group"]')
                        for group in groups:
                            aria = await group.get_attribute("aria-label") or ""
                            like_match = re.search(r'(\d+)\s*likes?', aria, re.IGNORECASE)
                            if like_match:
                                likes_list.append(int(like_match.group(1)))
                            rt_match = re.search(r'(\d+)\s*re(?:tweets?|posts?)', aria, re.IGNORECASE)
                            if rt_match:
                                retweets_list.append(int(rt_match.group(1)))

                        # Caption from tweet text
                        text_el = await article.query_selector('[data-testid="tweetText"]')
                        if text_el:
                            captions.append((await text_el.inner_text())[:500])
                    except Exception:
                        continue

                likes_avg = sum(likes_list) / len(likes_list) if likes_list else None
                shares_avg = sum(retweets_list) / len(retweets_list) if retweets_list else None

                return ScraperResult(
                    platform=self.platform,
                    handle=url,
                    followers=followers,
                    likes_avg=likes_avg,
                    comments_avg=None,
                    shares_avg=shares_avg,
                    posts_scraped=len(likes_list),
                    raw_data={
                        "source": "x.com",
                        "likes_list": likes_list,
                        "retweets_list": retweets_list,
                        "captions": captions,
                    },
                    captions=captions,
                )
            finally:
                await self._close()

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        handle = self._extract_handle(url)

        # Try Nitter first (more reliable for scraping)
        result = await self._try_nitter(handle)
        if result and result.followers:
            return result

        await self._random_delay()

        # Fallback to direct X.com
        return await self._try_xcom(url, handle)
