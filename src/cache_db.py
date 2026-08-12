"""
A small local database (SQLite) that stores downloaded price history, so the
app doesn't have to re-fetch from Angel One every time you open it. Data only
needs to be refreshed once a day (after market close).
"""
import sqlite3
from datetime import datetime

import pandas as pd

import config


def get_connection():
    return sqlite3.connect(config.DB_PATH)


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_ohlcv(symbol: str, df: pd.DataFrame):
    """Saves/updates OHLCV rows for one symbol. df must have a 'timestamp' column."""
    if df.empty:
        return
    conn = get_connection()
    rows = [
        (symbol, row.timestamp.strftime("%Y-%m-%d"), row.open, row.high,
         row.low, row.close, int(row.volume))
        for row in df.itertuples()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO ohlcv (symbol, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def load_ohlcv(symbol: str) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM ohlcv "
        "WHERE symbol = ? ORDER BY date ASC",
        conn, params=(symbol,), parse_dates=["date"],
    )
    conn.close()
    return df


def list_cached_symbols() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT symbol FROM ohlcv").fetchall()
    conn.close()
    return [r[0] for r in rows]


def set_last_refresh(timestamp: datetime = None):
    conn = get_connection()
    ts = (timestamp or datetime.now()).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_refresh', ?)", (ts,)
    )
    conn.commit()
    conn.close()


def get_last_refresh():
    conn = get_connection()
    row = conn.execute("SELECT value FROM meta WHERE key = 'last_refresh'").fetchone()
    conn.close()
    return row[0] if row else None
