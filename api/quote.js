const YAHOO_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36";
const SYMBOL_RE = /^[A-Z0-9.^%=-]{1,32}$/i;

function parseSymbols(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter((item) => SYMBOL_RE.test(item))
    .slice(0, 24);
}

function simplifyChart(payload, requested) {
  const result = payload && payload.chart && payload.chart.result && payload.chart.result[0];
  if (!result || !result.meta) {
    return { symbol: requested, error: "No data" };
  }
  const meta = result.meta;
  const closes =
    (result.indicators &&
      result.indicators.quote &&
      result.indicators.quote[0] &&
      result.indicators.quote[0].close) ||
    [];
  const previous = Number(meta.chartPreviousClose);
  const price = Number(meta.regularMarketPrice);
  const changePercent =
    meta.regularMarketChangePercent != null
      ? Number(meta.regularMarketChangePercent)
      : previous
        ? ((price - previous) / previous) * 100
        : 0;

  return {
    yahoo: meta.symbol || requested,
    name: meta.shortName || meta.longName || meta.symbol || requested,
    currency: meta.currency || "USD",
    price: Number.isFinite(price) ? price : null,
    previousClose: Number.isFinite(previous) ? previous : null,
    changePercent: Number.isFinite(changePercent) ? changePercent : null,
    dayHigh: meta.regularMarketDayHigh != null ? Number(meta.regularMarketDayHigh) : null,
    dayLow: meta.regularMarketDayLow != null ? Number(meta.regularMarketDayLow) : null,
    volume: meta.regularMarketVolume != null ? Number(meta.regularMarketVolume) : null,
    closes: closes.filter((value) => value != null && Number.isFinite(Number(value))).map(Number),
  };
}

async function fetchYahoo(symbol) {
  const url =
    "https://query1.finance.yahoo.com/v8/finance/chart/" +
    encodeURIComponent(symbol) +
    "?range=1mo&interval=1d";
  const response = await fetch(url, {
    headers: { "User-Agent": YAHOO_UA, Accept: "application/json" },
  });
  if (!response.ok) {
    return { symbol, error: "Quote unavailable" };
  }
  const payload = await response.json();
  return simplifyChart(payload, symbol);
}

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const symbols = parseSymbols(req.query.symbols);
  if (!symbols.length) {
    res.status(400).json({ error: "Missing symbols" });
    return;
  }

  const quotes = [];
  for (const symbol of symbols) {
    try {
      quotes.push(await fetchYahoo(symbol));
    } catch (error) {
      quotes.push({ symbol, error: "Quote unavailable" });
    }
  }

  res.setHeader("Cache-Control", "s-maxage=30, stale-while-revalidate=120");
  res.status(200).json({ quotes });
};
