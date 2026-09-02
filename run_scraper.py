"""
Daily Scraper Orchestrator for Revent AI Lab Content Intelligence Dashboard.

Executes as a standalone CLI job (triggered daily by GitHub Actions cron).
Steps:
1. Scrapes OUR_SOCIALS -> writes Day-0 row to social_snapshots (is_competitor=False)
2. Scrapes COMPETITORS -> writes Day-0 row to social_snapshots (is_competitor=True)
3. Extracts hashtags from competitor post captions -> writes to hashtag_tracking
4. Scrapes trending signals (pytrends, Google News, YouTube, Reddit) -> writes to trend_snapshots
5. Generates/rolls 7-day content calendar -> writes to content_calendar
6. Logs all outcomes to scrape_log table

Resilience Guarantee:
Every single platform and target is wrapped in try/except. Failures in one target
never interrupt or abort the remainder of the pipeline.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

# Ensure project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from scrapers.base import ScraperResult
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.x_scraper import XScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.youtube_scraper import YouTubeScraper
from scrapers.trends_scraper import scrape_all_trends
from scrapers.hashtag_extractor import extract_hashtags_from_raw_data
from calendar_engine.generator import generate_calendar
from app.db import (
    get_scraper_client,
    upsert_snapshot,
    upsert_calendar_entry,
    insert_trend,
    insert_hashtags,
    insert_scrape_log,
    read_trends,
    read_all_calendar,
    delete_old_calendar,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_scraper")


def get_scraper_for_platform(platform: str):
    """Instantiate scraper corresponding to platform name."""
    mapping = {
        "LinkedIn": LinkedInScraper,
        "Instagram": InstagramScraper,
        "X": XScraper,
        "Facebook": FacebookScraper,
        "YouTube": YouTubeScraper,
    }
    scraper_cls = mapping.get(platform)
    if scraper_cls:
        return scraper_cls()
    return None


async def scrape_target(
    platform: str,
    handle_url: str,
    is_competitor: bool,
    competitor_name: Optional[str] = None,
) -> Optional[ScraperResult]:
    """Scrapes a single social media target with timing and scrape_log recording."""
    start_time = time.time()
    scraper = get_scraper_for_platform(platform)

    if not scraper:
        logger.warning(f"No scraper implemented for platform: {platform}")
        return None

    result = None
    status = "failed"
    error_msg = None

    try:
        logger.info(f"Scraping [{platform}] -> {handle_url} (Competitor: {competitor_name})")
        result = await scraper.scrape(handle_url)
        if result:
            status = "success"
        else:
            status = "skipped"
            error_msg = "Scraper returned empty result (likely blocked or rate limited)"
    except Exception as e:
        status = "failed"
        error_msg = str(e)
        logger.error(f"Scraper crashed for [{platform}] {handle_url}: {e}")

    duration = time.time() - start_time

    # Record execution log in Supabase
    try:
        insert_scrape_log({
            "date": date.today().isoformat(),
            "platform": platform,
            "handle": handle_url,
            "status": status,
            "error_message": error_msg,
            "duration_seconds": round(duration, 2),
        })
    except Exception as log_err:
        logger.warning(f"Could not persist scrape log: {log_err}")

    # If successful, write snapshot to social_snapshots
    if result:
        snapshot_row = {
            "platform": platform,
            "handle": handle_url,
            "date": date.today().isoformat(),  # Day 0
            "followers": result.followers,
            "engagement_rate": result.engagement_rate,
            "likes_avg": result.likes_avg,
            "comments_avg": result.comments_avg,
            "shares_avg": result.shares_avg,
            "posts_scraped": result.posts_scraped,
            "post_frequency": result.post_frequency,
            "is_competitor": is_competitor,
            "competitor_name": competitor_name,
            "raw_data": result.raw_data,
        }
        try:
            upsert_snapshot(snapshot_row)
            logger.info(f"✅ Saved snapshot for {platform} ({handle_url}) to Supabase")
        except Exception as db_err:
            logger.error(f"Failed to save snapshot to DB: {db_err}")

    return result


async def run_social_scrapes():
    """Run all social profile scrapes for Revent and tracked competitors."""
    logger.info("==================================================")
    logger.info("STEP 1: Scraping Revent AI Lab Social Channels")
    logger.info("==================================================")

    for platform, url in config.OUR_SOCIALS.items():
        try:
            await scrape_target(
                platform=platform,
                handle_url=url,
                is_competitor=False,
                competitor_name=None,
            )
        except Exception as e:
            logger.error(f"Failed to scrape Revent social {platform}: {e}")

    logger.info("==================================================")
    logger.info("STEP 2: Scraping Competitors")
    logger.info("==================================================")

    for comp_name, platforms in config.COMPETITORS.items():
        for platform, url in platforms.items():
            try:
                res = await scrape_target(
                    platform=platform,
                    handle_url=url,
                    is_competitor=True,
                    competitor_name=comp_name,
                )

                # If competitor posts were scraped, extract and save hashtags
                if res and res.raw_data:
                    ht_counts = extract_hashtags_from_raw_data(res.raw_data)
                    if ht_counts:
                        ht_rows = [
                            {
                                "date": date.today().isoformat(),
                                "handle": url,
                                "platform": platform,
                                "competitor_name": comp_name,
                                "hashtag": tag,
                                "frequency": freq,
                            }
                            for tag, freq in ht_counts.items()
                        ]
                        insert_hashtags(ht_rows)
                        logger.info(f"Saved {len(ht_rows)} hashtags for competitor {comp_name}")
            except Exception as e:
                logger.error(f"Failed competitor scrape {comp_name} ({platform}): {e}")


def run_trend_pipeline():
    """Harvest trending keywords/topics and store in trend_snapshots."""
    logger.info("==================================================")
    logger.info("STEP 3: Scraping Trends & Signals")
    logger.info("==================================================")

    try:
        trend_items = scrape_all_trends()
        today_str = date.today().isoformat()

        saved_count = 0
        for item in trend_items:
            row = {
                "date": today_str,
                "keyword": item.get("keyword"),
                "source": item.get("source"),
                "score": item.get("score"),
                "title": item.get("title"),
                "url": item.get("url"),
                "metadata": item.get("metadata", {}),
            }
            if insert_trend(row):
                saved_count += 1

        logger.info(f"✅ Successfully inserted {saved_count} trend snapshots")
        return trend_items
    except Exception as e:
        logger.error(f"Trend pipeline failed: {e}")
        return []


def run_calendar_pipeline(trend_data: List[Dict]):
    """
    Rolls the 7-day content calendar forward by 1 day.
    Drops entries older than yesterday (if not marked manual override).
    Appends the newest day's schedule.
    """
    logger.info("==================================================")
    logger.info("STEP 4: Rolling 7-Day Content Calendar")
    logger.info("==================================================")

    try:
        # Cleanup expired days from calendar
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        delete_old_calendar(before_date=yesterday_str)

        # Retrieve existing calendar entries from database
        existing_cal = read_all_calendar()

        # If no trend data provided, try reading past 7 days from DB
        if not trend_data:
            trend_data = read_trends(days=7)

        # Generate rolled 7-day calendar
        updated_calendar = generate_calendar(
            trend_data=trend_data,
            existing_calendar=existing_cal,
            target_date=date.today(),
        )

        # Save all generated items
        saved_cal = 0
        for entry in updated_calendar:
            if upsert_calendar_entry(entry):
                saved_cal += 1

        logger.info(f"✅ Content calendar successfully updated ({saved_cal} active entries)")
    except Exception as e:
        logger.error(f"Calendar generation pipeline failed: {e}")


async def main_pipeline():
    logger.info("🚀 Starting Revent AI Lab Daily Scraping Pipeline")
    start_total = time.time()

    # Step 1 & 2: Social Scrapes
    await run_social_scrapes()

    # Step 3: Trend Pipeline
    trend_data = run_trend_pipeline()

    # Step 4: Content Calendar Pipeline
    run_calendar_pipeline(trend_data)

    elapsed = time.time() - start_total
    logger.info(f"🏁 Daily Scraper Pipeline finished in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main_pipeline())
