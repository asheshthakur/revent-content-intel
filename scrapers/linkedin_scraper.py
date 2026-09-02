"""
LinkedIn public company page scraper (Playwright, no login).

FRAGILITY NOTE: LinkedIn is the most aggressive at blocking unauthenticated
scraping. Public company pages sometimes show a login wall. The scraper
detects this and logs a skip. Expect this scraper to fail frequently.
"""

import logging
import re
from typing import Optional

from playwright.async_api import async_playwright

from scrapers.base import BaseScraper, ScraperResult, parse_count

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    platform = "LinkedIn"

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        async with async_playwright() as pw:
            ctx = await self._create_context(pw)
            page = await ctx.new_page()
            try:
                # Navigate to the public company page
                await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)  # let JS render

                content = await page.content()

                # ── Detect login wall ────────────────────────────
                if "authwall" in content.lower() or "sign in" in (await page.title()).lower():
                    logger.warning(f"[LinkedIn] Login wall detected for {url}")
                    # Try the /about page as fallback
                    about_url = url.rstrip("/") + "/about/"
                    await self._random_delay()
                    await page.goto(about_url, timeout=30_000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                    content = await page.content()
                    if "authwall" in content.lower():
                        logger.error(f"[LinkedIn] Login wall persists for {url}")
                        return None

                # ── Extract follower count ───────────────────────
                followers = None

                # Method 1: Look for "X followers" text pattern in page
                follower_patterns = [
                    r'([\d,\.]+[KMB]?)\s*followers',
                    r'([\d,\.]+[KMB]?)\s*Followers',
                ]
                for pattern in follower_patterns:
                    match = re.search(pattern, content)
                    if match:
                        followers = parse_count(match.group(1))
                        break

                # Method 2: Try meta description
                if not followers:
                    meta = await page.query_selector('meta[property="og:description"]')
                    if meta:
                        meta_content = await meta.get_attribute("content") or ""
                        for pattern in follower_patterns:
                            match = re.search(pattern, meta_content, re.IGNORECASE)
                            if match:
                                followers = parse_count(match.group(1))
                                break

                # Method 3: Try specific selectors
                if not followers:
                    selectors = [
                        "span.org-top-card-summary__follower-count",
                        "[data-test-id='about-us__followers-count']",
                        ".top-card-layout__first-subline",
                    ]
                    for sel in selectors:
                        elem = await page.query_selector(sel)
                        if elem:
                            text = await elem.inner_text()
                            match = re.search(r'([\d,\.]+[KMB]?)', text)
                            if match:
                                followers = parse_count(match.group(1))
                                break

                # ── Extract recent post engagement ───────────────
                likes_list = []
                comments_list = []
                captions = []

                # Try to find post activity section
                post_selectors = [
                    "div.feed-shared-update-v2",
                    "article.feed-shared-update",
                    "div.org-update-card",
                    "li.org-updates__update-card",
                ]
                posts = []
                for sel in post_selectors:
                    posts = await page.query_selector_all(sel)
                    if posts:
                        break

                for post in posts[:6]:  # sample up to 6 recent posts
                    try:
                        # Extract like count
                        like_el = await post.query_selector(
                            "span.social-details-social-counts__reactions-count, "
                            "span.feed-shared-social-counts__num-likes"
                        )
                        if like_el:
                            like_text = await like_el.inner_text()
                            count = parse_count(like_text)
                            if count is not None:
                                likes_list.append(count)

                        # Extract comment count
                        comment_el = await post.query_selector(
                            "button.social-details-social-counts__comments, "
                            "span.feed-shared-social-counts__num-comments"
                        )
                        if comment_el:
                            comment_text = await comment_el.inner_text()
                            match = re.search(r'([\d,]+)', comment_text)
                            if match:
                                comments_list.append(int(match.group(1).replace(",", "")))

                        # Extract caption text for content analysis
                        caption_el = await post.query_selector(
                            "span.feed-shared-text__text-view, "
                            "div.feed-shared-update-v2__description"
                        )
                        if caption_el:
                            caption = await caption_el.inner_text()
                            captions.append(caption[:500])
                    except Exception as e:
                        logger.debug(f"[LinkedIn] Error parsing post: {e}")
                        continue

                likes_avg = sum(likes_list) / len(likes_list) if likes_list else None
                comments_avg = sum(comments_list) / len(comments_list) if comments_list else None

                return ScraperResult(
                    platform=self.platform,
                    handle=url,
                    followers=followers,
                    likes_avg=likes_avg,
                    comments_avg=comments_avg,
                    shares_avg=None,  # LinkedIn doesn't show share counts publicly
                    posts_scraped=len(likes_list),
                    raw_data={
                        "likes_list": likes_list,
                        "comments_list": comments_list,
                        "captions": captions,
                        "url": url,
                    },
                    captions=captions,
                )
            finally:
                await self._close()
