# India Market Dashboard

A personal dashboard showing stock momentum, sector rotation, and market
breadth for NSE stocks, plus live TradingView charts.

**Two ways to use this app:**
- **Web app (recommended, no install)** — runs in the cloud, you just open
  a URL in your browser from any device. See **DEPLOYMENT.md** instead of
  this file — it walks you through the one-time setup (~15 minutes).
- **Local install** — runs on your own computer via a terminal command.
  Keep reading below for this option.

This guide assumes zero coding experience. Follow it top to bottom.

## 1. Install Python

1. Go to https://www.python.org/downloads/
2. Download and install the latest version.
3. **Important (Windows only):** on the first install screen, tick the box
   that says "Add Python to PATH" before clicking Install.

## 2. Get your Angel One SmartAPI credentials

You need 4 things. All are free from Angel One if you have a trading account:

1. Go to https://smartapi.angelone.in/ and log in with your Angel One account.
2. Click "Create an app" — choose "Market Data APIs" (you only need to read
   data, not place trades). Note down the **API key** it gives you.
3. Your **Client ID** is your Angel One login ID (the one you use to log
   into the Angel One app).
4. Your **MPIN** is the 4-digit PIN you use to log into Angel One.
5. For the **TOTP secret**: go to https://smartapi.angelone.in/enable-totp,
   log in, and it will show you a QR code plus a text secret key underneath
   it. Copy that text secret (you'll paste it into this app — you do NOT
   need to set up Google Authenticator separately, this app generates the
   code for you automatically).

Keep these 4 values handy for the next step.

## 3. Set up the app folder

1. Extract/open the `stock-dashboard` folder you received.
2. Find the file named `.env.example` inside it.
3. Make a **copy** of it and rename the copy to exactly `.env` (no ".example").
   - On Windows: copy the file, rename the copy, remove ".example" from the end.
   - On Mac: same — copy, rename, delete ".example".
4. Open `.env` in Notepad (Windows) or TextEdit (Mac) and replace the
   placeholder text with your real values from step 2, e.g.:
   ```
   ANGEL_API_KEY=abc123yourrealkey
   ANGEL_CLIENT_ID=A123456
   ANGEL_MPIN=1234
   ANGEL_TOTP_SECRET=JBSWY3DPEHPK3PXP
   ```
5. Save and close the file.

**This `.env` file is the only place your secrets live. Never send this
file to anyone, upload it to Google Drive/email/WhatsApp, or paste its
contents into any chat.** The app is already set up to keep it out of
anything you might share (like if you ever put this project on GitHub).

## 4. Install the app's requirements

1. Open a terminal:
   - Windows: search for "Command Prompt" in the Start menu.
   - Mac: search for "Terminal" in Spotlight.
2. Navigate into the folder. Type `cd ` (with a space after) then drag the
   `stock-dashboard` folder into the terminal window and press Enter.
3. Run this command and press Enter (this installs everything the app needs,
   takes 2-3 minutes):
   ```
   pip install -r requirements.txt
   ```
   If that gives an error, try `pip3 install -r requirements.txt` instead.

## 5. Run the app

In the same terminal window, run:
```
streamlit run app.py
```

Your web browser should open automatically showing the dashboard. If it
doesn't, the terminal will print a web address like `http://localhost:8501`
— copy that into your browser.

## 6. Load your data

1. In the app's left sidebar, click **"Refresh data now"**.
2. Wait for it to finish (it fetches ~1 year of history for your watchlist
   and sector indices — takes about a minute).
3. Explore the four tabs: Momentum, Sector rotation, Market breadth, and
   Chart & watchlist.

You only need to click "Refresh data now" once a day, ideally after market
close (after 3:30 PM IST), to pull the latest prices.

## Customizing your watchlist

By default the app tracks 20 major Nifty stocks. To change this list:
1. Open `src/refresh_job.py` in Notepad/TextEdit.
2. Find the `DEFAULT_WATCHLIST` list near the top.
3. Add or remove symbols in the format `"SYMBOL-EQ"` (e.g. `"WIPRO-EQ"`).
   Use the same symbol as shown on the NSE website.
4. Save, restart the app, and click "Refresh data now" again.

For market breadth to be truly meaningful (not just 20 stocks), consider
expanding this list toward the full Nifty 500 over time — the app will
handle it the same way, it'll just take a bit longer to refresh.

## Troubleshooting

- **"Angel One login failed"**: double-check all 4 values in `.env` are
  correct and have no extra spaces. TOTP secrets are case-sensitive.
- **App shows no data**: click "Refresh data now" in the sidebar first —
  the app doesn't fetch anything until you ask it to.
- **"command not found: streamlit"**: your Python installation may not have
  added itself to your system PATH. Reinstall Python and make sure to tick
  "Add Python to PATH" (Windows) during setup.
- **TradingView charts not loading**: they need an internet connection and
  aren't blocked by any firewall/ad-blocker — try disabling ad-blockers for
  this page if charts stay blank.

## Important disclaimer

This tool shows momentum, sector rotation, and breadth indicators to help
you understand current market conditions. These are lagging indicators —
they describe what has already happened, not guaranteed predictions of
what will happen next. This is not financial advice. Always do your own
research and consider consulting a registered financial advisor before
trading.
