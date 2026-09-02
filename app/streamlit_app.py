"""
Revent AI Lab — Content Intelligence Dashboard
Stateless Streamlit application for team-wide access on Streamlit Community Cloud.
Features:
- Shared password gate (checked against st.secrets["DASHBOARD_PASSWORD"])
- 3 Tabs: Our Social Analytics, Trend & Content Engine, Competitor Analysis
- 7/30/60/90-day Day-0 relative time filtering
- Real-time Supabase integration with graceful error handling
"""

import streamlit as st
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tab_our_analytics import render_tab_our_analytics
from app.tab_trends_content import render_tab_trends_content
from app.tab_competitor import render_tab_competitor
from app.db import read_scrape_log, is_supabase_configured
from app.local_storage import get_last_successful_scrape
from app.alerting import alert_stale_data
import config

# ── Streamlit Page Configuration ──────────────────────────────────────
st.set_page_config(
    page_title="Revent AI Lab — Content Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS for Revent Brand ───────────────────────────────────────
st.markdown(
    f"""
    <style>
    .main-header {{
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        background: linear-gradient(90deg, {config.BRAND_COLOR} 0%, {config.BRAND_COLOR_SECONDARY} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }}
    .sub-header {{
        color: #6c757d;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }}
    .stMetric {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        padding: 12px 16px;
    }}
    .stMetric label {{
        color: rgba(255, 255, 255, 0.85) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }}
    .stMetric [data-testid="stMetricValue"] {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}
    @media (prefers-color-scheme: light) {{
        .stMetric {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
        }}
        .stMetric label {{
            color: #495057 !important;
        }}
        .stMetric [data-testid="stMetricValue"] {{
            color: #212529 !important;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def check_password() -> bool:
    """
    Returns True if the user entered the correct shared password.
    Checks st.secrets["DASHBOARD_PASSWORD"], falling back to env var or default.
    """
    if st.session_state.get("authenticated", False):
        return True

    # Retrieve expected password
    expected_password = None
    try:
        expected_password = st.secrets.get("DASHBOARD_PASSWORD")
    except Exception:
        pass
    if not expected_password:
        expected_password = os.environ.get("DASHBOARD_PASSWORD", "REVENT_DASH_2024")

    # Password screen layout
    st.markdown("<div class='main-header'>⚡ Revent AI Lab</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Internal Content Intelligence Platform — GCC B2B</div>", unsafe_allow_html=True)

    with st.container():
        st.info("🔒 This dashboard contains confidential competitor intelligence. Please enter team password to proceed.")
        password_input = st.text_input(
            "Shared Team Password",
            type="password",
            placeholder="Enter password...",
            key="dash_pwd_input"
        )
        login_btn = st.button("Access Dashboard", type="primary")

        if login_btn or password_input:
            if password_input == expected_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please check with the Revent admin.")
                return False

    return False


def main():
    # 1. Enforce Password Gate
    if not check_password():
        return

    # 2. Main Title Banner
    col_logo, col_actions = st.columns([3, 1])
    with col_logo:
        st.markdown("<div class='main-header'>⚡ Revent AI Lab</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='sub-header'>UAE • KSA • Egypt — Content Intelligence & Competitor Radar</div>",
            unsafe_allow_html=True
        )

    # ── Stale Data Check & UI Warning Banner (> 48h) ─────────────────
    from datetime import datetime, timezone
    last_scrape_dt = get_last_successful_scrape()
    now_utc = datetime.now(timezone.utc)

    if last_scrape_dt:
        if last_scrape_dt.tzinfo is None:
            last_scrape_dt = last_scrape_dt.replace(tzinfo=timezone.utc)
        hours_old = (now_utc - last_scrape_dt).total_seconds() / 3600.0
        if hours_old > config.STALE_DATA_THRESHOLD_HOURS:
            st.warning(
                f"⚠️ **STALE DATA WARNING**: Latest snapshot metrics were collected {hours_old:.1f} hours ago "
                f"(last successful scrape: {last_scrape_dt.strftime('%Y-%m-%d %H:%M UTC')}). "
                f"Scheduled daily scrape may be delayed or experiencing errors.",
                icon="⚠️"
            )
            # Send alert email once per session if stale
            if not st.session_state.get("stale_alert_sent", False):
                alert_stale_data(last_scrape_dt, hours_old)
                st.session_state["stale_alert_sent"] = True
    else:
        # Check Supabase scrape_log as secondary source
        try:
            logs = read_scrape_log(days=3)
            if not logs:
                st.info("ℹ️ Initializing metrics pipeline. Trigger a scrape run or wait for the scheduled daily cron at 08:00 GST.")
        except Exception:
            pass

    # 3. Sidebar Controls
    with st.sidebar:
        st.markdown("### ⚙️ Dashboard Controls")

        # 7 / 30 / 60 / 90-day filter
        days_filter = st.selectbox(
            "Lookback Window (Day 0 Relative):",
            options=[7, 30, 60, 90],
            index=1,  # default 30 days
            format_func=lambda x: f"Last {x} Days",
            help="Filters snapshot history counting back N days from Day 0 (today)."
        )

        st.markdown("---")
        st.markdown("### 📡 Scraper Health")

        try:
            recent_logs = read_scrape_log(days=3)
            if recent_logs:
                success_count = sum(1 for log in recent_logs if log.get("status") == "success")
                st.write(f"**Last Scrapes:** {success_count}/{len(recent_logs)} succeeded")
                with st.expander("View Scraper Logs"):
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(recent_logs)[["platform", "status", "date"]].head(10),
                        hide_index=True
                    )
            else:
                st.caption("No scrape runs logged yet.")
        except Exception:
            st.caption("DB logs not available.")

        st.markdown("---")
        if is_supabase_configured():
            st.success("🟢 Connected to Supabase")
        else:
            st.warning("🟡 Demonstration Mode")
            with st.expander("ℹ️ Connect Live Supabase"):
                st.caption(
                    "To switch to live cloud database, add your Supabase credentials to "
                    "`.streamlit/secrets.toml` or Streamlit Cloud App Settings."
                )

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

        st.caption("Revent AI Lab • v1.0.0")

    # 4. Render Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Our Social Analytics",
        "🔥 Trend & Content Engine",
        "🏆 Competitor Analysis"
    ])

    with tab1:
        render_tab_our_analytics(days_filter)

    with tab2:
        render_tab_trends_content(days_filter)

    with tab3:
        render_tab_competitor(days_filter)


if __name__ == "__main__":
    main()
