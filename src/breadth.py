"""
Market breadth module: measures how broad-based a market move is, i.e.
whether most stocks are participating in a rally/decline, or whether it's
just a handful of large names masking a weak underlying market.
"""
import pandas as pd

from src import cache_db


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
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "ad_ratio": round(advances / declines, 2) if declines else None,
        "pct_advancing": round(advances / total * 100, 1) if total else None,
    }


def pct_above_moving_average(symbols: list, ma_period: int = 200) -> float:
    """% of stocks currently trading above their N-day moving average.
    This is one of the clearest 'is this rally healthy' signals - above ~70%
    suggests broad strength, below ~30% suggests broad weakness."""
    above = total = 0
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if len(df) < ma_period:
            continue
        ma = df["close"].rolling(ma_period).mean().iloc[-1]
        if df["close"].iloc[-1] > ma:
            above += 1
        total += 1
    if total == 0:
        return None
    return round(above / total * 100, 1)


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


def cumulative_ad_line(symbols: list, days: int = 90) -> pd.DataFrame:
    """Builds the day-by-day cumulative advance/decline line over time -
    a rising line confirms an uptrend is broad-based; a falling line while
    price rises is a classic warning sign of a narrow, fragile rally."""
    all_dates = None
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
