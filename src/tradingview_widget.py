"""
Generates TradingView's free embeddable widgets (chart + watchlist).
These don't need any API key - TradingView provides them for free for
embedding on any page.
"""


def advanced_chart_html(symbol: str = "NSE:NIFTY", height: int = 520) -> str:
    """A full interactive TradingView chart for one symbol.
    symbol format: 'NSE:RELIANCE', 'NSE:NIFTY', 'NSE:BANKNIFTY', etc."""
    return f"""
    <div class="tradingview-widget-container" style="height:{height}px;">
      <div id="tv_chart" style="height:100%;"></div>
      <script src="https://s3.tradingview.com/tv.js"></script>
      <script>
        new TradingView.widget({{
          "autosize": true,
          "symbol": "{symbol}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "light",
          "style": "1",
          "locale": "in",
          "toolbar_bg": "#f1f3f6",
          "enable_publishing": false,
          "hide_top_toolbar": false,
          "allow_symbol_change": true,
          "container_id": "tv_chart"
        }});
      </script>
    </div>
    """


def watchlist_html(symbols: list, height: int = 500) -> str:
    """A scrolling watchlist widget showing live prices for a list of symbols.
    symbols should be like ['NSE:RELIANCE', 'NSE:TCS', 'NSE:HDFCBANK']."""
    symbol_list = ",".join([f'{{"s":"{s}"}}' for s in symbols])
    return f"""
    <div class="tradingview-widget-container" style="height:{height}px;">
      <div class="tradingview-widget-container__widget"></div>
      <script src="https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js" async>
      {{
        "width": "100%",
        "height": {height},
        "symbolsGroups": [
          {{
            "name": "Watchlist",
            "originalName": "Watchlist",
            "symbols": [{symbol_list}]
          }}
        ],
        "showSymbolLogo": true,
        "colorTheme": "light",
        "locale": "in"
      }}
      </script>
    </div>
    """


def ticker_tape_html(symbols: list) -> str:
    """A slim scrolling ticker strip, good for the top of the dashboard."""
    symbol_list = ",".join([f'{{"proName":"{s}","title":"{s.split(":")[-1]}"}}' for s in symbols])
    return f"""
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {{
        "symbols": [{symbol_list}],
        "showSymbolLogo": true,
        "colorTheme": "light",
        "isTransparent": false,
        "displayMode": "adaptive",
        "locale": "in"
      }}
      </script>
    </div>
    """
