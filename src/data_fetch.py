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

# Curated list of major NSE sector indices we track for sector rotation.
# (symbol as it appears in Angel One's instrument master, under exchange NSE)
SECTOR_INDICES = [
    "NIFTY AUTO", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY FMCG",
    "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
    "NIFTY PSU BANK", "NIFTY REALTY", "NIFTY ENERGY", "NIFTY INFRA",
    "NIFTY CONSR DURBL", "NIFTY HEALTHCARE",
]
BENCHMARK_INDEX = "NIFTY 50"


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
