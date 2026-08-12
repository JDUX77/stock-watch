"""
Loads your Angel One credentials.

Works in two modes automatically:
  - Locally: reads from a ".env" file (see .env.example) via python-dotenv.
  - Deployed on Streamlit Community Cloud: reads from the app's "Secrets"
    settings in the Streamlit Cloud dashboard (st.secrets) - nothing to
    install, and your keys never touch the code or GitHub repo.

Either way, this file never contains any actual secret values itself.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


def _get(key: str, default: str = "") -> str:
    """Checks Streamlit Cloud secrets first, then falls back to .env / OS env vars."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


ANGEL_API_KEY = _get("ANGEL_API_KEY")
ANGEL_CLIENT_ID = _get("ANGEL_CLIENT_ID")
ANGEL_MPIN = _get("ANGEL_MPIN")
ANGEL_TOTP_SECRET = _get("ANGEL_TOTP_SECRET")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "market_cache.db"


def credentials_present() -> bool:
    """Returns True only if all four required secrets have been filled in."""
    return all([ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_MPIN, ANGEL_TOTP_SECRET])
