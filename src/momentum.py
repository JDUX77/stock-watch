"""
Momentum module: measures how strongly a stock has been moving, and how it
compares to the broader market (Nifty 50) over several time windows.
"""
import pandas as pd
import numpy as np

from src import cache_db

# Trading-day approximations for common windows
WINDOWS = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}


def rate_of_change(df: pd.DataFrame, days: int):
    """% price change over the last `days` trading days."""
    if len(df) < days + 1:
        return None
    start_price = df["close"].iloc[-days - 1]
    end_price = df["close"].iloc[-1]
    if start_price == 0:
        return None
    return round((end_price - start_price) / start_price * 100, 2)


def relative_strength(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame, days: int):
    """Stock's return minus the benchmark's return over the same window.
    Positive = stock is outperforming the index (real momentum, not just
    a market-wide rally lifting everything)."""
    stock_roc = rate_of_change(stock_df, days)
    bench_roc = rate_of_change(benchmark_df, days)
    if stock_roc is None or bench_roc is None:
        return None
    return round(stock_roc - bench_roc, 2)


def rsi(df: pd.DataFrame, period: int = 14):
    """Standard 14-day Relative Strength Index (0-100). >70 often read as
    overbought, <30 as oversold - use as a confirmation signal, not standalone."""
    if len(df) < period + 1:
        return None
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def volume_confirmation(df: pd.DataFrame, lookback: int = 20) -> bool:
    """True if today's volume is above the recent average - confirms a move
    is backed by real participation, not a thin/illiquid spike."""
    if len(df) < lookback + 1:
        return False
    avg_vol = df["volume"].iloc[-lookback - 1:-1].mean()
    return df["volume"].iloc[-1] > avg_vol


def build_momentum_table(symbols: list, benchmark_symbol: str = "NIFTY50") -> pd.DataFrame:
    """Builds a leaderboard: one row per symbol, with RoC / RS / RSI columns."""
    benchmark_df = cache_db.load_ohlcv(benchmark_symbol)
    rows = []
    for symbol in symbols:
        df = cache_db.load_ohlcv(symbol)
        if df.empty:
            continue
        row = {"symbol": symbol}
        for label, days in WINDOWS.items():
            row[f"RoC {label}"] = rate_of_change(df, days)
            if not benchmark_df.empty:
                row[f"RS {label}"] = relative_strength(df, benchmark_df, days)
        row["RSI(14)"] = rsi(df)
        row["Vol confirmed"] = volume_confirmation(df)
        rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty and "RS 3M" in result.columns:
        result = result.sort_values("RS 3M", ascending=False, na_position="last")
    return result
