"""
Maps every stock to its NSE sector index, so the app can support the
Market -> Sector -> Stock drill-down navigation across the full Nifty 500
universe (not just a hand-picked watchlist).

Built dynamically from NSE's official Nifty 500 constituent list, which
includes each company's "Industry" classification (e.g. "Automobile and
Auto Components"). That gets matched by keyword to one of the 14 broad
NIFTY sector indices this app already tracks.

If the live Nifty 500 fetch has never succeeded (e.g. first run before any
refresh, or NSE unreachable), falls back to a small hand-curated map for
the original 20-stock starter watchlist, so the app still works.
"""
from src import cache_db
from src.data_fetch import fetch_nifty500_constituents, SECTOR_INDICES

# Keyword -> sector index. Checked in order; first match wins. Based on the
# "Industry" labels NSE uses in the Nifty 500 constituent list.
_INDUSTRY_KEYWORDS = [
    (["bank"], "NIFTY BANK"),
    (["financial services", "finance", "insurance", "nbfc"], "NIFTY FIN SERVICE"),
    (["automobile", "auto components"], "NIFTY AUTO"),
    (["fast moving consumer goods", "fmcg"], "NIFTY FMCG"),
    (["information technology", "software", "it services"], "NIFTY IT"),
    (["media", "entertainment", "publication"], "NIFTY MEDIA"),
    (["metals", "mining"], "NIFTY METAL"),
    (["pharmaceuticals", "biotechnology"], "NIFTY PHARMA"),
    (["realty", "real estate"], "NIFTY REALTY"),
    (["oil", "gas", "power", "energy", "utilities"], "NIFTY ENERGY"),
    (["construction", "capital goods", "infrastructure", "cement", "services"], "NIFTY INFRA"),
    (["consumer durables"], "NIFTY CONSR DURBL"),
    (["healthcare"], "NIFTY HEALTHCARE"),
]

# Emergency fallback covering only the original 20-stock starter watchlist,
# used if the Nifty 500 industry data has never been successfully fetched.
_FALLBACK_MAP = {
    "RELIANCE": "NIFTY ENERGY", "TCS": "NIFTY IT", "HDFCBANK": "NIFTY BANK",
    "ICICIBANK": "NIFTY BANK", "INFY": "NIFTY IT", "HINDUNILVR": "NIFTY FMCG",
    "ITC": "NIFTY FMCG", "SBIN": "NIFTY PSU BANK", "BHARTIARTL": "NIFTY INFRA",
    "KOTAKBANK": "NIFTY BANK", "LT": "NIFTY INFRA", "AXISBANK": "NIFTY BANK",
    "MARUTI": "NIFTY AUTO", "SUNPHARMA": "NIFTY PHARMA", "TITAN": "NIFTY CONSR DURBL",
    "ULTRACEMCO": "NIFTY INFRA", "BAJFINANCE": "NIFTY FIN SERVICE", "WIPRO": "NIFTY IT",
    "ADANIENT": "NIFTY METAL", "TATAMOTORS": "NIFTY AUTO",
}

_cached_map = None


def _industry_to_sector(industry: str) -> str:
    industry_lower = industry.lower()
    for keywords, sector in _INDUSTRY_KEYWORDS:
        if any(kw in industry_lower for kw in keywords):
            return sector
    return "Unclassified"


def _build_map() -> dict:
    try:
        constituents = fetch_nifty500_constituents()
        mapping = {}
        for c in constituents:
            if c.get("symbol") and c.get("industry"):
                mapping[c["symbol"]] = _industry_to_sector(c["industry"])
        if mapping:
            return mapping
    except Exception:
        pass
    return dict(_FALLBACK_MAP)


def get_map() -> dict:
    """Cached in memory for the life of the Streamlit session/process -
    rebuilding this dict on every rerun would be wasteful."""
    global _cached_map
    if _cached_map is None:
        _cached_map = _build_map()
    return _cached_map


def sector_for_stock(symbol: str) -> str:
    return get_map().get(symbol, "Unclassified")


def stocks_in_sector(sector: str) -> list:
    return [s for s, sec in get_map().items() if sec == sector]
