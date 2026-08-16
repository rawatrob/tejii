# tejii

Hindi-first stock market portal for Indian beginners.
No server, no database, no dependencies — just Python's standard library.

A GitHub Action runs every weekday evening: it downloads NSE's official files,
computes everything, and commits two JSON files. GitHub Pages serves the HTML,
which reads that JSON in the browser. Hosting cost: zero.

## Pages

| File | What | Needs |
|---|---|---|
| `index.html` | Homepage — the 30-second daily market view | `data/home.json` |
| `seekhein.html` | 12 articles in 3 levels, with a reader | `articles.json` |
| `khabrein.html` | News, filterable by source | `data/news.json` |
| `watchlist.html` | Pick stocks, follow them daily (localStorage) | `data/scan.json` |
| `scanner.html` | Full stock filter for advanced users | `data/scan.json` |
| `practice.html` | Loss calculator now; paper trading later | — |

`style.css` and `app.js` are shared by all six. `app.js` renders the header, mobile
nav and footer from one place — set `<body data-page="seekhein">` and the right nav
item highlights itself. Change the nav once, it changes everywhere.

## Editing content without touching code

| Want to change | Edit |
|---|---|
| Articles (add, reword, reorder) | `articles.json` |
| Quiz, concept of the day, word, tip | `content.json` |
| Today's "why it happened" + tomorrow's events | `data/why.json` |
| News sources | `FEEDS` in `build.py` |

## News freshness

News is sorted newest-first and the homepage box only takes items from the last
48 hours, with a per-source cap so one feed cannot fill it.

RSS feeds go stale silently — Moneycontrol's had been frozen for ~2.3 years and was
putting 2024 headlines on the homepage before anyone noticed. Check before trusting
a source, and re-check occasionally:

```bash
python3 build.py --feeds
```

It prints each feed's newest item age and flags anything over 72 hours as stale.

## Daily pipeline

```
scan.py     NSE bhavcopy  -> raw/*.zip -> data/scan.json   (~2,700 stocks + indicators)
build.py    scan.json + NSE indices + RSS -> data/home.json (homepage)
```

`build.py` prints a status line naming any source that failed — nothing crashes
the build, the page just hides that box.

**`scan.py` needs `--back` large enough.** Indicators need at least 15 sessions, and
52-week highs need ~250. Running it bare pulls only ~8 sessions, which would drop
every stock — so it now refuses to write an empty or drastically smaller
`scan.json` rather than silently blanking a good one. The daily job passes
`--back 400`.

## What is automatic vs manual

**Automatic** — indices, sector performance, advance/decline, heatmap, top movers,
India VIX, FII/DII, USD/INR, news headlines, scanner counts, the "30 सेकंड का सार"
bullets, the daily quiz/concept/word (rotated from `content.json` by date).

**Manual — one thing only:** `data/why.json`, the "आज ऐसा क्यों हुआ" bullets.
No price feed can explain *why* the market moved. This is the 10 minutes a day
that makes the site worth visiting.

```json
{
  "date": "2026-08-14",
  "points": ["...", "...", "..."]
}
```

`date` must match `home.json`'s date, or the card falls back to a neutral message —
stale reasoning is worse than none.

To extend the quiz, concepts, words, or tips, just add entries to `content.json`.
They rotate by date automatically; nothing else to change.

## Setup (once)

```bash
git init && git add -A && git commit -m "init"
gh repo create tejii --public --source=. --push
python3 scan.py --back 400 && python3 build.py
git add raw data && git commit -m "backfill" && git push
```

Then **Settings → Pages → Source: main branch**, and point tejii.in at it with a
`CNAME` file plus a DNS ALIAS/CNAME to `<user>.github.io`.

## Local

```bash
python3 scan.py --selfcheck && python3 build.py --selfcheck
python3 scan.py && python3 build.py
python3 -m http.server 8000        # http://localhost:8000
```

## The data

Both JSON files are static and served with permissive CORS, so they double as a
free public API:

```
https://tejii.in/data/home.json     today's market summary
https://tejii.in/data/scan.json     every stock with indicators
```

`raw/` keeps the original bhavcopy zips (~195 KB/day) as the archive — everything
is rebuildable from them, so nothing is lost if the JSON is deleted.

## Deliberate omissions

- **Sensex** — BSE blocks its API. All indices come from NSE.
- **Crude oil** — no free source without a key.
- **Real-time prices** — needs an NSE redistribution licence. Everything here is
  end-of-day, and the page says so.
- **User counts, testimonials, community activity** — these were in the original
  mockup and are not built. Publishing invented numbers or reviews would be
  deceptive; add them when they are real.
- **AI Market Explainer** — shown as "जल्द आ रहा है"; needs an LLM API key.

## Content rules

1. Simple Hindi. Explain every English term on first use.
2. Never promise returns. Never say a stock will rise.
3. Show the downside before the upside.
4. Short paragraphs — this is read on a phone.

## Before charging money

- NSE bhavcopy is public, but commercial redistribution wants an agreement with
  NSE Data & Analytics (marketdata@nse.co.in).
- Name scans by their **filters**, never by an outcome. "RSI below 30" is a tool;
  "Best stocks to buy today" is a recommendation and needs SEBI Research Analyst
  (INH) registration.
- News: headline + own summary + source link only. Never reproduce full articles.
