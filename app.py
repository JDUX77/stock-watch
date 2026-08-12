"""
Main dashboard app. Run with:  streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

import config
from src import cache_db
from src.refresh_job import run_refresh, DEFAULT_WATCHLIST
from src import momentum, breadth, sector_rotation, tradingview_widget

st.set_page_config(page_title="India Market Dashboard", layout="wide")
cache_db.init_db()

# ---------- Sidebar ----------
st.sidebar.title("India Market Dashboard")

if not config.credentials_present():
    st.sidebar.error(
        "Angel One credentials not found.\n\n"
        "Copy '.env.example' to '.env' and fill in your details, then restart the app."
    )
else:
    st.sidebar.success("Angel One credentials loaded.")

last_refresh = cache_db.get_last_refresh()
st.sidebar.caption(f"Last data refresh: {last_refresh or 'never'}")

if st.sidebar.button("Refresh data now", use_container_width=True):
    if not config.credentials_present():
        st.sidebar.error("Add your credentials to .env first.")
    else:
        progress = st.sidebar.progress(0, text="Starting...")
        def update(i, total, label):
            progress.progress(i / total, text=f"Fetching {label} ({i}/{total})")
        try:
            run_refresh(progress_callback=update)
            st.sidebar.success("Data refreshed.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Refresh failed: {e}")

watchlist_symbols = [s.replace("-EQ", "") for s in DEFAULT_WATCHLIST]

# ---------- Ticker tape across the top ----------
tv_watchlist = [f"NSE:{s}" for s in watchlist_symbols[:10]]
components.html(tradingview_widget.ticker_tape_html(tv_watchlist), height=60)

# ---------- Tabs ----------
tab_momentum, tab_sector, tab_breadth, tab_chart = st.tabs(
    ["Momentum", "Sector rotation", "Market breadth", "Chart & watchlist"]
)

with tab_momentum:
    st.subheader("Stock momentum leaderboard")
    st.caption(
        "RoC = raw price change. RS = the stock's return minus the Nifty 50's return "
        "over the same window (positive means it's beating the index, not just rising with it)."
    )
    cached = cache_db.list_cached_symbols()
    available = [s for s in watchlist_symbols if s in cached]
    if not available:
        st.info("No data cached yet. Click 'Refresh data now' in the sidebar to get started.")
    else:
        table = momentum.build_momentum_table(available, benchmark_symbol="NIFTY50")
        st.dataframe(
            table.style.background_gradient(
                subset=[c for c in table.columns if c.startswith("RS")], cmap="RdYlGn"
            ),
            use_container_width=True, hide_index=True,
        )

with tab_sector:
    st.subheader("Sector rotation")
    st.caption(
        "Which NSE sectors are gaining or losing relative strength vs Nifty 50."
    )
    rrg = sector_rotation.build_rrg_table()
    if rrg.empty:
        simple = sector_rotation.simple_sector_leaderboard()
        if simple.empty:
            st.info("No sector data cached yet. Click 'Refresh data now' in the sidebar.")
        else:
            st.caption("Showing simple returns leaderboard (need more history for full rotation chart).")
            st.dataframe(simple, use_container_width=True, hide_index=True)
    else:
        fig = px.scatter(
            rrg, x="rs_ratio", y="rs_momentum", text="sector", color="quadrant",
            color_discrete_map={
                "Leading": "#2E7D32", "Weakening": "#F9A825",
                "Lagging": "#C62828", "Improving": "#1565C0",
            },
        )
        fig.add_hline(y=100, line_dash="dash", line_color="gray")
        fig.add_vline(x=100, line_dash="dash", line_color="gray")
        fig.update_traces(textposition="top center", marker=dict(size=14))
        fig.update_layout(
            xaxis_title="Relative strength ratio (>100 = outperforming Nifty)",
            yaxis_title="Relative strength momentum (>100 = ratio rising)",
            height=550,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(rrg, use_container_width=True, hide_index=True)

with tab_breadth:
    st.subheader("Market breadth")
    cached = cache_db.list_cached_symbols()
    available = [s for s in watchlist_symbols if s in cached]
    if not available:
        st.info("No data cached yet. Click 'Refresh data now' in the sidebar.")
    else:
        col1, col2, col3 = st.columns(3)
        ad = breadth.advance_decline_snapshot(available)
        pct_above_200 = breadth.pct_above_moving_average(available, 200)
        hl = breadth.new_highs_lows(available)

        col1.metric("Advances vs declines", f"{ad['advances']} / {ad['declines']}")
        col2.metric("% above 200-day MA", f"{pct_above_200}%" if pct_above_200 is not None else "n/a")
        col3.metric("New highs vs lows", f"{hl['new_highs']} / {hl['new_lows']}")

        st.caption(
            "Note: with a 20-stock starter watchlist these numbers are illustrative. "
            "Expand DEFAULT_WATCHLIST in src/refresh_job.py to your full universe "
            "(e.g. Nifty 500) for breadth numbers that actually reflect the whole market."
        )

        ad_line = breadth.cumulative_ad_line(available)
        if not ad_line.empty:
            fig = go.Figure(go.Scatter(x=ad_line["date"], y=ad_line["cumulative_ad"], mode="lines"))
            fig.update_layout(title="Cumulative advance/decline line", height=350)
            st.plotly_chart(fig, use_container_width=True)

with tab_chart:
    st.subheader("Chart & watchlist (TradingView)")
    selected = st.selectbox("Select a symbol to chart", watchlist_symbols, index=0)
    components.html(
        tradingview_widget.advanced_chart_html(f"NSE:{selected}"), height=540
    )
    st.markdown("**Watchlist**")
    components.html(
        tradingview_widget.watchlist_html([f"NSE:{s}" for s in watchlist_symbols]),
        height=500,
    )
