"""
Maps each stock in the watchlist to its NSE sector, so the app can support
the Market -> Sector -> Stock drill-down navigation.

NOTE: this is a manually curated map covering the ~20-stock starter
watchlist. If you expand DEFAULT_WATCHLIST in refresh_job.py, add the new
symbols here too, or the sector drill-down won't be able to place them.

True "industry" sub-classification (e.g. Auto -> Passenger Vehicles vs
Auto Components) isn't included yet - NSE's official indices only go down
to sector level, so a proper industry breakdown needs a separate
classification data source. This map stops at sector level for now.
"""

STOCK_SECTOR_MAP = {
    "RELIANCE": "NIFTY ENERGY",
    "TCS": "NIFTY IT",
    "HDFCBANK": "NIFTY BANK",
    "ICICIBANK": "NIFTY BANK",
    "INFY": "NIFTY IT",
    "HINDUNILVR": "NIFTY FMCG",
    "ITC": "NIFTY FMCG",
    "SBIN": "NIFTY PSU BANK",
    "BHARTIARTL": "NIFTY INFRA",
    "KOTAKBANK": "NIFTY BANK",
    "LT": "NIFTY INFRA",
    "AXISBANK": "NIFTY BANK",
    "MARUTI": "NIFTY AUTO",
    "SUNPHARMA": "NIFTY PHARMA",
    "TITAN": "NIFTY CONSR DURBL",
    "ULTRACEMCO": "NIFTY INFRA",
    "BAJFINANCE": "NIFTY FIN SERVICE",
    "WIPRO": "NIFTY IT",
    "ADANIENT": "NIFTY METAL",
    "TATAMOTORS": "NIFTY AUTO",
}


def sector_for_stock(symbol: str) -> str:
    return STOCK_SECTOR_MAP.get(symbol, "Unclassified")


def stocks_in_sector(sector: str) -> list:
    return [s for s, sec in STOCK_SECTOR_MAP.items() if sec == sector]
