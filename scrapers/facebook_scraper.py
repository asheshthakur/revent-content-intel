"""
Facebook public page scraper (Playwright, no login).

FRAGILITY NOTE: Facebook is heavy with JS rendering and anti-bot measures.
Public pages often require long wait times and may show a cookie consent
wall or login prompt. This scraper attempts to extract page likes/followers
from the visible page header.
"""

import logging
import re
from typing import Optional

from playwright.async_api import async_playwright

from scrapers.base import BaseScraper, ScraperResult, parse_count

logger = logging.getLogger(__name__)


class FacebookScraper(BaseScraper):
    platform = "Facebook"

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        async with async_playwright() as pw:
            ctx = await self._create_context(pw)
            page = await ctx.new_page()
            try:
                await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                # ── Dismiss cookie consent if present ────────────
                try:
                    cookie_btns = await page.query_selector_all(
                        'button[data-cookiebanner="accept_button"], '
                        'button[title="Allow all cookies"], '
                        'button:has-text("Accept All"), '
                        'button:has-text("Allow")'
                    )
                    for btn in cookie_btns:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    pass

                content = await page.content()
                page_text = await page.evaluate("() => document.body?.innerText || ''")

                followers = None
                page_likes = None
                likes_list = []
                comments_list = []
                shares_list = []
                captions = []

                # ── Extract follower/like count ──────────────────
                # Facebook pages show "X people like this" and "X people follow this"
                follower_patterns = [
                    r'([\d,\.]+[KMB]?)\s*(?:people\s+)?follow',
                    r'([\d,\.]+[KMB]?)\s*followers',
                    r'([\d,\.]+[KMB]?)\s*people like this',
                    r'([\d,\.]+[KMB]?)\s*likes',
                ]
                for pattern in follower_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        count = parse_count(match.group(1))
                        if count and count > 0:
                            if "follow" in pattern:
                                followers = count
                            elif "like" in pattern:
                                page_likes = count
                            if followers:
                                break

                # Use page_likes as fallback for followers
                if not followers and page_likes:
                    followers = page_likes

                # ── Try og:description meta ──────────────────────
                if not followers:
                    meta = await page.query_selector('meta[property="og:description"]')
                    if meta:
                        meta_content = await meta.get_attribute("content") or ""
                        for pattern in follower_patterns:
                            match = re.search(pattern, meta_content, re.IGNORECASE)
                            if match:
                                followers = parse_count(match.group(1))
                                if followers:
                                    break

                # ── Extract recent post engagement ───────────────
                # Facebook public page posts
                post_containers = await page.query_selector_all(
                    '[role="article"], div[data-ad-preview="message"]'
                )
                for container in post_containers[:6]:
                    try:
                        container_text = await container.inner_text()

                        # Likes / reactions
                        like_match = re.search(
                            r'(\d[\d,]*)\s*$',
                            container_text.split("\n")[0] if "\n" in container_text else "",
                        )
                        # Look for reaction counts in aria-labels
                        reaction_el = await container.query_selector(
                            'span[aria-label*="reaction"], '
                            'span[aria-label*="like"]'
                        )
                        if reaction_el:
                            aria = await reaction_el.get_attribute("aria-label") or ""
                            count_match = re.search(r'([\d,]+)', aria)
                            if count_match:
                                likes_list.append(
                                    int(count_match.group(1).replace(",", ""))
                                )

                        # Comments
                        comment_match = re.search(
                            r'(\d[\d,]*)\s*comments?',
                            container_text,
                            re.IGNORECASE,
                        )
                        if comment_match:
                            comments_list.append(
                                int(comment_match.group(1).replace(",", ""))
                            )

                        # Shares
                        share_match = re.search(
                            r'(\d[\d,]*)\s*shares?',
                            container_text,
                            re.IGNORECASE,
                        )
                        if share_match:
                            shares_list.append(
                                int(share_match.group(1).replace(",", ""))
                            )

                        # Caption
                        if len(container_text) > 20:
                            captions.append(container_text[:500])
                    except Exception as e:
                        logger.debug(f"[Facebook] Error parsing post: {e}")
                        continue

                likes_avg = sum(likes_list) / len(likes_list) if likes_list else None
                comments_avg = (
                    sum(comments_list) / len(comments_list) if comments_list else None
                )
                shares_avg = (
                    sum(shares_list) / len(shares_list) if shares_list else None
                )

                return ScraperResult(
                    platform=self.platform,
                    handle=url,
                    followers=followers,
                    likes_avg=likes_avg,
                    comments_avg=comments_avg,
                    shares_avg=shares_avg,
                    posts_scraped=len(likes_list),
                    raw_data={
                        "likes_list": likes_list,
                        "comments_list": comments_list,
                        "shares_list": shares_list,
                        "captions": captions,
                        "page_likes": page_likes,
                        "url": url,
                    },
                    captions=captions,
                )
            finally:
                await self._close()
