const YAHOO_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36";

function sanitizeQuery(value) {
  return String(value || "")
    .replace(/[^\w .&+-]/g, " ")
    .trim()
    .slice(0, 40);
}

function simplifyQuote(quote) {
  const type = String(quote.quoteType || quote.typeDisp || "").toUpperCase();
  if (["OPTION", "FUTURE", "CURRENCY"].includes(type)) {
    return null;
  }
  const symbol = String(quote.symbol || "").trim();
  if (!symbol) {
    return null;
  }
  return {
    yahoo: symbol,
    name: quote.shortname || quote.longname || symbol,
    longName: quote.longname || "",
    exchange: quote.exchDisp || quote.exchange || "",
    type: quote.typeDisp || quote.quoteType || "",
  };
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

  const query = sanitizeQuery(req.query.q);
  if (query.length < 2) {
    res.status(200).json({ quotes: [] });
    return;
  }

  const url =
    "https://query1.finance.yahoo.com/v1/finance/search?q=" +
    encodeURIComponent(query) +
    "&quotesCount=10&newsCount=0&listsCount=0";

  try {
    const response = await fetch(url, {
      headers: { "User-Agent": YAHOO_UA, Accept: "application/json" },
    });
    if (!response.ok) {
      res.status(502).json({ error: "Search unavailable" });
      return;
    }
    const payload = await response.json();
    const quotes = (payload.quotes || []).map(simplifyQuote).filter(Boolean).slice(0, 8);
    res.setHeader("Cache-Control", "s-maxage=20, stale-while-revalidate=60");
    res.status(200).json({ quotes });
  } catch (error) {
    res.status(502).json({ error: "Search unavailable" });
  }
};
