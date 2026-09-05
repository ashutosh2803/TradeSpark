"""Local static server plus Yahoo Finance quote proxy for the watchlist."""

from __future__ import annotations

import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

YAHOO_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
SYMBOL_RE = re.compile(r"^[A-Z0-9.^%=-]{1,32}$", re.I)
HOST = "127.0.0.1"
PORT = 8765


def parse_symbols(value: str) -> list[str]:
    symbols = []
    for item in (value or "").split(","):
        symbol = item.strip()
        if SYMBOL_RE.match(symbol):
            symbols.append(symbol)
        if len(symbols) >= 24:
            break
    return symbols


def simplify_chart(payload: dict, requested: str) -> dict:
    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
    except (KeyError, IndexError, TypeError):
        return {"symbol": requested, "error": "No data"}

    closes = (
        (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close"))
        or []
    )
    previous = meta.get("chartPreviousClose")
    price = meta.get("regularMarketPrice")
    change = meta.get("regularMarketChangePercent")
    if change is None and previous and price:
        change = ((price - previous) / previous) * 100

    return {
        "yahoo": meta.get("symbol") or requested,
        "name": meta.get("shortName") or meta.get("longName") or requested,
        "currency": meta.get("currency") or "USD",
        "price": price,
        "previousClose": previous,
        "changePercent": change,
        "dayHigh": meta.get("regularMarketDayHigh"),
        "dayLow": meta.get("regularMarketDayLow"),
        "volume": meta.get("regularMarketVolume"),
        "closes": [float(value) for value in closes if value is not None],
    }


def fetch_yahoo(symbol: str) -> dict:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?range=1mo&interval=1d"
    )
    request = Request(url, headers={"User-Agent": YAHOO_UA, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return simplify_chart(payload, symbol)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return {"symbol": symbol, "error": "Quote unavailable"}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/api/quote":
            self.handle_quote(parsed)
            return
        super().do_GET()

    def handle_quote(self, parsed) -> None:
        query = parse_qs(parsed.query)
        symbols = parse_symbols(unquote(query.get("symbols", [""])[0]))
        if not symbols:
            self.send_json({"error": "Missing symbols"}, 400)
            return
        quotes = [fetch_yahoo(symbol) for symbol in symbols]
        self.send_json({"quotes": quotes}, 200)

    def send_json(self, payload: dict, status: int) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Trade Spark at http://{HOST}:{PORT}/")
    server.serve_forever()
