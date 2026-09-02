"""
Plotly chart factory functions for the Revent dashboard.

Consistent brand colors and styles across all visualizations.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import BRAND_COLOR, BRAND_COLOR_SECONDARY

# ── Color palette ────────────────────────────────────────────────────
REVENT_COLORS = [
    BRAND_COLOR,           # #6C3CE1 — primary purple
    BRAND_COLOR_SECONDARY, # #00D4AA — accent teal
    "#FF6B6B",             # coral
    "#4ECDC4",             # turquoise
    "#FFE66D",             # yellow
    "#95E1D3",             # mint
    "#F38181",             # salmon
    "#AA96DA",             # lavender
    "#A8D8EA",             # sky blue
    "#FCBAD3",             # pink
]

CHART_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12),
    margin=dict(l=40, r=20, t=50, b=40),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
)


def follower_trend_chart(
    df: pd.DataFrame,
    platform: str,
    title: Optional[str] = None,
) -> go.Figure:
    """
    Line chart of follower count over time for a single platform.
    Expects df with columns: date, followers
    """
    if df.empty:
        return _empty_chart(f"No data for {platform}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["followers"],
        mode="lines+markers",
        name="Followers",
        line=dict(color=BRAND_COLOR, width=3),
        marker=dict(size=6),
        hovertemplate="%{y:,.0f} followers<extra></extra>",
    ))

    # Add delta annotation
    if len(df) >= 2:
        first_val = df["followers"].iloc[0]
        last_val = df["followers"].iloc[-1]
        if first_val and last_val and first_val > 0:
            delta = last_val - first_val
            pct = (delta / first_val) * 100
            sign = "+" if delta >= 0 else ""
            color = "#00C853" if delta >= 0 else "#FF1744"
            fig.add_annotation(
                x=df["date"].iloc[-1],
                y=last_val,
                text=f"{sign}{delta:,.0f} ({sign}{pct:.1f}%)",
                showarrow=True,
                arrowhead=2,
                font=dict(color=color, size=14, family="Inter, sans-serif"),
                bgcolor="white",
                bordercolor=color,
                borderwidth=1,
            )

    fig.update_layout(
        title=title or f"{platform} — Follower Growth",
        yaxis_title="Followers",
        xaxis_title="",
        **CHART_LAYOUT,
    )
    return fig


def engagement_trend_chart(
    df: pd.DataFrame,
    platform: str,
    title: Optional[str] = None,
) -> go.Figure:
    """
    Line chart of engagement rate over time.
    Expects df with columns: date, engagement_rate
    """
    if df.empty or "engagement_rate" not in df.columns:
        return _empty_chart(f"No engagement data for {platform}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["engagement_rate"],
        mode="lines+markers",
        name="Engagement Rate %",
        line=dict(color=BRAND_COLOR_SECONDARY, width=3),
        marker=dict(size=6),
        hovertemplate="%{y:.3f}%<extra></extra>",
    ))

    fig.update_layout(
        title=title or f"{platform} — Engagement Rate",
        yaxis_title="Engagement Rate (%)",
        xaxis_title="",
        **CHART_LAYOUT,
    )
    return fig


def likes_trend_chart(
    df: pd.DataFrame,
    platform: str,
    title: Optional[str] = None,
) -> go.Figure:
    """
    Line chart of average likes over time.
    Expects df with columns: date, likes_avg
    """
    if df.empty or "likes_avg" not in df.columns:
        return _empty_chart(f"No likes data for {platform}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["likes_avg"],
        mode="lines+markers",
        name="Avg Likes",
        line=dict(color="#FF6B6B", width=3),
        marker=dict(size=6),
        hovertemplate="%{y:,.1f} avg likes<extra></extra>",
    ))

    fig.update_layout(
        title=title or f"{platform} — Like Rate Trend",
        yaxis_title="Avg Likes per Post",
        xaxis_title="",
        **CHART_LAYOUT,
    )
    return fig


def competitor_comparison_chart(
    df: pd.DataFrame,
    platform: str,
    metric: str = "followers",
    title: Optional[str] = None,
) -> go.Figure:
    """
    Multi-line chart comparing Revent against competitors.
    Expects df with columns: date, {metric}, competitor_name (None for Revent)
    """
    if df.empty:
        return _empty_chart(f"No comparison data for {platform}")

    fig = go.Figure()

    # Group by competitor_name
    groups = df.groupby("competitor_name") if "competitor_name" in df.columns else [(None, df)]

    color_idx = 0
    for name, group_df in groups:
        display_name = name if name else "Revent AI Lab"
        is_revent = name is None or name == "" or pd.isna(name) if isinstance(name, float) else name is None

        fig.add_trace(go.Scatter(
            x=group_df["date"],
            y=group_df[metric],
            mode="lines+markers",
            name=display_name,
            line=dict(
                color=REVENT_COLORS[color_idx % len(REVENT_COLORS)],
                width=4 if is_revent else 2,
            ),
            marker=dict(size=8 if is_revent else 4),
            hovertemplate=f"{display_name}: %{{y:,.0f}}<extra></extra>",
        ))
        color_idx += 1

    metric_labels = {
        "followers": "Followers",
        "engagement_rate": "Engagement Rate (%)",
        "likes_avg": "Avg Likes",
    }

    fig.update_layout(
        title=title or f"{platform} — {metric_labels.get(metric, metric)} Comparison",
        yaxis_title=metric_labels.get(metric, metric),
        xaxis_title="",
        **CHART_LAYOUT,
    )
    return fig


def trend_bar_chart(
    df: pd.DataFrame,
    title: str = "Trending Keywords",
) -> go.Figure:
    """
    Horizontal bar chart of trending keywords by score.
    Expects df with columns: keyword, score
    """
    if df.empty:
        return _empty_chart("No trend data available")

    # Aggregate by keyword
    agg = df.groupby("keyword")["score"].mean().sort_values(ascending=True).tail(15)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg.values,
        y=agg.index,
        orientation="h",
        marker_color=BRAND_COLOR,
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Trend Score",
        yaxis_title="",
        height=max(400, len(agg) * 30),
        **CHART_LAYOUT,
    )
    return fig


def _empty_chart(message: str) -> go.Figure:
    """Return a chart with a 'no data' message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        **CHART_LAYOUT,
    )
    return fig
