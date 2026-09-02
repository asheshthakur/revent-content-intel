"""
Instagram public profile scraper (Playwright, no login).

FRAGILITY NOTE: Instagram frequently shows login walls for unauthenticated
visitors. The scraper attempts multiple strategies: og:description meta tag,
page source JSON blobs, and visible DOM selectors. Expect frequent failures.
"""

import json
import logging
import re
from typing import Optional

from playwright.async_api import async_playwright

from scrapers.base import BaseScraper, ScraperResult, parse_count

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    platform = "Instagram"

    async def _scrape(self, url: str) -> Optional[ScraperResult]:
        async with async_playwright() as pw:
            ctx = await self._create_context(pw)
            # Don't block images on Instagram — we need the page to render
            page = await ctx.new_page()
            try:
                await page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                content = await page.content()
                page_text = await page.evaluate("() => document.body?.innerText || ''")

                # ── Detect login wall ────────────────────────────
                if "log in" in page_text.lower()[:500] and "followers" not in page_text.lower():
                    logger.warning(f"[Instagram] Login wall likely for {url}")

                followers = None
                posts_count = None
                likes_list = []
                comments_list = []
                captions = []

                # ── Strategy 1: og:description meta tag ──────────
                # Format: "X Followers, Y Following, Z Posts - ..."
                meta = await page.query_selector('meta[property="og:description"]')
                if meta:
                    meta_content = await meta.get_attribute("content") or ""
                    match = re.search(
                        r'([\d,\.]+[KMB]?)\s*Followers',
                        meta_content,
                        re.IGNORECASE,
                    )
                    if match:
                        followers = parse_count(match.group(1))
                    posts_match = re.search(
                        r'([\d,\.]+[KMB]?)\s*Posts',
                        meta_content,
                        re.IGNORECASE,
                    )
                    if posts_match:
                        posts_count = parse_count(posts_match.group(1))

                # ── Strategy 2: JSON in page source ──────────────
                if not followers:
                    # Look for _sharedData or additionalDataLoaded JSON
                    json_patterns = [
                        r'window\._sharedData\s*=\s*({.*?});</script>',
                        r'"edge_followed_by":\s*\{\s*"count":\s*(\d+)',
                    ]
                    for pattern in json_patterns:
                        match = re.search(pattern, content)
                        if match:
                            try:
                                if pattern.startswith('"edge_followed_by'):
                                    followers = int(match.group(1))
                                else:
                                    data = json.loads(match.group(1))
                                    user = (
                                        data.get("entry_data", {})
                                        .get("ProfilePage", [{}])[0]
                                        .get("graphql", {})
                                        .get("user", {})
                                    )
                                    followers = user.get("edge_followed_by", {}).get("count")
                            except (json.JSONDecodeError, IndexError, KeyError):
                                pass
                            if followers:
                                break

                # ── Strategy 3: visible DOM selectors ────────────
                if not followers:
                    # Various selector patterns Instagram has used
                    selectors = [
                        "header section ul li:first-child span span",
                        "header section ul li:first-child button span",
                        "[title]",  # sometimes follower count is in title attr
                    ]
                    for sel in selectors:
                        elements = await page.query_selector_all(sel)
                        for el in elements:
                            text = await el.inner_text()
                            title = await el.get_attribute("title") or ""
                            for t in [title, text]:
                                if re.search(r'[\d,\.]+', t):
                                    candidate = parse_count(t.strip())
                                    if candidate and candidate > 10:
                                        # Heuristic: follower count is usually the largest number
                                        if not followers or candidate > followers:
                                            followers = candidate

                    # Look for follower text in page_text
                    match = re.search(
                        r'([\d,\.]+[KMB]?)\s*[Ff]ollowers',
                        page_text,
                    )
                    if match:
                        followers = parse_count(match.group(1))

                # ── Extract engagement from recent posts ─────────
                # Try to extract like counts from the grid
                # Instagram post pages sometimes show like counts
                post_links = await page.query_selector_all('a[href*="/p/"]')
                seen_hrefs = set()
                for link in post_links[:8]:
                    href = await link.get_attribute("href")
                    if href and href not in seen_hrefs:
                        seen_hrefs.add(href)

                # Visit first few posts for engagement data
                for href in list(seen_hrefs)[:4]:
                    try:
                        await self._random_delay()
                        post_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                        post_page = await ctx.new_page()
                        await post_page.goto(post_url, timeout=20_000, wait_until="domcontentloaded")
                        await post_page.wait_for_timeout(2000)
                        post_content = await post_page.content()
                        post_text = await post_page.evaluate("() => document.body?.innerText || ''")

                        # Likes
                        like_match = re.search(
                            r'([\d,\.]+[KMB]?)\s*likes?',
                            post_text,
                            re.IGNORECASE,
                        )
                        if like_match:
                            count = parse_count(like_match.group(1))
                            if count is not None:
                                likes_list.append(count)

                        # Comments
                        comment_match = re.search(
                            r'([\d,]+)\s*comments?',
                            post_text,
                            re.IGNORECASE,
                        )
                        if comment_match:
                            comments_list.append(
                                int(comment_match.group(1).replace(",", ""))
                            )

                        # Caption
                        caption_match = re.search(
                            r'"edge_media_to_caption".*?"text":"(.*?)"',
                            post_content,
                        )
                        if caption_match:
                            captions.append(caption_match.group(1)[:500])
                        else:
                            # Try visible caption
                            cap_el = await post_page.query_selector(
                                "div._a9zs span, h1._ap3a"
                            )
                            if cap_el:
                                cap_text = await cap_el.inner_text()
                                if cap_text:
                                    captions.append(cap_text[:500])

                        await post_page.close()
                    except Exception as e:
                        logger.debug(f"[Instagram] Error on post {href}: {e}")
                        continue

                likes_avg = sum(likes_list) / len(likes_list) if likes_list else None
                comments_avg = (
                    sum(comments_list) / len(comments_list) if comments_list else None
                )

                return ScraperResult(
                    platform=self.platform,
                    handle=url,
                    followers=followers,
                    likes_avg=likes_avg,
                    comments_avg=comments_avg,
                    posts_scraped=len(likes_list),
                    raw_data={
                        "likes_list": likes_list,
                        "comments_list": comments_list,
                        "captions": captions,
                        "posts_count": posts_count,
                        "url": url,
                    },
                    captions=captions,
                )
            finally:
                await self._close()
