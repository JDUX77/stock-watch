"""
Sector rotation module: scores each NSE sector index using the same
composite scoring engine as individual stocks (so "Auto sector scores 91"
and "Maruti scores 91" mean the same thing), plus the RRG-style relative
rotation view, plus drill-down into the stocks within a sector.
"""
import pandas as pd

from src import cache_db, scoring, sector_map
from src.data_fetch import SECTOR_INDICES, BENCHMARK_INDEX


def build_sector_table(benchmark_symbol: str = "NIFTY50") -> pd.DataFrame:
    """One row per sector: Momentum Score, Relative Strength, Breadth
    (% of the sector's watchlist stocks with a rising 3M score), color band."""
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    rows = []
    for sector in SECTOR_INDICES:
        df = cache_db.load_ohlcv(sector)
        if df.empty or benchmark_df.empty:
            continue

        scores = {label: scoring.composite_score(df, benchmark_df, days)["score"]
                  for label, days in scoring.LOOKBACKS.items()}
        color, label = scoring.score_to_status(scores["3M"])

        stocks = sector_map.stocks_in_sector(sector)
        positive_count = 0
        counted = 0
        for stock in stocks:
            stock_df = cache_db.load_ohlcv(stock)
            if len(stock_df) >= 90:
                stock_score = scoring.composite_score(stock_df, benchmark_df, scoring.LOOKBACKS["3M"])["score"]
                if stock_score >= 60:
                    positive_count += 1
                counted += 1
        breadth_pct = round(positive_count / counted * 100, 0) if counted else None

        rows.append({
            "sector": sector,
            "1M Score": scores["1M"],
            "3M Score": scores["3M"],
            "6M Score": scores["6M"],
            "Breadth": breadth_pct,
            "Status": label,
            "_color": color,
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("3M Score", ascending=False)
    return result


def _rs_ratio_series(sector_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.Series:
    merged = pd.merge(
        sector_df[["date", "close"]], benchmark_df[["date", "close"]],
        on="date", suffixes=("_sector", "_bench"),
    )
    ratio = (merged["close_sector"] / merged["close_bench"]) * 100
    normalized = 100 * ratio / ratio.rolling(60, min_periods=10).mean()
    normalized.index = merged["date"]
    return normalized.dropna()


def build_rrg_table(lookback_days: int = 10) -> pd.DataFrame:
    """RRG quadrant view: x = relative strength ratio, y = momentum of that
    ratio. Leading / Weakening / Lagging / Improving."""
    benchmark_df = cache_db.load_ohlcv(BENCHMARK_INDEX)
    if benchmark_df.empty:
        return pd.DataFrame()

    rows = []
    for sector in SECTOR_INDICES:
        sector_df = cache_db.load_ohlcv(sector)
        if sector_df.empty or len(sector_df) < 70:
            continue

        ratio_series = _rs_ratio_series(sector_df, benchmark_df)
        if len(ratio_series) < lookback_days + 1:
            continue

        current_ratio = ratio_series.iloc[-1]
        momentum = (ratio_series.iloc[-1] / ratio_series.iloc[-lookback_days - 1]) * 100

        if current_ratio >= 100 and momentum >= 100:
            quadrant = "Leading"
        elif current_ratio >= 100 and momentum < 100:
            quadrant = "Weakening"
        elif current_ratio < 100 and momentum < 100:
            quadrant = "Lagging"
        else:
            quadrant = "Improving"

        rows.append({
            "sector": sector, "rs_ratio": round(current_ratio, 2),
            "rs_momentum": round(momentum, 2), "quadrant": quadrant,
        })

    return pd.DataFrame(rows).sort_values("rs_ratio", ascending=False) if rows else pd.DataFrame()


def stocks_in_sector_table(sector: str, benchmark_symbol: str = "NIFTY50") -> pd.DataFrame:
    """Drill-down: every watchlist stock belonging to one sector, with scores."""
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    stocks = sector_map.stocks_in_sector(sector)
    rows = []
    for stock in stocks:
        df = cache_db.load_ohlcv(stock)
        if df.empty or benchmark_df.empty or len(df) < 90:
            continue
        scores = {label: scoring.composite_score(df, benchmark_df, days)["score"]
                  for label, days in scoring.LOOKBACKS.items()}
        color, label = scoring.score_to_status(scores["3M"])
        rows.append({
            "symbol": stock, "1M Score": scores["1M"], "3M Score": scores["3M"],
            "6M Score": scores["6M"], "Status": label,
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("3M Score", ascending=False)
    return result
