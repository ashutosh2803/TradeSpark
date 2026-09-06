"""Local static server plus Yahoo Finance quote proxy for the watchlist."""

from __future__ import annotations

import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlparse
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


def last_number(values):
    if not isinstance(values, list):
        return None
    for value in reversed(values):
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def simplify_chart(payload: dict, requested: str) -> dict:
    try:
        result = payload["chart"]["result"][0]
        meta = result["meta"]
    except (KeyError, IndexError, TypeError):
        return {"symbol": requested, "error": "No data"}

    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    closes = quote.get("close") or []
    previous = meta.get("chartPreviousClose")
    price = meta.get("regularMarketPrice")
    change_pct = meta.get("regularMarketChangePercent")
    if change_pct is None and previous and price:
        change_pct = ((price - previous) / previous) * 100
    change = meta.get("fulldayChange")
    if change is None and previous is not None and price is not None:
        change = price - previous

    return {
        "yahoo": meta.get("symbol") or requested,
        "name": meta.get("shortName") or meta.get("longName") or requested,
        "longName": meta.get("longName") or meta.get("shortName") or requested,
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "",
        "currency": meta.get("currency") or "USD",
        "price": price,
        "previousClose": previous,
        "open": last_number(quote.get("open")),
        "change": change,
        "changePercent": change_pct,
        "dayHigh": meta.get("regularMarketDayHigh"),
        "dayLow": meta.get("regularMarketDayLow"),
        "week52High": meta.get("fiftyTwoWeekHigh"),
        "week52Low": meta.get("fiftyTwoWeekLow"),
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
        if parsed.path.rstrip("/") == "/api/search":
            self.handle_search(parsed)
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

    def handle_search(self, parsed) -> None:
        query = parse_qs(parsed.query)
        raw = unquote(query.get("q", [""])[0])
        cleaned = re.sub(r"[^\w .&+-]", " ", raw).strip()[:40]
        if len(cleaned) < 2:
            self.send_json({"quotes": []}, 200)
            return
        url = (
            "https://query1.finance.yahoo.com/v1/finance/search?q="
            f"{quote(cleaned)}&quotesCount=10&newsCount=0&listsCount=0"
        )
        request = Request(url, headers={"User-Agent": YAHOO_UA, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
            self.send_json({"error": "Search unavailable"}, 502)
            return
        quotes = []
        for item in payload.get("quotes") or []:
            kind = str(item.get("quoteType") or item.get("typeDisp") or "").upper()
            if kind in {"OPTION", "FUTURE", "CURRENCY"}:
                continue
            symbol = str(item.get("symbol") or "").strip()
            if not symbol:
                continue
            quotes.append(
                {
                    "yahoo": symbol,
                    "name": item.get("shortname") or item.get("longname") or symbol,
                    "longName": item.get("longname") or "",
                    "exchange": item.get("exchDisp") or item.get("exchange") or "",
                    "type": item.get("typeDisp") or item.get("quoteType") or "",
                }
            )
            if len(quotes) >= 8:
                break
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
