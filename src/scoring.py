"""
The scoring engine: turns raw price/volume history into a single 0-100
"Momentum Score" per stock or index, built from six weighted components.
This is the shared math used by the Momentum, Sector Rotation, and Market
Overview modules, so a stock's score means the same thing everywhere in
the app.

Score components (100 points total):
  Price Momentum   28 pts - how far/fast has it moved
  Relative Strength 24 pts - outperformance vs the benchmark (Nifty 50)
  Trend             15 pts - is price above its DMAs, and are DMAs stacked
  Volume             15 pts - is the move backed by above-average volume
  Breakout           10 pts - how close to a 52-week high
  Efficiency          8 pts - how "clean" the move is (trending vs choppy)
"""
import numpy as np
import pandas as pd

LOOKBACKS = {"1M": 21, "3M": 63, "6M": 126}


def _clip(value, lo, hi):
    return max(lo, min(hi, value))


def price_momentum_score(df: pd.DataFrame, days: int, max_points: float = 28) -> float:
    """Scales the raw % return over the window into points. A +25% move over
    3 months maxes this out; scaling is intentionally generous since this is
    one signal among six, not the whole score."""
    if len(df) < days + 1:
        return 0.0
    roc = (df["close"].iloc[-1] - df["close"].iloc[-days - 1]) / df["close"].iloc[-days - 1] * 100
    # Normalize: 0% return = 50% of points, +25% = full points, -25% = zero
    normalized = _clip((roc + 25) / 50, 0, 1)
    return round(normalized * max_points, 2)


def relative_strength_score(df: pd.DataFrame, benchmark_df: pd.DataFrame, days: int, max_points: float = 24) -> float:
    """Scales outperformance vs Nifty 50 over the window. Matching the index
    exactly = half points; +15% outperformance = full points."""
    if len(df) < days + 1 or len(benchmark_df) < days + 1:
        return 0.0
    stock_roc = (df["close"].iloc[-1] - df["close"].iloc[-days - 1]) / df["close"].iloc[-days - 1] * 100
    bench_roc = (benchmark_df["close"].iloc[-1] - benchmark_df["close"].iloc[-days - 1]) / benchmark_df["close"].iloc[-days - 1] * 100
    rs = stock_roc - bench_roc
    normalized = _clip((rs + 15) / 30, 0, 1)
    return round(normalized * max_points, 2)


def trend_score(df: pd.DataFrame, max_points: float = 15) -> float:
    """Rewards price trading above its 20/50/200-day averages, and those
    averages being stacked in the healthy order (20 > 50 > 200)."""
    if len(df) < 200:
        return 0.0
    close = df["close"]
    price = close.iloc[-1]
    dma20 = close.rolling(20).mean().iloc[-1]
    dma50 = close.rolling(50).mean().iloc[-1]
    dma200 = close.rolling(200).mean().iloc[-1]

    points = 0.0
    if price > dma20:
        points += max_points * 0.25
    if price > dma50:
        points += max_points * 0.25
    if price > dma200:
        points += max_points * 0.25
    if dma20 > dma50 > dma200:
        points += max_points * 0.25
    return round(points, 2)


def volume_score(df: pd.DataFrame, lookback: int = 20, max_points: float = 15) -> float:
    """Rewards recent volume running above its own 20-day average - a move
    with rising participation is more trustworthy than one on thin volume."""
    if len(df) < lookback + 5:
        return 0.0
    recent_avg = df["volume"].iloc[-5:].mean()
    baseline_avg = df["volume"].iloc[-lookback - 5:-5].mean()
    if baseline_avg == 0:
        return 0.0
    ratio = recent_avg / baseline_avg
    normalized = _clip((ratio - 0.5) / 1.5, 0, 1)  # 0.5x=0pts, 2x=full pts
    return round(normalized * max_points, 2)


def breakout_score(df: pd.DataFrame, lookback: int = 252, max_points: float = 10) -> float:
    """Rewards proximity to the 52-week high - full points if at/near it."""
    if len(df) < lookback:
        lookback = len(df)
    if lookback < 20:
        return 0.0
    window = df["close"].iloc[-lookback:]
    high = window.max()
    price = window.iloc[-1]
    if high == 0:
        return 0.0
    pct_from_high = (high - price) / high * 100
    normalized = _clip((15 - pct_from_high) / 15, 0, 1)  # at high=full, 15%+ below=0
    return round(normalized * max_points, 2)


def efficiency_score(df: pd.DataFrame, days: int = 21, max_points: float = 8) -> float:
    """Kaufman's Efficiency Ratio: net price change divided by total path
    length of daily moves. A stock that trends smoothly upward scores near 1;
    one that whipsaws up and down to reach the same endpoint scores near 0."""
    if len(df) < days + 1:
        return 0.0
    window = df["close"].iloc[-days - 1:]
    net_change = abs(window.iloc[-1] - window.iloc[0])
    daily_moves = window.diff().abs().sum()
    if daily_moves == 0:
        return 0.0
    efficiency_ratio = net_change / daily_moves
    return round(_clip(efficiency_ratio, 0, 1) * max_points, 2)


def composite_score(df: pd.DataFrame, benchmark_df: pd.DataFrame, days: int) -> dict:
    """Combines all six components into a single 0-100 score, with the
    breakdown returned alongside so the UI can explain *why* the score is
    what it is."""
    components = {
        "Price Momentum": price_momentum_score(df, days),
        "Relative Strength": relative_strength_score(df, benchmark_df, days),
        "Trend": trend_score(df),
        "Volume": volume_score(df),
        "Breakout": breakout_score(df),
        "Efficiency": efficiency_score(df, days),
    }
    total = round(sum(components.values()), 1)
    return {"score": total, "components": components}


def score_history(df: pd.DataFrame, benchmark_df: pd.DataFrame, days: int, points: int = 6) -> pd.DataFrame:
    """Recomputes the composite score at several points in the past, so the
    UI can plot how a stock's score has evolved over time (not just today's
    snapshot)."""
    if len(df) < days + 30:
        return pd.DataFrame()

    rows = []
    step = max(len(df) // points, 5)
    indices = list(range(len(df) - 1, days + 20, -step))[:points]
    indices.reverse()

    for idx in indices:
        sub_df = df.iloc[: idx + 1]
        sub_bench = benchmark_df[benchmark_df["date"] <= df["date"].iloc[idx]]
        if len(sub_df) < days + 1 or len(sub_bench) < days + 1:
            continue
        result = composite_score(sub_df, sub_bench, days)
        rows.append({"date": df["date"].iloc[idx], "score": result["score"]})

    return pd.DataFrame(rows)


def trending_score(current_score: float, score_1w_ago: float) -> float:
    """Trending = strong momentum AND accelerating momentum, not just a big
    single-day gainer. Weighted 70% current level, 30% recent change."""
    change = current_score - score_1w_ago
    # Normalize the change component: +/-20 pts change maps to 0-100
    change_component = _clip((change + 20) / 40, 0, 1) * 100
    return round(current_score * 0.7 + change_component * 0.3, 1)


def score_to_status(score: float) -> tuple:
    """Maps a 0-100 score to a color band and label, used consistently
    across every screen in the app."""
    if score >= 90:
        return ("#1B5E20", "Very Strong")
    elif score >= 75:
        return ("#2E7D32", "Strong")
    elif score >= 60:
        return ("#9E9D24", "Improving")
    elif score >= 45:
        return ("#F9A825", "Neutral")
    elif score >= 30:
        return ("#EF6C00", "Weak")
    else:
        return ("#C62828", "Very Weak")
