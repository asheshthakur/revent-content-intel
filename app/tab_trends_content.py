"""
Tab 2 — Trend & Content Idea Engine
Aggregates free trend sources (Google Trends, Google News, YouTube, Reddit)
into ranked keyword tables (7, 30, 60-day filters), renders a 7-day rolling
content calendar adhering to hard cadence rules and GCC B2B posting heuristics,
and provides a dedicated Instagram Stories feed and manual calendar editor.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from app.db import read_trends, read_all_calendar, upsert_calendar_entry
from app.charts import trend_bar_chart
from app.manual_edit import render_calendar_editor
from calendar_engine.posting_times import GCC_BEST_TIMES
import config


def render_tab_trends_content(days_filter: int):
    st.markdown("## 🔥 Trend & Content Idea Engine")
    st.caption(
        "Automated intelligence harvested from Google Trends (UAE/KSA/EG), Google News RSS, "
        "YouTube video search, and Reddit community discussions — zero paid APIs."
    )

    # 1. Trend Filter (7, 30, 60 days)
    t_col1, t_col2 = st.columns([1, 2])
    with t_col1:
        trend_window = st.selectbox(
            "Trend Lookback Window:",
            options=[7, 30, 60],
            index=0 if days_filter <= 7 else (1 if days_filter <= 30 else 2),
            format_func=lambda x: f"Last {x} Days",
            help="Filters trend signals captured within this timeframe."
        )

    # Fetch trend snapshots
    try:
        raw_trends = read_trends(days=trend_window)
    except Exception as e:
        st.error(f"Error reading trend snapshots: {e}")
        raw_trends = []

    # 2. Ranked Keywords & Topic Intelligence Table
    st.markdown("### 📈 Ranked Industry Signals & Topics")

    if raw_trends:
        trend_df = pd.DataFrame(raw_trends)
        if "date" in trend_df.columns:
            trend_df["date"] = pd.to_datetime(trend_df["date"]).dt.date

        c_chart, c_table = st.columns([1, 1])
        with c_chart:
            st.plotly_chart(
                trend_bar_chart(trend_df, title=f"Top Keywords by Avg Score (Last {trend_window}d)"),
                use_container_width=True
            )

        with c_table:
            st.markdown("#### Source Breakdown")
            # Aggregation by keyword and source count
            agg_df = (
                trend_df.groupby("keyword")
                .agg(
                    avg_score=("score", "mean"),
                    mentions=("score", "count"),
                    sources=("source", lambda x: ", ".join(sorted(set(x))))
                )
                .reset_index()
                .sort_values(by="avg_score", ascending=False)
            )
            agg_df["avg_score"] = agg_df["avg_score"].round(1)
            st.dataframe(
                agg_df.rename(columns={
                    "keyword": "Keyword / Topic",
                    "avg_score": "Avg Score (0-100)",
                    "mentions": "Data Points",
                    "sources": "Detected In"
                }),
                use_container_width=True,
                hide_index=True
            )

        with st.expander("🔍 View Raw Trending Signals (Articles, Videos & Discussions)"):
            disp_cols = [c for c in ["keyword", "source", "score", "title", "url", "date"] if c in trend_df.columns]
            st.dataframe(trend_df[disp_cols].head(30), use_container_width=True, hide_index=True)
    else:
        st.info(
            f"No trend snapshots recorded in the database for the last {trend_window} days. "
            f"The daily GitHub Actions job will populate this automatically, or you can trigger a run."
        )

    st.markdown("---")

    # 3. Rolling 7-Day Content Calendar
    st.markdown("### 🗓️ Rolling 7-Day Content Calendar")
    st.caption(
        "Strategically generated from trending industry topics using GCC B2B scheduling benchmarks. "
        "Strict platform quotas, deliberate gap days, and non-repeating topics are strictly enforced."
    )

    # GCC Heuristic Alert Box
    with st.expander("ℹ️ GCC B2B Best Time to Post Heuristics (Editable Baseline)"):
        st.markdown(
            """
            *These defaults represent established GCC B2B & SME engagement patterns (GST = UTC+4), "
            "designed to hit decision-makers during working hours.*
            """
        )
        heuristic_rows = []
        for p, d in GCC_BEST_TIMES.items():
            heuristic_rows.append({
                "Platform": p,
                "Recommended Days": ", ".join(d.get("best_days", [])),
                "Peak Window (GST)": d.get("display", ""),
                "Timezone": d.get("timezone", "Asia/Dubai")
            })
        st.table(pd.DataFrame(heuristic_rows))

    try:
        raw_calendar = read_all_calendar()
    except Exception as e:
        st.error(f"Error loading content calendar: {e}")
        raw_calendar = []

    cal_df = pd.DataFrame(raw_calendar)
    if not cal_df.empty and "date" in cal_df.columns:
        cal_df["date"] = pd.to_datetime(cal_df["date"]).dt.date
        cal_df = cal_df.sort_values(by=["date", "platform"])

    # Separate feed calendar vs Instagram Stories
    feed_df = cal_df[cal_df["format"] != "story"] if not cal_df.empty and "format" in cal_df.columns else pd.DataFrame()
    story_df = cal_df[cal_df["format"] == "story"] if not cal_df.empty and "format" in cal_df.columns else pd.DataFrame()

    # Feed Calendar Filters
    if not feed_df.empty:
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            platform_filter = st.multiselect(
                "Filter by Platform:",
                options=sorted(feed_df["platform"].unique()),
                default=sorted(feed_df["platform"].unique())
            )
        with filter_col2:
            format_filter = st.multiselect(
                "Filter by Format:",
                options=sorted(feed_df["format"].unique()),
                default=sorted(feed_df["format"].unique())
            )

        filtered_feed = feed_df[
            (feed_df["platform"].isin(platform_filter)) &
            (feed_df["format"].isin(format_filter))
        ]

        # Display Cards or Table
        st.markdown("#### Main Feed Schedule")
        for date_val, group in filtered_feed.groupby("date"):
            st.markdown(f"##### 📅 {date_val.strftime('%A, %b %d, %Y')}")
            for _, row in group.iterrows():
                badge_color = {
                    "LinkedIn": "blue",
                    "YouTube": "red",
                    "X": "gray",
                    "Instagram": "orange",
                    "Facebook": "indigo"
                }.get(row.get("platform"), "gray")

                with st.container(border=True):
                    c_meta, c_content = st.columns([1, 3])
                    with c_meta:
                        st.markdown(f"**:{badge_color}[{row.get('platform')}]**")
                        st.badge(row.get("format", "").upper())
                        st.caption(f"⏰ **Best Time:** {row.get('best_time')}")
                        if row.get("is_manual_override"):
                            st.caption("✏️ *Manually Edited*")
                    with c_content:
                        st.markdown(f"**Topic:** {row.get('topic')}")
                        st.markdown(f"🎯 **Hook:** *\"{row.get('hook')}\"*")
                        with st.expander("Read Structured Body & Call to Action"):
                            st.text(row.get("body"))
                            st.markdown(f"👉 **CTA:** `{row.get('cta')}`")

        # Edit Section
        st.markdown("#### ✏️ Quick Calendar Entry Editor")
        with st.expander("Click to modify any scheduled calendar item"):
            records = filtered_feed.to_dict("records")
            for rec in records:
                render_calendar_editor(rec, key_prefix="cal_tab2")
    else:
        st.info("No main feed calendar items found for the upcoming 7 days.")

    st.markdown("---")

    # 4. Dedicated Instagram Stories Section
    st.markdown("### 📸 Instagram Stories (Alternate Day Track)")
    st.caption(
        "High-engagement interactive stories (polls, questions, quizzes) scheduled every alternate day, "
        "independent of the main feed calendar."
    )

    if not story_df.empty:
        story_cols = st.columns(min(len(story_df), 4))
        for idx, (_, s_row) in enumerate(story_df.iterrows()):
            col_target = story_cols[idx % len(story_cols)]
            with col_target:
                with st.container(border=True):
                    st.markdown(f"**📅 {s_row.get('date')}**")
                    st.markdown(f"**{s_row.get('topic')}**")
                    st.caption(f"⏰ {s_row.get('best_time')}")
                    st.markdown(f"💡 *{s_row.get('hook')}*")
                    with st.expander("Story Sequence"):
                        st.text(s_row.get("body"))
                        st.markdown(f"**CTA:** {s_row.get('cta')}")
    else:
        st.info("No Instagram Stories currently scheduled.")
