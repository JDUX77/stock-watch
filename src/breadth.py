"""
Market breadth module: measures how broad-based a market move is, plus
per-index Trend Scores for the Market Overview landing page.
"""
import pandas as pd

from src import cache_db, scoring

# Indices shown at the top of the Market Overview page.
MAJOR_INDICES = ["NIFTY50", "NIFTY BANK", "NIFTY IT", "NIFTY AUTO"]


def index_trend_score(index_symbol: str, benchmark_symbol: str = "NIFTY50") -> dict:
    """A 0-100 Trend Score for one index, using the same composite engine
    as stocks - lets you compare 'is Bank Nifty strong' on the same scale
    as 'is HDFC Bank strong'."""
    df = cache_db.load_ohlcv(index_symbol)
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    if df.empty or benchmark_df.empty:
        return {}

    result = scoring.composite_score(df, benchmark_df, scoring.LOOKBACKS["3M"])
    color, label = scoring.score_to_status(result["score"])

    changes = {}
    for period_label, days in {"1D": 1, "1W": 5, "1M": 21}.items():
        if len(df) > days:
            changes[period_label] = round(
                (df["close"].iloc[-1] - df["close"].iloc[-days - 1]) / df["close"].iloc[-days - 1] * 100, 2
            )
    return {
        "symbol": index_symbol, "score": result["score"], "status": label,
        "color": color, "changes": changes,
        "price": df["close"].iloc[-1] if not df.empty else None,
    }


def all_major_indices_overview(benchmark_symbol: str = "NIFTY50") -> pd.DataFrame:
    rows = []
    for idx in MAJOR_INDICES:
        data = index_trend_score(idx, benchmark_symbol)
        if not data:
            continue
        rows.append({
            "Index": idx, "Price": data["price"],
            "1D %": data["changes"].get("1D"), "1W %": data["changes"].get("1W"),
            "1M %": data["changes"].get("1M"), "Trend Score": data["score"],
            "Status": data["status"],
        })
    return pd.DataFrame(rows)


def advance_decline_snapshot(symbols: list) -> dict:
    """Counts how many stocks rose vs fell on the latest available day."""
    advances = declines = unchanged = 0
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if len(df) < 2:
            continue
        change = df["close"].iloc[-1] - df["close"].iloc[-2]
        if change > 0:
            advances += 1
        elif change < 0:
            declines += 1
        else:
            unchanged += 1
    total = advances + declines + unchanged
    return {
        "advances": advances, "declines": declines, "unchanged": unchanged,
        "ad_ratio": round(advances / declines, 2) if declines else None,
        "pct_advancing": round(advances / total * 100, 1) if total else None,
    }


def pct_above_moving_average(symbols: list, ma_period: int = 200) -> float:
    """% of stocks currently trading above their N-day moving average."""
    above = total = 0
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if len(df) < ma_period:
            continue
        ma = df["close"].rolling(ma_period).mean().iloc[-1]
        if df["close"].iloc[-1] > ma:
            above += 1
        total += 1
    return round(above / total * 100, 1) if total else None


def new_highs_lows(symbols: list, lookback: int = 252) -> dict:
    """Counts stocks making a new 52-week high or low as of the latest day."""
    highs = lows = 0
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if len(df) < lookback:
            continue
        window = df["close"].iloc[-lookback:]
        latest = window.iloc[-1]
        if latest >= window.max():
            highs += 1
        elif latest <= window.min():
            lows += 1
    return {"new_highs": highs, "new_lows": lows}


def breadth_summary_row(symbols: list, label: str) -> dict:
    """One row of the multi-index breadth table: A/D ratio, % above DMAs,
    new highs/lows, and an overall color band for a given stock universe."""
    ad = advance_decline_snapshot(symbols)
    pct20 = pct_above_moving_average(symbols, 20)
    pct50 = pct_above_moving_average(symbols, 50)
    pct200 = pct_above_moving_average(symbols, 200)
    hl = new_highs_lows(symbols)

    breadth_score = pct200 if pct200 is not None else 50
    color, status = scoring.score_to_status(breadth_score)

    return {
        "Universe": label, "A/D": ad["ad_ratio"],
        ">20 DMA": f"{pct20}%" if pct20 is not None else "n/a",
        ">50 DMA": f"{pct50}%" if pct50 is not None else "n/a",
        ">200 DMA": f"{pct200}%" if pct200 is not None else "n/a",
        "New High": hl["new_highs"], "New Low": hl["new_lows"],
        "Status": status, "_color": color,
    }


def cumulative_ad_line(symbols: list, days: int = 90) -> pd.DataFrame:
    """Day-by-day cumulative advance/decline line over time."""
    daily_changes = []
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol).tail(days + 1)
        if len(df) < 2:
            continue
        df = df.set_index("date")
        change = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        daily_changes.append(change)

    if not daily_changes:
        return pd.DataFrame()

    combined = pd.concat(daily_changes, axis=1).sum(axis=1)
    ad_line = combined.cumsum().reset_index()
    ad_line.columns = ["date", "cumulative_ad"]
    return ad_line
