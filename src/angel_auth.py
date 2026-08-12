"""
Handles logging in to Angel One SmartAPI using your saved credentials.

Angel One requires a fresh login once a day using your API key, client ID,
MPIN, and a 6-digit TOTP code generated from your TOTP secret (the same way
Google Authenticator generates codes). This module does that automatically.
"""
import pyotp
from SmartApi import SmartConnect

import config


class AngelSession:
    """Wraps a logged-in SmartConnect client and keeps it alive for reuse."""

    def __init__(self):
        self._client = None
        self._feed_token = None

    def connect(self):
        if not config.credentials_present():
            raise RuntimeError(
                "Angel One credentials are missing. Please fill in the "
                "'.env' file with your API key, client ID, MPIN, and TOTP secret."
            )

        smart_api = SmartConnect(api_key=config.ANGEL_API_KEY)
        totp = pyotp.TOTP(config.ANGEL_TOTP_SECRET).now()

        session_data = smart_api.generateSession(
            config.ANGEL_CLIENT_ID, config.ANGEL_MPIN, totp
        )

        if not session_data.get("status"):
            raise RuntimeError(
                f"Angel One login failed: {session_data.get('message', 'unknown error')}. "
                "Double check your credentials in the .env file."
            )

        self._client = smart_api
        self._feed_token = smart_api.getfeedToken()
        return self._client

    @property
    def client(self):
        if self._client is None:
            self.connect()
        return self._client


# One shared session for the whole app (Streamlit re-runs the script often,
# so we cache this at the app layer - see app.py's @st.cache_resource usage).
def get_session() -> AngelSession:
    return AngelSession()
