"""
Tab 3 — Competitor Analysis
Compares Revent AI Lab against tracked industry competitors:
1. Combined growth chart (multi-line Plotly, selectable platform, 7/30/60/90d filter)
2. Competitor hashtag frequency breakdown
3. Content Gap Analysis using the niche keyword taxonomy
4. Top-performing competitor content breakdown
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Optional
import json

from app.db import read_snapshots, read_hashtags
from app.charts import competitor_comparison_chart
import config


def render_tab_competitor(days_filter: int):
    st.markdown("## 🏆 Competitor Analysis & Benchmarking")
    st.caption(
        "Benchmarking Revent AI Lab against key regional and global AI/automation players "
        "(Implement AI, Anvenssa AI, Maqsam, Lucidya, Dataiku, Ahrefs, Semrush)."
    )

    # 1. Fetch all snapshots (both Revent and competitors)
    try:
        all_snapshots = read_snapshots(days=days_filter)
    except Exception as e:
        st.error(f"Error fetching snapshot data: {e}")
        all_snapshots = []

    df = pd.DataFrame(all_snapshots)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values(by="date")

    # Available platforms
    platforms_with_data = sorted(df["platform"].unique()) if not df.empty and "platform" in df.columns else list(config.OUR_SOCIALS.keys())
    selected_platform = st.selectbox(
        "Select Platform for Competitor Benchmark:",
        options=platforms_with_data,
        index=0,
        help="Select a platform to compare audience growth and engagement against competitors."
    )

    plat_df = df[df["platform"] == selected_platform] if not df.empty and "platform" in df.columns else pd.DataFrame()

    # ── Section 1: Combined Growth Chart ──────────────────────────
    st.markdown("### 📈 Audience Growth Comparison")
    if not plat_df.empty:
        # Toggle between Followers, Engagement Rate, and Likes
        metric_choice = st.radio(
            "Metric to Compare:",
            options=["followers", "engagement_rate", "likes_avg"],
            format_func=lambda m: {
                "followers": "Follower / Subscriber Count",
                "engagement_rate": "Engagement Rate (%)",
                "likes_avg": "Average Likes per Post"
            }[m],
            horizontal=True
        )

        st.plotly_chart(
            competitor_comparison_chart(
                plat_df,
                platform=selected_platform,
                metric=metric_choice,
                title=f"{selected_platform} — Revent AI Lab vs Competitors (Last {days_filter} Days)"
            ),
            use_container_width=True
        )
    else:
        st.info(f"No benchmark snapshot history available for {selected_platform} in this date range.")

    st.markdown("---")

    # ── Section 2: Hashtag Frequency Table ────────────────────────
    st.markdown("### 🏷️ Competitor Hashtag Intelligence")
    st.caption("Hashtags extracted from competitor posts, identifying their organic positioning.")

    try:
        raw_hashtags = read_hashtags(days=days_filter)
    except Exception as e:
        st.error(f"Error reading hashtag tracking: {e}")
        raw_hashtags = []

    if raw_hashtags:
        ht_df = pd.DataFrame(raw_hashtags)
        c_filter, c_tbl = st.columns([1, 2])
        with c_filter:
            competitors_in_ht = sorted(ht_df["competitor_name"].dropna().unique())
            selected_comp = st.selectbox(
                "Filter Hashtags by Competitor:",
                options=["All Competitors"] + competitors_in_ht,
                index=0
            )

        with c_tbl:
            filtered_ht = ht_df if selected_comp == "All Competitors" else ht_df[ht_df["competitor_name"] == selected_comp]
            agg_ht = (
                filtered_ht.groupby("hashtag")["frequency"]
                .sum()
                .reset_index()
                .sort_values(by="frequency", ascending=False)
                .head(25)
            )
            agg_ht["hashtag"] = agg_ht["hashtag"].apply(lambda h: f"#{h}")
            st.dataframe(
                agg_ht.rename(columns={"hashtag": "Hashtag", "frequency": "Frequency Count"}),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No hashtag records found yet. Scraped competitor post captions will populate this table automatically.")

    st.markdown("---")

    # ── Section 3: Content Gap Analysis ───────────────────────────
    st.markdown("### 🎯 Content Gap Analysis")
    st.caption(
        "Identifies topics and niche keywords covered by competitors that Revent has NOT recently published on. "
        "Evaluated against our core niche keyword taxonomy."
    )

    render_content_gap_analysis(df)

    st.markdown("---")

    # ── Section 4: Top-Performing Content ─────────────────────────
    st.markdown("### 🚀 Top-Performing Competitor Content")
    st.caption("Highest-engagement recent posts across all competitors with format type and metrics.")

    render_top_performing_content(df)


def render_content_gap_analysis(df: pd.DataFrame):
    """
    Compares competitor post topics against Revent's own recent topics
    using the NICHE_KEYWORDS taxonomy.
    """
    if df.empty or "raw_data" not in df.columns:
        st.info("Insufficient post caption data for content gap analysis.")
        return

    # Extract all text/captions for Revent vs Competitors
    revent_captions = []
    competitor_captions_by_name = {}

    for _, row in df.iterrows():
        is_comp = row.get("is_competitor", False)
        comp_name = row.get("competitor_name") or "Competitor"
        raw = row.get("raw_data") or {}

        # raw_data might be a dict or a JSON string
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}

        captions = raw.get("captions", [])

        if not is_comp:
            revent_captions.extend([str(c).lower() for c in captions])
        else:
            if comp_name not in competitor_captions_by_name:
                competitor_captions_by_name[comp_name] = []
            competitor_captions_by_name[comp_name].extend([str(c).lower() for c in captions])

    revent_combined = " ".join(revent_captions)

    # Check taxonomy presence
    gap_records = []
    for kw in config.NICHE_KEYWORDS:
        kw_clean = kw.lower()
        covered_by_revent = kw_clean in revent_combined

        competitors_covering = []
        for cname, c_caps in competitor_captions_by_name.items():
            combined_comp = " ".join(c_caps)
            if kw_clean in combined_comp:
                competitors_covering.append(cname)

        is_gap = (not covered_by_revent) and (len(competitors_covering) > 0)
        gap_records.append({
            "Topic / Keyword": kw,
            "Revent Covered?": "✅ Yes" if covered_by_revent else "❌ No",
            "Covered By Competitors": ", ".join(competitors_covering) if competitors_covering else "None",
            "Status": "⚠️ CONTENT GAP" if is_gap else ("✅ Covered" if covered_by_revent else "⚪ Untapped Opportunity")
        })

    gap_df = pd.DataFrame(gap_records)
    st.dataframe(gap_df, use_container_width=True, hide_index=True)


def render_top_performing_content(df: pd.DataFrame):
    """
    Extracts individual post metrics from competitor raw_data JSON
    and displays top posts sorted by likes/engagement.
    """
    if df.empty or "raw_data" not in df.columns:
        st.info("No scraped post details available.")
        return

    comp_df = df[df["is_competitor"] == True]
    if comp_df.empty:
        st.info("No competitor post records found.")
        return

    extracted_posts = []
    for _, row in comp_df.iterrows():
        comp_name = row.get("competitor_name", "Unknown")
        platform = row.get("platform", "Unknown")
        raw = row.get("raw_data") or {}

        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}

        # Case A: YouTube videos
        if "videos" in raw and isinstance(raw["videos"], list):
            for v in raw["videos"]:
                extracted_posts.append({
                    "Competitor": comp_name,
                    "Platform": platform,
                    "Format": "Long-Form Video",
                    "Title / Caption": v.get("title", "Untitled"),
                    "Views": v.get("views", 0),
                    "Likes": v.get("likes", 0),
                    "Comments": v.get("comments", 0),
                    "URL": v.get("url", "")
                })

        # Case B: Social post captions with likes list
        likes_list = raw.get("likes_list", [])
        captions = raw.get("captions", [])
        comments_list = raw.get("comments_list", [])

        for idx, cap in enumerate(captions):
            likes_val = likes_list[idx] if idx < len(likes_list) else 0
            comm_val = comments_list[idx] if idx < len(comments_list) else 0
            extracted_posts.append({
                "Competitor": comp_name,
                "Platform": platform,
                "Format": "Social Post / Carousel",
                "Title / Caption": cap[:140] + ("..." if len(cap) > 140 else ""),
                "Views": 0,
                "Likes": likes_val,
                "Comments": comm_val,
                "URL": row.get("handle", "")
            })

    if extracted_posts:
        posts_df = pd.DataFrame(extracted_posts).sort_values(by="Likes", ascending=False).head(20)
        st.dataframe(posts_df, use_container_width=True, hide_index=True)
    else:
        st.info("Competitor posts will appear here once the scraper records individual post engagement data.")
