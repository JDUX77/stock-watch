"""
Momentum module: ranks stocks by composite Momentum Score (see scoring.py)
across 1M/3M/6M windows, and identifies "trending" stocks - ones where
momentum is both strong AND accelerating, not just today's biggest mover.
"""
import pandas as pd

from src import cache_db, scoring


def build_momentum_table(symbols: list, benchmark_symbol: str = "NIFTY50") -> pd.DataFrame:
    """One row per stock: 1M/3M/6M Momentum Scores plus raw return context."""
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    rows = []
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if df.empty or benchmark_df.empty:
            continue
        row = {"symbol": symbol}
        for label, days in scoring.LOOKBACKS.items():
            result = scoring.composite_score(df, benchmark_df, days)
            row[f"{label} Score"] = result["score"]
        if len(df) >= 2:
            row["1D %"] = round((df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100, 2)
        rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty and "3M Score" in result.columns:
        result = result.sort_values("3M Score", ascending=False, na_position="last")
    return result


def trending_stocks(symbols: list, benchmark_symbol: str = "NIFTY50", top_n: int = 10) -> pd.DataFrame:
    """Ranks stocks by Trending Score: 70% current 3M momentum score,
    30% how much that score has improved over the last week. This surfaces
    stocks with building momentum, not just today's biggest % gainer."""
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    rows = []
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if df.empty or len(df) < 90 or benchmark_df.empty:
            continue

        current = scoring.composite_score(df, benchmark_df, scoring.LOOKBACKS["3M"])["score"]

        df_1w_ago = df.iloc[:-5] if len(df) > 5 else df
        bench_1w_ago = benchmark_df[benchmark_df["date"] <= df_1w_ago["date"].iloc[-1]] if not df_1w_ago.empty else benchmark_df
        past = scoring.composite_score(df_1w_ago, bench_1w_ago, scoring.LOOKBACKS["3M"])["score"] if len(df_1w_ago) >= 90 else current

        trend_sc = scoring.trending_score(current, past)
        rows.append({
            "symbol": symbol,
            "Momentum Score": current,
            "1W ago": past,
            "Change": round(current - past, 1),
            "Trending Score": trend_sc,
        })

    columns = ["symbol", "Momentum Score", "1W ago", "Change", "Trending Score"]
    result = pd.DataFrame(rows, columns=columns)
    if not result.empty:
        result = result.sort_values("Trending Score", ascending=False).head(top_n)
    return result


def top_movers(symbols: list, top_n: int = 10) -> dict:
    """Simple 1-day % gainers/losers, for the Market Overview page."""
    rows = []
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if len(df) < 2:
            continue
        change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
        vol_ratio = None
        if len(df) >= 21:
            avg_vol = df["volume"].iloc[-21:-1].mean()
            if avg_vol > 0:
                vol_ratio = round(df["volume"].iloc[-1] / avg_vol, 2)
        rows.append({"symbol": symbol, "1D %": round(change, 2), "Volume x": vol_ratio})

    result = pd.DataFrame(rows)
    if result.empty:
        return {"gainers": result, "losers": result}
    gainers = result.sort_values("1D %", ascending=False).head(top_n)
    losers = result.sort_values("1D %", ascending=True).head(top_n)
    return {"gainers": gainers, "losers": losers}


def stock_score_breakdown(symbol: str, benchmark_symbol: str = "NIFTY50") -> dict:
    """Full detail for the Stock Detail page: scores at each lookback,
    the component breakdown for 3M, and score history for the trend chart."""
    df = cache_db.load_ohlcv(symbol)
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    if df.empty or benchmark_df.empty:
        return {}

    scores_by_window = {}
    for label, days in scoring.LOOKBACKS.items():
        scores_by_window[label] = scoring.composite_score(df, benchmark_df, days)

    history = scoring.score_history(df, benchmark_df, scoring.LOOKBACKS["3M"], points=6)

    returns = {}
    for label, days in {"1D": 1, "1W": 5, **scoring.LOOKBACKS}.items():
        if len(df) > days:
            returns[label] = round((df["close"].iloc[-1] - df["close"].iloc[-days - 1]) / df["close"].iloc[-days - 1] * 100, 2)

    return {
        "symbol": symbol,
        "scores_by_window": scores_by_window,
        "score_history": history,
        "returns": returns,
        "latest_price": df["close"].iloc[-1] if not df.empty else None,
    }


def momentum_drivers(symbol: str, benchmark_symbol: str = "NIFTY50") -> list:
    """Generates plain-English bullet points explaining why a stock's score
    is what it is, based on the same components that feed the score."""
    df = cache_db.load_ohlcv(symbol)
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    if df.empty or len(df) < 200 or benchmark_df.empty:
        return []

    drivers = []
    days = scoring.LOOKBACKS["3M"]
    comp = scoring.composite_score(df, benchmark_df, days)["components"]

    if comp["Relative Strength"] >= 18:
        drivers.append(("up", "3-month relative strength vs Nifty 50 is strong"))
    elif comp["Relative Strength"] <= 8:
        drivers.append(("down", "Underperforming Nifty 50 over the last 3 months"))

    close = df["close"]
    price = close.iloc[-1]
    dma50 = close.rolling(50).mean().iloc[-1]
    if price > dma50 and close.iloc[-6] <= close.rolling(50).mean().iloc[-6]:
        drivers.append(("up", "Price recently crossed above its 50-day average"))
    elif price < dma50:
        drivers.append(("down", "Trading below its 50-day average"))

    if comp["Volume"] >= 11:
        drivers.append(("up", "Recent volume is well above its 20-day average"))

    if comp["Breakout"] >= 8:
        drivers.append(("up", "Trading near its 52-week high"))
    elif comp["Breakout"] <= 2:
        drivers.append(("down", "Well off its 52-week high"))

    if comp["Efficiency"] <= 2:
        drivers.append(("neutral", "Price action has been choppy rather than trending smoothly"))

    return drivers
