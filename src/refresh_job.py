"""
Pulls the latest daily price history from Angel One for your full stock
list, benchmark index, and sector indices, and saves it into the local
cache. Run this once a day (e.g. after market close) via the "Refresh data"
button in the app, or manually with: python -m src.refresh_job
"""
import time

from src.angel_auth import get_session
from src.data_fetch import (
    load_instrument_master, get_token, fetch_daily_history,
    SECTOR_INDICES, BENCHMARK_INDEX,
)
from src import cache_db

# Starter watchlist - edit this list to add/remove stocks you care about.
# Format must match Angel One's symbol naming: 'RELIANCE-EQ', 'TCS-EQ', etc.
DEFAULT_WATCHLIST = [
    "RELIANCE-EQ", "TCS-EQ", "HDFCBANK-EQ", "ICICIBANK-EQ", "INFY-EQ",
    "HINDUNILVR-EQ", "ITC-EQ", "SBIN-EQ", "BHARTIARTL-EQ", "KOTAKBANK-EQ",
    "LT-EQ", "AXISBANK-EQ", "MARUTI-EQ", "SUNPHARMA-EQ", "TITAN-EQ",
    "ULTRACEMCO-EQ", "BAJFINANCE-EQ", "WIPRO-EQ", "ADANIENT-EQ", "TATAMOTORS-EQ",
]

INDEX_SYMBOL_MAP = {BENCHMARK_INDEX: "NIFTY50", **{s: s for s in SECTOR_INDICES}}


def run_refresh(watchlist=None, progress_callback=None):
    """progress_callback(current, total, label) - optional, for UI progress bars."""
    watchlist = watchlist or DEFAULT_WATCHLIST
    cache_db.init_db()

    session = get_session()
    client = session.connect()
    instruments = load_instrument_master()

    tasks = []
    for symbol in watchlist:
        tasks.append(("NSE", symbol, symbol.replace("-EQ", "")))
    for index_symbol, cache_name in INDEX_SYMBOL_MAP.items():
        tasks.append(("NSE", index_symbol, cache_name))

    total = len(tasks)
    for i, (exchange, api_symbol, cache_name) in enumerate(tasks, start=1):
        if progress_callback:
            progress_callback(i, total, cache_name)
        try:
            token = get_token(instruments, api_symbol, exch_seg="NSE")
            df = fetch_daily_history(client, token, exchange=exchange, days_back=400)
            cache_db.save_ohlcv(cache_name, df)
        except Exception as e:
            print(f"Skipped {api_symbol}: {e}")
        time.sleep(0.15)  # stay comfortably under the 10 req/sec limit

    cache_db.set_last_refresh()


if __name__ == "__main__":
    run_refresh(progress_callback=lambda i, t, s: print(f"[{i}/{t}] {s}"))
    print("Done.")
