"""
Sector rotation module: shows which NSE sectors are gaining or losing
relative strength versus the broader market, so you can see where money is
rotating into and out of.

Uses a simplified Relative Rotation Graph (RRG) approach:
  x-axis = relative strength ratio  (sector / benchmark, normalized)
  y-axis = momentum of that ratio   (is the ratio itself rising or falling)

Four quadrants:
  Leading    (x>100, y>100) - outperforming and still gaining strength
  Weakening  (x>100, y<100) - outperforming but losing steam
  Lagging    (x<100, y<100) - underperforming and still falling
  Improving  (x<100, y>100) - underperforming but starting to turn up
"""
import pandas as pd

from src import cache_db
from src.data_fetch import SECTOR_INDICES, BENCHMARK_INDEX


def _rs_ratio_series(sector_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.Series:
    merged = pd.merge(
        sector_df[["date", "close"]], benchmark_df[["date", "close"]],
        on="date", suffixes=("_sector", "_bench"),
    )
    ratio = (merged["close_sector"] / merged["close_bench"]) * 100
    # Normalize around 100 using a rolling mean so the ratio is comparable across sectors
    normalized = 100 * ratio / ratio.rolling(60, min_periods=10).mean()
    normalized.index = merged["date"]
    return normalized.dropna()


def build_rrg_table(lookback_days: int = 10) -> pd.DataFrame:
    """One row per sector index: current RS ratio, RS momentum, and quadrant."""
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
            "sector": sector,
            "rs_ratio": round(current_ratio, 2),
            "rs_momentum": round(momentum, 2),
            "quadrant": quadrant,
        })

    return pd.DataFrame(rows).sort_values("rs_ratio", ascending=False)


def simple_sector_leaderboard() -> pd.DataFrame:
    """Fallback/simpler view: just 1W/1M/3M returns per sector, ranked.
    Useful before the full RRG table has enough history to be meaningful."""
    from src.momentum import rate_of_change

    rows = []
    for sector in SECTOR_INDICES:
        df = cache_db.load_ohlcv(sector)
        if df.empty:
            continue
        rows.append({
            "sector": sector,
            "1W %": rate_of_change(df, 5),
            "1M %": rate_of_change(df, 21),
            "3M %": rate_of_change(df, 63),
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("1M %", ascending=False, na_position="last")
    return result
