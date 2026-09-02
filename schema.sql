-- ============================================================
-- Revent AI Lab — Content Intelligence Dashboard
-- Supabase (PostgreSQL) Schema
-- Run this in your Supabase SQL Editor to create all tables.
-- ============================================================

-- Enable UUID extension (available by default on Supabase)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. social_snapshots
--    Daily per-platform follower & engagement data.
--    One row per platform per handle per day.
-- ============================================================
CREATE TABLE IF NOT EXISTS social_snapshots (
    id            BIGSERIAL PRIMARY KEY,
    platform      TEXT        NOT NULL,                    -- 'Facebook','Instagram','YouTube','LinkedIn','X'
    handle        TEXT        NOT NULL,                    -- profile URL or handle
    date          DATE        NOT NULL DEFAULT CURRENT_DATE,
    followers     INTEGER,
    engagement_rate REAL,                                  -- avg (likes+comments+shares)/followers
    likes_avg     REAL,                                    -- avg likes per recent post
    comments_avg  REAL,
    shares_avg    REAL,
    posts_scraped INTEGER     DEFAULT 0,                   -- how many recent posts were sampled
    post_frequency REAL,                                   -- estimated posts per week
    is_competitor BOOLEAN     DEFAULT FALSE,
    competitor_name TEXT,                                   -- NULL for our own accounts
    raw_data      JSONB,                                   -- full scraped payload for debugging
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, handle, date)
);

-- ============================================================
-- 2. content_calendar
--    Rolling 7-day content plan, one row per scheduled idea.
-- ============================================================
CREATE TABLE IF NOT EXISTS content_calendar (
    id               BIGSERIAL PRIMARY KEY,
    date             DATE    NOT NULL,
    platform         TEXT    NOT NULL,
    format           TEXT    NOT NULL,                     -- 'static','carousel','short-form','long-form','story'
    topic            TEXT    NOT NULL,
    hook             TEXT,
    body             TEXT,                                  -- key points / structure
    cta              TEXT,
    best_time        TEXT,                                  -- e.g. '10:00 AM GST'
    source_keyword   TEXT,                                  -- trending keyword that inspired this idea
    is_manual_override BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, platform, format, topic)
);

-- ============================================================
-- 3. trend_snapshots
--    Daily keyword / topic trend scores from multiple sources.
-- ============================================================
CREATE TABLE IF NOT EXISTS trend_snapshots (
    id         BIGSERIAL PRIMARY KEY,
    date       DATE    NOT NULL DEFAULT CURRENT_DATE,
    keyword    TEXT    NOT NULL,
    source     TEXT    NOT NULL,                            -- 'google_trends','google_news','youtube','reddit'
    score      REAL,                                        -- normalised relevance 0-100
    title      TEXT,                                        -- article / video title
    url        TEXT,                                        -- source URL
    metadata   JSONB,                                       -- extra (tags, subreddit, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 4. hashtag_tracking
--    Hashtag frequency extracted from competitor posts.
-- ============================================================
CREATE TABLE IF NOT EXISTS hashtag_tracking (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE    NOT NULL DEFAULT CURRENT_DATE,
    handle          TEXT    NOT NULL,
    platform        TEXT    NOT NULL,
    competitor_name TEXT,
    hashtag         TEXT    NOT NULL,
    frequency       INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 5. scrape_log
--    Operational log — one row per scrape attempt for debugging.
-- ============================================================
CREATE TABLE IF NOT EXISTS scrape_log (
    id               BIGSERIAL PRIMARY KEY,
    date             DATE    NOT NULL DEFAULT CURRENT_DATE,
    platform         TEXT,
    handle           TEXT,
    status           TEXT    NOT NULL,                      -- 'success','failed','skipped'
    error_message    TEXT,
    duration_seconds REAL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Indexes for common query patterns
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_snapshots_date          ON social_snapshots(date);
CREATE INDEX IF NOT EXISTS idx_snapshots_platform      ON social_snapshots(platform, is_competitor);
CREATE INDEX IF NOT EXISTS idx_snapshots_handle_date   ON social_snapshots(handle, date);
CREATE INDEX IF NOT EXISTS idx_calendar_date           ON content_calendar(date);
CREATE INDEX IF NOT EXISTS idx_trends_date_keyword     ON trend_snapshots(date, keyword);
CREATE INDEX IF NOT EXISTS idx_trends_source           ON trend_snapshots(source);
CREATE INDEX IF NOT EXISTS idx_hashtags_handle         ON hashtag_tracking(handle, date);
CREATE INDEX IF NOT EXISTS idx_scrape_log_date         ON scrape_log(date, status);
