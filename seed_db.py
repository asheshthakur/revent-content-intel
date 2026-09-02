"""
Supabase Database Seeding Tool for Revent AI Lab.
Populates your Supabase project with 90 days of baseline historical data,
competitor benchmarks, trends, hashtags, and rolling calendar.
Run this once after executing schema.sql to give your team historical trendlines on Day 1.

Usage:
    export SUPABASE_URL="https://xyz.supabase.co"
    export SUPABASE_SERVICE_KEY="your-service-role-key"
    python seed_db.py
"""

import os
import sys
import logging
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mock_data import generate_seed_snapshots, generate_seed_trends, generate_seed_hashtags
from calendar_engine.generator import generate_calendar
from app.db import get_scraper_client, upsert_snapshot, upsert_calendar_entry, insert_trend, insert_hashtags

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_db")


def main():
    logger.info("🌱 Starting Supabase Seeding Script for Revent AI Lab...")

    try:
        client = get_scraper_client()
        logger.info("Connected to Supabase successfully!")
    except Exception as e:
        logger.error(f"Cannot connect to Supabase: {e}")
        logger.error("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        sys.exit(1)

    # 1. Seed Social Snapshots (90 days)
    logger.info("1/4: Seeding 90 days of social snapshots (Revent + 7 competitors)...")
    snaps = generate_seed_snapshots(days=90)
    success_snaps = 0
    for s in snaps:
        payload = {k: v for k, v in s.items() if k != "id"}
        if upsert_snapshot(payload):
            success_snaps += 1
    logger.info(f"✅ Upserted {success_snaps}/{len(snaps)} social snapshot rows.")

    # 2. Seed Trends (60 days)
    logger.info("2/4: Seeding 60 days of trend signals (Google, YouTube, Reddit, News)...")
    trends = generate_seed_trends(days=60)
    success_trends = 0
    for t in trends:
        if insert_trend(t):
            success_trends += 1
    logger.info(f"✅ Inserted {success_trends}/{len(trends)} trend rows.")

    # 3. Seed Hashtags
    logger.info("3/4: Seeding competitor hashtag frequencies...")
    hashtags = generate_seed_hashtags()
    if insert_hashtags(hashtags):
        logger.info(f"✅ Inserted {len(hashtags)} hashtag tracking records.")

    # 4. Seed Content Calendar (7-day rolling)
    logger.info("4/4: Seeding rolling 7-day content calendar...")
    cal_items = generate_calendar(trend_data=trends, existing_calendar=[], target_date=date.today())
    success_cal = 0
    for c in cal_items:
        payload = {k: v for k, v in c.items() if k != "id"}
        if upsert_calendar_entry(payload):
            success_cal += 1
    logger.info(f"✅ Generated and upserted {success_cal} calendar items.")

    logger.info("🎉 Database seeding complete! Launch your Streamlit app to view all populated charts.")


if __name__ == "__main__":
    main()
