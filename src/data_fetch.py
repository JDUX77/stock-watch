"""
Fetches the list of tradeable NSE symbols (with their internal "tokens")
and historical price candles from Angel One SmartAPI.
"""
import time
import json
from datetime import datetime, timedelta

import requests
import pandas as pd

import config

INSTRUMENT_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)
INSTRUMENT_CACHE_PATH = config.DATA_DIR / "instrument_master.json"

# Where NSE publishes the official Nifty 500 constituent list (symbol + industry).
# Two URLs tried in order since NSE has migrated domains before.
NIFTY500_CSV_URLS = [
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
]
NIFTY500_CACHE_PATH = config.DATA_DIR / "nifty500_constituents.json"

# Curated list of major NSE sector indices we track for sector rotation.
# (symbol as it appears in Angel One's instrument master, under exchange NSE)
SECTOR_INDICES = [
    "NIFTY AUTO", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY FMCG",
    "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
    "NIFTY PSU BANK", "NIFTY REALTY", "NIFTY ENERGY", "NIFTY INFRA",
    "NIFTY CONSR DURBL", "NIFTY HEALTHCARE",
]
BENCHMARK_INDEX = "NIFTY 50"

# Cache names used for index data (as opposed to individual stocks) - used
# elsewhere in the app to separate "the market universe" from "the indices
# that measure it".
INDEX_CACHE_NAMES = {"NIFTY50"} | set(SECTOR_INDICES)


def load_instrument_master(force_refresh: bool = False) -> pd.DataFrame:
    """Downloads (or loads a cached copy of) the full NSE instrument list.

    This file maps human-readable symbols like 'RELIANCE-EQ' to the numeric
    'token' that Angel One's API actually requires for data requests.
    Refreshed at most once a day since it rarely changes.
    """
    if not force_refresh and INSTRUMENT_CACHE_PATH.exists():
        age_hours = (time.time() - INSTRUMENT_CACHE_PATH.stat().st_mtime) / 3600
        if age_hours < 24:
            with open(INSTRUMENT_CACHE_PATH) as f:
                return pd.DataFrame(json.load(f))

    resp = requests.get(INSTRUMENT_MASTER_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    with open(INSTRUMENT_CACHE_PATH, "w") as f:
        json.dump(data, f)
    return pd.DataFrame(data)


def fetch_nifty500_constituents(force_refresh: bool = False) -> list:
    """Downloads (or loads a cached copy of) the official Nifty 500 list from
    NSE, including each company's Industry classification. Cached for 7 days
    since the index only rebalances twice a year - no need to refetch daily.

    Returns a list of dicts: [{"symbol": "RELIANCE", "company_name": "...",
    "industry": "Oil Gas & Consumable Fuels"}, ...]

    Falls back to a stale cached copy if NSE's site is unreachable, and
    raises only if there's no cache at all to fall back on.
    """
    if not force_refresh and NIFTY500_CACHE_PATH.exists():
        age_days = (time.time() - NIFTY500_CACHE_PATH.stat().st_mtime) / 86400
        if age_days < 7:
            with open(NIFTY500_CACHE_PATH) as f:
                return json.load(f)

    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        "Accept": "text/csv,application/csv,*/*",
    }
    session = requests.Session()
    session.headers.update(headers)
    try:
        # NSE requires a "real browser" visit first to set session cookies,
        # or direct CSV requests often get rejected.
        session.get("https://www.nseindia.com", timeout=10)
    except Exception:
        pass

    last_error = None
    for url in NIFTY500_CSV_URLS:
        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            constituents = _parse_nifty500_csv(resp.text)
            if constituents:
                with open(NIFTY500_CACHE_PATH, "w") as f:
                    json.dump(constituents, f)
                return constituents
        except Exception as e:
            last_error = e
            continue

    if NIFTY500_CACHE_PATH.exists():
        with open(NIFTY500_CACHE_PATH) as f:
            return json.load(f)
    raise RuntimeError(f"Could not fetch the Nifty 500 list from NSE and no cached copy exists: {last_error}")


def _parse_nifty500_csv(text: str) -> list:
    import csv
    import io
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        symbol = (row.get("Symbol") or row.get("SYMBOL") or "").strip()
        industry = (row.get("Industry") or row.get("INDUSTRY") or "").strip()
        company = (row.get("Company Name") or row.get("COMPANY NAME") or "").strip()
        if symbol:
            out.append({"symbol": symbol, "industry": industry, "company_name": company})
    return out



def get_token(instruments: pd.DataFrame, symbol: str, exch_seg: str = "NSE") -> str:
    """Looks up the numeric token for a given symbol, e.g. 'RELIANCE-EQ'."""
    match = instruments[
        (instruments["symbol"] == symbol) & (instruments["exch_seg"] == exch_seg)
    ]
    if match.empty:
        raise ValueError(f"Symbol '{symbol}' not found in instrument master.")
    return match.iloc[0]["token"]


def fetch_historical_candles(
    angel_client, symbol_token: str, exchange: str, interval: str,
    from_date: datetime, to_date: datetime,
) -> pd.DataFrame:
    """Fetches OHLCV candles for one symbol between two dates.

    interval: one of ONE_DAY, ONE_HOUR, FIFTEEN_MINUTE, etc.
    """
    params = {
        "exchange": exchange,
        "symboltoken": symbol_token,
        "interval": interval,
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M"),
    }
    response = angel_client.getCandleData(params)
    if not response.get("status"):
        raise RuntimeError(f"Historical data fetch failed: {response.get('message')}")

    candles = response["data"]
    df = pd.DataFrame(
        candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def fetch_daily_history(angel_client, symbol_token, exchange="NSE", days_back=400) -> pd.DataFrame:
    """Convenience wrapper: fetch ~days_back of daily candles up to today."""
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)
    return fetch_historical_candles(
        angel_client, symbol_token, exchange, "ONE_DAY", from_date, to_date
    )
