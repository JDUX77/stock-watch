"""
Pulls the latest daily price history from Angel One for your stock
universe, benchmark index, and sector indices, and saves it into the local
cache. Run this once a day (e.g. after market close) via the "Refresh data"
button in the app, or manually with: python -m src.refresh_job

By default this now covers the full Nifty 500 (~500 liquid NSE stocks),
fetched live from NSE's official constituent list. A full refresh takes
roughly 8-15 minutes depending on Angel One's response times - this is
expected, not a bug. Don't close the browser tab while it's running.

If you'd rather use a small, fast starter list instead (e.g. for quick
testing), call run_refresh(watchlist=FALLBACK_WATCHLIST) directly.
"""
import time

from src.angel_auth import get_session
from src.data_fetch import (
    load_instrument_master, get_token, fetch_daily_history,
    fetch_nifty500_constituents, SECTOR_INDICES, BENCHMARK_INDEX,
)
from src import cache_db

# Emergency fallback list, used only if NSE's Nifty 500 list can't be
# fetched AND there's no cached copy from a previous successful run.
FALLBACK_WATCHLIST = [
    "RELIANCE-EQ", "TCS-EQ", "HDFCBANK-EQ", "ICICIBANK-EQ", "INFY-EQ",
    "HINDUNILVR-EQ", "ITC-EQ", "SBIN-EQ", "BHARTIARTL-EQ", "KOTAKBANK-EQ",
    "LT-EQ", "AXISBANK-EQ", "MARUTI-EQ", "SUNPHARMA-EQ", "TITAN-EQ",
    "ULTRACEMCO-EQ", "BAJFINANCE-EQ", "WIPRO-EQ", "ADANIENT-EQ", "TATAMOTORS-EQ",
]

INDEX_SYMBOL_MAP = {BENCHMARK_INDEX: "NIFTY50", **{s: s for s in SECTOR_INDICES}}


def get_watchlist() -> list:
    """Returns the full Nifty 500 as a list of 'SYMBOL-EQ' strings. Falls
    back to the small starter list if NSE's site can't be reached and
    there's no cached copy from a previous run."""
    try:
        constituents = fetch_nifty500_constituents()
        symbols = [f"{c['symbol']}-EQ" for c in constituents if c.get("symbol")]
        if symbols:
            return symbols
    except Exception as e:
        print(f"Could not fetch Nifty 500 list, using starter watchlist instead: {e}")
    return FALLBACK_WATCHLIST


def run_refresh(watchlist=None, progress_callback=None):
    """progress_callback(current, total, label) - optional, for UI progress bars."""
    watchlist = watchlist or get_watchlist()
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
        time.sleep(0.2)  # conservative pacing to stay well under Angel One's rate limit over a long run

    cache_db.set_last_refresh()


if __name__ == "__main__":
    run_refresh(progress_callback=lambda i, t, s: print(f"[{i}/{t}] {s}"))
    print("Done.")
