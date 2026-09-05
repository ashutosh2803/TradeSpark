# Trade Spark

Simple tools, smarter trading, brighter decisions.

A live market dashboard for Indian indices and global markets. Charts, heatmap, movers, and technicals come from TradingView widgets. The app is a static Progressive Web App — install it from the browser and use it like a standalone window.

![Trade Spark dashboard](screenshot.png)

## Features

- Dark theme by default, with a light/dark toggle
- Live ticker for Sensex, Nifty 50, Bank Nifty, Bitcoin, DXY, and S&P 500
- Mini overviews for Sensex, Bankex, BTC, and FTSE 100
- Advanced Sensex chart with details, hotlist, and SMA
- Market news, BSE hotlists, and Sensex sector heatmap
- Technical ratings for Sensex, Nifty, Bank Nifty, and Nifty MidCap 100
- Custom watchlist with Yahoo Finance live search, quotes, and 1-month sparkline price action, saved in this browser
- Installable PWA with offline shell (market widgets still need a network connection)

## Run locally

Open the files over HTTP. A service worker cannot register from a `file://` URL. Use `serve.py` so the watchlist can load Yahoo Finance quotes through `/api/quote`.

```bash
python serve.py
```

Then visit [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

## Install as an app

Serve the site over HTTP or HTTPS (not `file://`). In Chrome, install from the address bar or **Customize and control Google Chrome → Cast, save, and share → Install page as app**. On iOS Safari, use **Share → Add to Home Screen**.

## Deploy

The site is static plus one serverless quote route. Vercel will serve `api/quote.js` automatically. Keep these files at the site root:

- `index.html`
- `manifest.json`
- `sw.js`
- `api/quote.js`
- `api/search.js`
- `favicon.svg` / `favicon.ico`
- `icons/`
