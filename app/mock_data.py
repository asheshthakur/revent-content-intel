"""
Mock & Seed Dataset Generator for Revent AI Lab Content Intelligence Dashboard.
Generates realistic 90-day historical social snapshots, trends, competitor records,
and content calendars so the dashboard can be previewed immediately.
"""

from datetime import date, timedelta, datetime
import random
from typing import Dict, List
import config


def generate_seed_snapshots(days: int = 90) -> List[Dict]:
    """Generates 90 days of daily snapshots for Revent and tracked competitors."""
    snapshots = []
    base_date = date.today()

    # Revent baseline metrics (exact numbers from user)
    revent_base = {
        "LinkedIn":  {"followers": 2415, "growth": 4, "likes": 38, "comments": 6, "shares": 3},
        "Instagram": {"followers": 759,  "growth": 3, "likes": 28, "comments": 5, "shares": 2},
        "Facebook":  {"followers": 319,  "growth": 1, "likes": 12, "comments": 2, "shares": 1},
        "YouTube":   {"followers": 336,  "growth": 2, "likes": 24, "comments": 4, "shares": 0},
    }

    # Competitor baseline metrics
    competitor_base = {
        "Implement AI": {"followers": 4800, "growth": 9, "likes": 65, "comments": 12},
        "Anvenssa AI": {"followers": 2200, "growth": 6, "likes": 42, "comments": 7},
        "Maqsam": {"followers": 8900, "growth": 14, "likes": 140, "comments": 25},
        "Lucidya": {"followers": 12400, "growth": 18, "likes": 190, "comments": 32},
        "Dataiku": {"followers": 85000, "growth": 45, "likes": 420, "comments": 60},
        "Ahrefs": {"followers": 110000, "growth": 60, "likes": 580, "comments": 85},
        "Semrush": {"followers": 145000, "growth": 75, "likes": 710, "comments": 95},
    }

    row_id = 1
    for day_offset in range(days, -1, -1):
        cur_date = base_date - timedelta(days=day_offset)
        cur_date_str = cur_date.isoformat()

        # 1. Revent Socials
        for platform, profile_url in config.OUR_SOCIALS.items():
            base = revent_base.get(platform, {"followers": 1000, "growth": 3, "likes": 20, "comments": 3, "shares": 1})
            # Growth curve
            progress = (days - day_offset)
            f_count = int(base["followers"] - (day_offset * base["growth"]) + random.randint(-2, 3))
            likes = max(1.0, float(base["likes"] + random.randint(-5, 8)))
            comments = max(0.5, float(base["comments"] + random.randint(-2, 3)))
            shares = max(0.0, float(base["shares"] + random.randint(-1, 2)))
            er = round(((likes + comments + shares) / max(f_count, 1)) * 100, 4)

            snapshots.append({
                "id": row_id,
                "platform": platform,
                "handle": profile_url,
                "date": cur_date_str,
                "followers": max(50, f_count),
                "engagement_rate": er,
                "likes_avg": likes,
                "comments_avg": comments,
                "shares_avg": shares,
                "posts_scraped": random.randint(3, 8),
                "post_frequency": 3.5,
                "is_competitor": False,
                "competitor_name": None,
                "raw_data": {
                    "captions": [
                        f"Discover how our {random.choice(config.NICHE_KEYWORDS)} cuts SME operating costs by 40% in UAE. #AI #UAE #SME",
                        f"Why agentic AI is the future of enterprise automation in KSA and Egypt. #AgenticAI #Revent",
                        f"Top 3 workflows your business should automate this month using AI bots. #Automation #BusinessAI"
                    ],
                    "likes_list": [int(likes * 1.2), int(likes * 0.9), int(likes)],
                    "comments_list": [int(comments * 1.1), int(comments * 0.8), int(comments)]
                }
            })
            row_id += 1

        # 2. Competitors
        for comp_name, platforms in config.COMPETITORS.items():
            base = competitor_base.get(comp_name, {"followers": 5000, "growth": 10, "likes": 50, "comments": 8})
            for platform, handle_url in platforms.items():
                f_count = int(base["followers"] - (day_offset * base["growth"]) + random.randint(-10, 15))
                likes = max(1.0, float(base["likes"] + random.randint(-8, 12)))
                comments = max(0.5, float(base["comments"] + random.randint(-3, 5)))
                shares = max(0.0, float(random.randint(1, 10)))
                er = round(((likes + comments + shares) / max(f_count, 1)) * 100, 4)

                snapshots.append({
                    "id": row_id,
                    "platform": platform,
                    "handle": handle_url,
                    "date": cur_date_str,
                    "followers": max(100, f_count),
                    "engagement_rate": er,
                    "likes_avg": likes,
                    "comments_avg": comments,
                    "shares_avg": shares,
                    "posts_scraped": random.randint(3, 8),
                    "post_frequency": 4.0,
                    "is_competitor": True,
                    "competitor_name": comp_name,
                    "raw_data": {
                        "captions": [
                            f"How {comp_name} automates enterprise workflows with #AIagents and custom integrations. #AI #B2B",
                            f"SME AI automation trends report 2025: what every CEO in Dubai must know. #BusinessAI #TechUAE",
                            f"New release: enhanced agentic workflows for customer intelligence. #Lucidya #Semrush #Ahrefs"
                        ],
                        "likes_list": [int(likes * 1.3), int(likes * 0.8), int(likes)],
                        "comments_list": [int(comments * 1.2), int(comments * 0.7), int(comments)]
                    }
                })
                row_id += 1

    return snapshots


def generate_seed_trends(days: int = 60) -> List[Dict]:
    """Generates 60 days of realistic trend signals."""
    trends = []
    base_date = date.today()
    sources = ["google_trends", "google_news", "youtube", "reddit"]

    for day_offset in range(days, -1, -1):
        cur_date = (base_date - timedelta(days=day_offset)).isoformat()
        for kw in config.NICHE_KEYWORDS:
            for src in sources:
                score = round(random.uniform(45.0, 95.0), 1)
                trends.append({
                    "date": cur_date,
                    "keyword": kw,
                    "source": src,
                    "score": score,
                    "title": f"Recent insights: {kw} adoption across UAE & KSA markets",
                    "url": "https://news.google.com",
                    "metadata": {"relevance": score, "region": "GCC"}
                })
    return trends


def generate_seed_hashtags() -> List[Dict]:
    """Generates competitor hashtag tracking records."""
    hashtags_data = [
        ("aiagents", 45),
        ("agenticai", 38),
        ("dubai", 32),
        ("uae", 29),
        ("automation", 27),
        ("saas", 24),
        ("businessai", 22),
        ("sme", 19),
        ("ksa", 16),
        ("generativeai", 15),
        ("productivity", 14),
        ("workflowautomation", 12),
        ("techdubai", 10),
        ("egypt", 9),
    ]
    records = []
    today_str = date.today().isoformat()
    for tag, freq in hashtags_data:
        records.append({
            "date": today_str,
            "handle": "https://linkedin.com/company/implement-ai",
            "platform": "LinkedIn",
            "competitor_name": "Implement AI",
            "hashtag": tag,
            "frequency": freq
        })
    return records
