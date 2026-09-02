"""
Manual override / edit UI components.

Provides st.form-based editors for social_snapshots and content_calendar
rows, allowing the team to correct bad scrapes or edit calendar entries.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional

from app.db import update_snapshot, update_calendar_entry


def render_snapshot_editor(row: Dict, key_prefix: str = "snap"):
    """
    Render an inline editor for a social_snapshots row.
    Returns True if the row was updated.
    """
    row_id = row.get("id")
    if not row_id:
        return False

    with st.expander(
        f"✏️ Edit {row.get('platform', '')} — {row.get('date', '')}",
        expanded=False,
    ):
        with st.form(key=f"{key_prefix}_edit_{row_id}"):
            col1, col2 = st.columns(2)
            with col1:
                followers = st.number_input(
                    "Followers",
                    value=row.get("followers") or 0,
                    min_value=0,
                    step=1,
                    key=f"{key_prefix}_followers_{row_id}",
                )
                likes_avg = st.number_input(
                    "Avg Likes",
                    value=float(row.get("likes_avg") or 0),
                    min_value=0.0,
                    step=0.1,
                    key=f"{key_prefix}_likes_{row_id}",
                )
            with col2:
                comments_avg = st.number_input(
                    "Avg Comments",
                    value=float(row.get("comments_avg") or 0),
                    min_value=0.0,
                    step=0.1,
                    key=f"{key_prefix}_comments_{row_id}",
                )
                shares_avg = st.number_input(
                    "Avg Shares",
                    value=float(row.get("shares_avg") or 0),
                    min_value=0.0,
                    step=0.1,
                    key=f"{key_prefix}_shares_{row_id}",
                )
            engagement_rate = st.number_input(
                "Engagement Rate (%)",
                value=float(row.get("engagement_rate") or 0),
                min_value=0.0,
                step=0.001,
                format="%.4f",
                key=f"{key_prefix}_er_{row_id}",
            )

            submitted = st.form_submit_button("💾 Save Changes")
            if submitted:
                updates = {
                    "followers": int(followers),
                    "likes_avg": likes_avg,
                    "comments_avg": comments_avg,
                    "shares_avg": shares_avg,
                    "engagement_rate": engagement_rate,
                }
                success = update_snapshot(row_id, updates)
                if success:
                    st.success("✅ Updated successfully!")
                    return True
                else:
                    st.error("❌ Failed to update. Check the logs.")
    return False


def render_calendar_editor(row: Dict, key_prefix: str = "cal"):
    """
    Render an inline editor for a content_calendar row.
    Returns True if the row was updated.
    """
    row_id = row.get("id")
    if not row_id:
        return False

    with st.expander(
        f"✏️ Edit: {row.get('platform', '')} — {row.get('topic', '')[:40]}",
        expanded=False,
    ):
        with st.form(key=f"{key_prefix}_edit_{row_id}"):
            topic = st.text_input(
                "Topic",
                value=row.get("topic", ""),
                key=f"{key_prefix}_topic_{row_id}",
            )
            hook = st.text_area(
                "Hook",
                value=row.get("hook", ""),
                height=80,
                key=f"{key_prefix}_hook_{row_id}",
            )
            body = st.text_area(
                "Body / Key Points",
                value=row.get("body", ""),
                height=150,
                key=f"{key_prefix}_body_{row_id}",
            )
            cta = st.text_input(
                "Call to Action",
                value=row.get("cta", ""),
                key=f"{key_prefix}_cta_{row_id}",
            )

            col1, col2 = st.columns(2)
            with col1:
                format_type = st.selectbox(
                    "Format",
                    ["static", "carousel", "short-form", "long-form", "story"],
                    index=["static", "carousel", "short-form", "long-form", "story"].index(
                        row.get("format", "static")
                    ) if row.get("format") in ["static", "carousel", "short-form", "long-form", "story"] else 0,
                    key=f"{key_prefix}_format_{row_id}",
                )
            with col2:
                best_time = st.text_input(
                    "Best Time",
                    value=row.get("best_time", ""),
                    key=f"{key_prefix}_time_{row_id}",
                )

            submitted = st.form_submit_button("💾 Save Changes")
            if submitted:
                updates = {
                    "topic": topic,
                    "hook": hook,
                    "body": body,
                    "cta": cta,
                    "format": format_type,
                    "best_time": best_time,
                }
                success = update_calendar_entry(row_id, updates)
                if success:
                    st.success("✅ Updated! Marked as manual override.")
                    return True
                else:
                    st.error("❌ Failed to update.")
    return False


def render_data_table_with_edit(
    df: pd.DataFrame,
    table_type: str = "snapshot",
    key_prefix: str = "tbl",
):
    """
    Render a dataframe as a table with per-row edit buttons.
    table_type: 'snapshot' or 'calendar'
    """
    if df.empty:
        st.info("No data to display.")
        return

    # Show the table
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Edit section
    st.markdown("---")
    st.markdown("**Edit individual entries:**")

    rows = df.to_dict("records")
    for i, row in enumerate(rows):
        if table_type == "snapshot":
            render_snapshot_editor(row, key_prefix=f"{key_prefix}_{i}")
        elif table_type == "calendar":
            render_calendar_editor(row, key_prefix=f"{key_prefix}_{i}")
