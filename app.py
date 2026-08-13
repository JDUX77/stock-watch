"""
Main dashboard app. Run with:  streamlit run app.py

Navigation: Market Overview -> Sector Rotation -> Stock Detail forms a
drill-down journey (click a sector, see its stocks, click a stock, see why
its score is what it is). Momentum and Market Breadth are flat leaderboard
/ summary pages that feed the same underlying scores.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components

import config
from src import cache_db, scoring, sector_map
from src.refresh_job import run_refresh, DEFAULT_WATCHLIST
from src import momentum, breadth, sector_rotation, tradingview_widget

st.set_page_config(page_title="India Market Dashboard", layout="wide")
cache_db.init_db()

st.markdown("""
<style>
.score-badge {
    display: inline-block; padding: 4px 12px; border-radius: 12px;
    color: white; font-weight: 600; font-size: 0.85rem;
}
.driver-up { color: #2E7D32; }
.driver-down { color: #C62828; }
.driver-neutral { color: #757575; }
</style>
""", unsafe_allow_html=True)


def score_badge(score: float) -> str:
    color, label = scoring.score_to_status(score)
    return f'<span class="score-badge" style="background-color:{color}">{score:.0f} · {label}</span>'


def style_status_column(df: pd.DataFrame):
    """Colors the 'Status' column background based on the hidden _color field."""
    if "_color" not in df.columns:
        return df
    color_map = dict(zip(df["Status"], df["_color"]))
    display_df = df.drop(columns=["_color"])

    def highlight(row):
        c = color_map.get(row["Status"], "#999")
        return [f"background-color:{c};color:white" if col == "Status" else "" for col in row.index]

    return display_df.style.apply(highlight, axis=1)


watchlist_symbols = [s.replace("-EQ", "") for s in DEFAULT_WATCHLIST]

if "nav" not in st.session_state:
    st.session_state.nav = "Market Overview"
if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = None
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = watchlist_symbols[0]

# ---------- Sidebar ----------
st.sidebar.title("India Market Dashboard")

if not config.credentials_present():
    st.sidebar.error(
        "Angel One credentials not found.\n\nFill in your '.env' file (or Streamlit Cloud Secrets) and restart."
    )
else:
    st.sidebar.success("Angel One credentials loaded.")

last_refresh = cache_db.get_last_refresh()
st.sidebar.caption(f"Last data refresh: {last_refresh or 'never'}")

if st.sidebar.button("Refresh data now", width='stretch'):
    if not config.credentials_present():
        st.sidebar.error("Add your credentials first.")
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

st.sidebar.divider()
st.session_state.nav = st.sidebar.radio(
    "Navigate",
    ["Market Overview", "Momentum", "Sector Rotation", "Market Breadth", "Stock Detail", "Chart & Watchlist"],
    index=["Market Overview", "Momentum", "Sector Rotation", "Market Breadth", "Stock Detail", "Chart & Watchlist"].index(st.session_state.nav),
)

cached = cache_db.list_cached_symbols()
available = [s for s in watchlist_symbols if s in cached]

if not available:
    st.info("No data cached yet. Click 'Refresh data now' in the sidebar to get started.")
    st.stop()

# ================= MARKET OVERVIEW =================
if st.session_state.nav == "Market Overview":
    st.title("Market Overview")
    tv_watchlist = [f"NSE:{s}" for s in watchlist_symbols[:10]]
    components.html(tradingview_widget.ticker_tape_html(tv_watchlist), height=60)

    st.subheader("Major indices")
    idx_table = breadth.all_major_indices_overview()
    if not idx_table.empty:
        color_lookup = {"Very Strong": "#1B5E20", "Strong": "#2E7D32", "Improving": "#9E9D24",
                         "Neutral": "#F9A825", "Weak": "#EF6C00", "Very Weak": "#C62828"}
        idx_table_colored = idx_table.assign(_color=idx_table["Status"].map(color_lookup))
        st.dataframe(style_status_column(idx_table_colored), width='stretch', hide_index=True)
    else:
        st.info("Index data not cached yet.")

    col1, col2, col3 = st.columns(3)
    movers = momentum.top_movers(available, top_n=8)
    trending = momentum.trending_stocks(available, top_n=8)

    with col1:
        st.markdown("**Top gainers (1D)**")
        st.dataframe(movers["gainers"], width='stretch', hide_index=True)
    with col2:
        st.markdown("**Top losers (1D)**")
        st.dataframe(movers["losers"], width='stretch', hide_index=True)
    with col3:
        st.markdown("**Trending (strong + accelerating)**")
        st.dataframe(trending[["symbol", "Trending Score"]], width='stretch', hide_index=True)

    st.caption(
        "Trending = 70% current momentum level + 30% how much it's improved this week, "
        "not just today's biggest mover."
    )

# ================= MOMENTUM =================
elif st.session_state.nav == "Momentum":
    st.title("Momentum")
    st.caption("Composite Momentum Score (0-100) blends price momentum, relative strength vs Nifty 50, trend, volume, breakout proximity, and move efficiency.")

    table = momentum.build_momentum_table(available)
    if table.empty:
        st.info("Not enough data yet.")
    else:
        display = table.copy()
        for col in ["1M Score", "3M Score", "6M Score"]:
            if col in display.columns:
                display[col] = display[col].round(0)
        st.dataframe(
            display.style.background_gradient(subset=[c for c in display.columns if "Score" in c], cmap="RdYlGn", vmin=0, vmax=100),
            width='stretch', hide_index=True,
        )

    st.divider()
    st.subheader("Trending stocks")
    trending = momentum.trending_stocks(available, top_n=10)
    if not trending.empty:
        st.dataframe(trending, width='stretch', hide_index=True)

    pick = st.selectbox("View full detail for", available, key="momentum_pick")
    if st.button("Open stock detail"):
        st.session_state.selected_stock = pick
        st.session_state.nav = "Stock Detail"
        st.rerun()

# ================= SECTOR ROTATION =================
elif st.session_state.nav == "Sector Rotation":
    st.title("Sector rotation")
    st.caption("Which NSE sectors are gaining or losing strength, scored on the same 0-100 scale as individual stocks.")

    sector_table = sector_rotation.build_sector_table()
    if sector_table.empty:
        st.info("Sector data not cached yet.")
    else:
        st.dataframe(style_status_column(sector_table), width='stretch', hide_index=True)

        st.divider()
        st.subheader("Relative Rotation Graph")
        rrg = sector_rotation.build_rrg_table()
        if not rrg.empty:
            fig = px.scatter(
                rrg, x="rs_ratio", y="rs_momentum", text="sector", color="quadrant",
                color_discrete_map={"Leading": "#2E7D32", "Weakening": "#F9A825", "Lagging": "#C62828", "Improving": "#1565C0"},
            )
            fig.add_hline(y=100, line_dash="dash", line_color="gray")
            fig.add_vline(x=100, line_dash="dash", line_color="gray")
            fig.update_traces(textposition="top center", marker=dict(size=14))
            fig.update_layout(xaxis_title="Relative strength ratio", yaxis_title="Relative strength momentum", height=500)
            st.plotly_chart(fig, width='stretch')
        else:
            st.caption("Need more price history for the RRG view - showing the table above instead.")

        st.divider()
        st.subheader("Drill into a sector")
        sector_choice = st.selectbox("Sector", sector_table["sector"].tolist())
        stocks_table = sector_rotation.stocks_in_sector_table(sector_choice)
        if stocks_table.empty:
            st.info("No watchlist stocks mapped to this sector yet - edit src/sector_map.py to add some.")
        else:
            st.dataframe(stocks_table, width='stretch', hide_index=True)
            stock_pick = st.selectbox("View full detail for", stocks_table["symbol"].tolist())
            if st.button("Open stock detail", key="sector_drill_btn"):
                st.session_state.selected_stock = stock_pick
                st.session_state.nav = "Stock Detail"
                st.rerun()

# ================= MARKET BREADTH =================
elif st.session_state.nav == "Market Breadth":
    st.title("Market breadth")
    st.caption(
        "Currently scoped to your watchlist. Expand DEFAULT_WATCHLIST in src/refresh_job.py toward the full "
        "Nifty 500 for breadth numbers that reflect the whole market, not just 20 stocks."
    )

    row = breadth.breadth_summary_row(available, "My Watchlist")
    summary_df = pd.DataFrame([row])
    st.dataframe(style_status_column(summary_df), width='stretch', hide_index=True)

    col1, col2, col3 = st.columns(3)
    ad = breadth.advance_decline_snapshot(available)
    col1.metric("Advances vs declines", f"{ad['advances']} / {ad['declines']}")
    col2.metric("% above 200-day MA", f"{breadth.pct_above_moving_average(available, 200)}%")
    hl = breadth.new_highs_lows(available)
    col3.metric("New highs vs lows", f"{hl['new_highs']} / {hl['new_lows']}")

    ad_line = breadth.cumulative_ad_line(available)
    if not ad_line.empty:
        fig = go.Figure(go.Scatter(x=ad_line["date"], y=ad_line["cumulative_ad"], mode="lines"))
        fig.update_layout(title="Cumulative advance/decline line (90 days)", height=350)
        st.plotly_chart(fig, width='stretch')

# ================= STOCK DETAIL =================
elif st.session_state.nav == "Stock Detail":
    pick = st.selectbox("Stock", available, index=available.index(st.session_state.selected_stock) if st.session_state.selected_stock in available else 0)
    st.session_state.selected_stock = pick

    detail = momentum.stock_score_breakdown(pick)
    if not detail:
        st.info("Not enough history for this stock yet.")
    else:
        st.title(pick)
        price = detail["latest_price"]
        st.markdown(f"### ₹{price:,.2f}" if price else "")

        cols = st.columns(3)
        for i, (label, result) in enumerate(detail["scores_by_window"].items()):
            with cols[i]:
                st.markdown(f"**{label} Momentum Score**")
                st.markdown(score_badge(result["score"]), unsafe_allow_html=True)

        st.divider()
        st.subheader("Score history")
        if not detail["score_history"].empty:
            fig = go.Figure(go.Scatter(
                x=detail["score_history"]["date"], y=detail["score_history"]["score"],
                mode="lines+markers", line=dict(color="#1565C0", width=3),
            ))
            fig.update_layout(height=300, yaxis_range=[0, 100], yaxis_title="Momentum Score")
            st.plotly_chart(fig, width='stretch')

        st.subheader("3-month score breakdown")
        components_data = detail["scores_by_window"]["3M"]["components"]
        max_points = {"Price Momentum": 28, "Relative Strength": 24, "Trend": 15, "Volume": 15, "Breakout": 10, "Efficiency": 8}
        comp_df = pd.DataFrame([
            {"Component": k, "Score": v, "Max": max_points[k]} for k, v in components_data.items()
        ])
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(y=comp_df["Component"], x=comp_df["Score"], orientation="h", name="Score", marker_color="#2E7D32"))
        fig2.add_trace(go.Bar(y=comp_df["Component"], x=comp_df["Max"] - comp_df["Score"], orientation="h", name="Remaining", marker_color="#E0E0E0"))
        fig2.update_layout(barmode="stack", height=300, showlegend=False, xaxis_title="Points")
        st.plotly_chart(fig2, width='stretch')

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Returns")
            for label, value in detail["returns"].items():
                st.write(f"{label}: {'+' if value >= 0 else ''}{value}%")
        with col2:
            st.subheader("Momentum drivers")
            drivers = momentum.momentum_drivers(pick)
            if not drivers:
                st.caption("Not enough history yet.")
            for kind, text in drivers:
                icon = "🟢" if kind == "up" else ("🔴" if kind == "down" else "🟡")
                st.markdown(f"{icon} {text}")

        sector = sector_map.sector_for_stock(pick)
        st.caption(f"Sector: {sector}")

        st.divider()
        components.html(tradingview_widget.advanced_chart_html(f"NSE:{pick}"), height=500)

# ================= CHART & WATCHLIST =================
elif st.session_state.nav == "Chart & Watchlist":
    st.title("Chart & watchlist (TradingView)")
    selected = st.selectbox("Select a symbol to chart", watchlist_symbols, index=0)
    components.html(tradingview_widget.advanced_chart_html(f"NSE:{selected}"), height=540)
    st.markdown("**Watchlist**")
    components.html(tradingview_widget.watchlist_html([f"NSE:{s}" for s in watchlist_symbols]), height=500)
