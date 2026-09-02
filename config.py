"""
Global configuration for the Revent AI Lab Content Intelligence Dashboard.
All social handles, competitor definitions, niche keywords, scraping
parameters, and posting-time heuristics live here.
"""

from typing import Dict, List, Tuple

# ── Our social profiles ──────────────────────────────────────────────
OUR_SOCIALS: Dict[str, str] = {
    "Facebook":  "https://www.facebook.com/revent.uae/",
    "Instagram": "https://www.instagram.com/revent.uae/",
    "YouTube":   "https://www.youtube.com/@revent",
    "LinkedIn":  "https://www.linkedin.com/company/revent-fzco/",
}

# ── Competitor profiles ──────────────────────────────────────────────
COMPETITORS: Dict[str, Dict[str, str]] = {
    "Implement AI": {
        "LinkedIn": "https://www.linkedin.com/company/implement-ai",
        "X":        "https://x.com/ImplementAI",
    },
    "Anvenssa AI": {
        "LinkedIn":  "https://www.linkedin.com/company/agentflowwai/",
        "Instagram": "https://www.instagram.com/anvenssa_ai/",
    },
    "Maqsam": {
        "X":         "https://x.com/MaqsamHQ",
        "Instagram": "https://www.instagram.com/maqsamhq/",
    },
    "Lucidya": {
        "LinkedIn":  "https://www.linkedin.com/company/lucidya/",
        "X":         "https://x.com/lucidyaai",
        "Instagram": "https://www.instagram.com/lucidyaai",
    },
    "Dataiku": {
        "LinkedIn":  "https://www.linkedin.com/company/dataiku/",
        "X":         "https://x.com/dataiku",
        "Instagram": "https://www.instagram.com/dataiku",
    },
    "Ahrefs": {
        "LinkedIn":  "https://www.linkedin.com/company/ahrefs",
        "X":         "https://x.com/ahrefs",
        "Instagram": "https://www.instagram.com/ahrefs",
    },
    "Semrush": {
        "LinkedIn":  "https://www.linkedin.com/company/semrush/",
        "X":         "https://x.com/semrush",
        "Instagram": "https://www.instagram.com/semrush",
    },
}

# ── Niche keywords for trend tracking ────────────────────────────────
NICHE_KEYWORDS: List[str] = [
    "AI labs",
    "AI platform",
    "AI agents",
    "agentic AI",
    "AI bot",
    "AI automation SME",
    "business AI UAE",
    "AI workflow automation",
]

# ── Scraping parameters ─────────────────────────────────────────────
SCRAPE_DELAY_RANGE: Tuple[float, float] = (2.0, 5.0)   # random seconds between requests
SCRAPE_TIMEOUT: float = 30.0                             # page-load timeout in seconds
MAX_RETRIES: int = 2                                      # retries per target on failure
PLAYWRIGHT_HEADLESS: bool = True

# Rotating pool of realistic User-Agent strings
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}

# ── Nitter fallback instances (for X/Twitter scraping) ───────────────
# These go up and down — the scraper tries them in order.
NITTER_INSTANCES: List[str] = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.woodland.cafe",
]

# ── GCC B2B / SME best-time-to-post heuristics (GST = UTC+4) ────────
# These are editable defaults based on published GCC B2B benchmarks.
# Refine later using real engagement data from Tab 1.
GCC_BEST_TIMES: Dict[str, Dict] = {
    "LinkedIn": {
        "best_days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
        "best_times": ["08:00", "09:00", "10:00"],
        "timezone": "Asia/Dubai",
        "display": "8:00–10:00 AM GST, Sun–Thu",
    },
    "Instagram": {
        "best_days": ["Sunday", "Monday", "Tuesday", "Wednesday"],
        "best_times": ["12:00", "13:00", "14:00", "19:00", "20:00", "21:00"],
        "timezone": "Asia/Dubai",
        "display": "12:00–2:00 PM or 7:00–9:00 PM GST, Sun–Wed",
    },
    "X": {
        "best_days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
        "best_times": ["09:00", "10:00", "11:00"],
        "timezone": "Asia/Dubai",
        "display": "9:00–11:00 AM GST, Sun–Thu",
    },
    "Facebook": {
        "best_days": ["Sunday", "Monday", "Tuesday", "Wednesday"],
        "best_times": ["13:00", "14:00", "15:00"],
        "timezone": "Asia/Dubai",
        "display": "1:00–3:00 PM GST, Sun–Wed",
    },
    "YouTube": {
        "best_days": ["Sunday", "Tuesday", "Thursday"],
        "best_times": ["17:00", "18:00", "19:00"],
        "timezone": "Asia/Dubai",
        "display": "5:00–7:00 PM GST, Sun/Tue/Thu",
    },
}

# ── Content calendar cadence rules ───────────────────────────────────
# Max items per platform per 7-day window, by format.
CALENDAR_CADENCE: Dict[str, Dict[str, int]] = {
    "YouTube": {
        "long-form": 1,
        "short-form": 2,
    },
    "Instagram": {
        "short-form": 2,
        "carousel": 2,
        "static": 2,
    },
    "LinkedIn": {
        "short-form": 2,
        "carousel": 2,
        "static": 2,
    },
    "X": {
        "short-form": 2,
        "carousel": 1,
        "static": 2,
    },
    "Facebook": {
        "short-form": 2,
        "carousel": 2,
        "static": 2,
    },
}

# Instagram Stories — every alternate day, independent track
STORIES_CADENCE_DAYS: int = 2   # one story every 2 days

# ── Reddit subreddits for trend signal ───────────────────────────────
REDDIT_SUBREDDITS: List[str] = [
    "artificial",
    "automation",
    "machinelearning",
    "smallbusiness",
]

# ── Google Trends geo codes ──────────────────────────────────────────
PYTRENDS_GEO: List[str] = ["AE", "SA", "EG"]   # UAE, KSA, Egypt

# ── Brand / display ─────────────────────────────────────────────────
BRAND_NAME: str = "Revent AI Lab"
BRAND_COLOR: str = "#6C3CE1"          # primary purple
BRAND_COLOR_SECONDARY: str = "#00D4AA" # accent teal
