"""
Tab 1 — Our Social Analytics
Visualizes Revent AI Lab's own social performance across Facebook, Instagram,
YouTube, LinkedIn, and X.
Includes 7/30/60/90-day toggle, follower growth, engagement rate, like trends,
and manual data correction.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.db import read_snapshots
from app.charts import follower_trend_chart, engagement_trend_chart, likes_trend_chart
from app.manual_edit import render_snapshot_editor
import config


def render_tab_our_analytics(days_filter: int):
    st.markdown("## 📊 Revent AI Lab — Social Analytics")
    st.caption(
        "Performance snapshots scraped automatically across official channels. "
        "Historical data is stored in Supabase with Day-0 relative time filtering."
    )

    # 1. Fetch data for our own socials
    try:
        raw_snapshots = read_snapshots(days=days_filter, is_competitor=False)
    except Exception as e:
        st.error(f"Failed to load social snapshots from database: {e}")
        raw_snapshots = []

    df = pd.DataFrame(raw_snapshots)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values(by="date")

    # 2. KPI Summary Cards across platforms
    st.markdown("### 🌐 At a Glance")
    kpi_cols = st.columns(len(config.OUR_SOCIALS))

    for idx, (platform_name, profile_url) in enumerate(config.OUR_SOCIALS.items()):
        with kpi_cols[idx]:
            plat_df = df[df["platform"] == platform_name] if not df.empty and "platform" in df.columns else pd.DataFrame()
            if not plat_df.empty:
                latest = plat_df.iloc[-1]
                followers_now = latest.get("followers")
                followers_str = f"{followers_now:,.0f}" if pd.notna(followers_now) else "N/A"

                # Delta vs first record in the selected window
                delta_str = None
                if len(plat_df) >= 2 and pd.notna(followers_now):
                    oldest_f = plat_df.iloc[0].get("followers")
                    if pd.notna(oldest_f) and oldest_f > 0:
                        diff = int(followers_now - oldest_f)
                        diff_pct = (diff / oldest_f) * 100
                        delta_str = f"{diff:+d} ({diff_pct:+.1f}%)"

                st.metric(
                    label=platform_name,
                    value=followers_str,
                    delta=delta_str,
                    help=f"Latest snapshot for {platform_name} ({profile_url})"
                )
            else:
                st.metric(label=platform_name, value="No Data", delta=None)

    st.markdown("---")

    # 3. Platform Breakdown & Deep Dive
    platform_options = list(config.OUR_SOCIALS.keys())
    selected_platform = st.selectbox(
        "Select Platform to Inspect:",
        options=platform_options,
        index=0,
        help="Select any platform to view detailed follower growth, engagement rate, and post history."
    )

    plat_df = df[df["platform"] == selected_platform] if not df.empty and "platform" in df.columns else pd.DataFrame()

    if plat_df.empty:
        st.warning(
            f"No historical snapshots found for **{selected_platform}** in the last {days_filter} days. "
            f"Check the scraper logs or trigger a scrape in GitHub Actions."
        )
        # Give option to manually add an initial row
        st.markdown(f"#### ➕ Add Manual Snapshot for {selected_platform}")
        render_manual_entry_form(selected_platform, config.OUR_SOCIALS[selected_platform])
        return

    # Deep dive columns
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            follower_trend_chart(
                plat_df,
                platform=selected_platform,
                title=f"{selected_platform} — Follower / Subscriber Growth (Last {days_filter} Days)"
            ),
            use_container_width=True
        )
    with c2:
        st.plotly_chart(
            engagement_trend_chart(
                plat_df,
                platform=selected_platform,
                title=f"{selected_platform} — Engagement Rate Trend (%)"
            ),
            use_container_width=True
        )

    # Secondary chart: Like rate trend
    st.plotly_chart(
        likes_trend_chart(
            plat_df,
            platform=selected_platform,
            title=f"{selected_platform} — Average Likes per Post"
        ),
        use_container_width=True
    )

    # 4. Data Table & Manual Override Section
    st.markdown("### 📝 Snapshot History & Manual Override")
    st.caption(
        "Social media scrapers may occasionally fail or report partial data. "
        "Use the editor below to correct or backfill numbers without breaking historical trendlines."
    )

    display_cols = [c for c in ["date", "followers", "engagement_rate", "likes_avg", "comments_avg", "shares_avg", "posts_scraped"] if c in plat_df.columns]
    st.dataframe(plat_df[display_cols].tail(14), use_container_width=True, hide_index=True)

    with st.expander(f"✏️ Edit Recent {selected_platform} Snapshots"):
        records = plat_df.tail(7).to_dict("records")
        for rec in reversed(records):
            render_snapshot_editor(rec, key_prefix=f"our_{selected_platform}")


def render_manual_entry_form(platform: str, handle: str):
    """Render a form allowing team members to insert an initial or missing snapshot."""
    from app.db import upsert_snapshot

    with st.form(key=f"manual_entry_{platform}"):
        st.write(f"Add Snapshot for **{platform}** ({handle})")
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Date", value=date.today())
            followers = st.number_input("Followers / Subscribers", min_value=0, value=100, step=1)
            likes_avg = st.number_input("Average Likes", min_value=0.0, value=10.0, step=0.5)
        with col2:
            comments_avg = st.number_input("Average Comments", min_value=0.0, value=2.0, step=0.5)
            shares_avg = st.number_input("Average Shares / Retweets", min_value=0.0, value=0.0, step=0.5)
            er = st.number_input("Engagement Rate % (optional)", min_value=0.0, value=2.5, step=0.01)

        submitted = st.form_submit_button("Save Snapshot to Database")
        if submitted:
            payload = {
                "platform": platform,
                "handle": handle,
                "date": entry_date.isoformat(),
                "followers": int(followers),
                "likes_avg": float(likes_avg),
                "comments_avg": float(comments_avg),
                "shares_avg": float(shares_avg),
                "engagement_rate": float(er) if er > 0 else (float(likes_avg + comments_avg + shares_avg) / max(followers, 1)) * 100,
                "posts_scraped": 5,
                "is_competitor": False,
                "competitor_name": None,
            }
            if upsert_snapshot(payload):
                st.success("Snapshot saved! Please refresh to view.")
                st.rerun()
            else:
                st.error("Failed to save snapshot.")
