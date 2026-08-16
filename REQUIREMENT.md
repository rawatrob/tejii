# Tejii — Requirement / Build Prompt

Paste everything below into any AI coding tool (Claude Code, Cursor, ChatGPT).
It is self-contained — no other context needed.

---

## PROJECT: Tejii (tejii.in) — Hindi-first stock market portal for Indian beginners

### Goal

Build a Hindi-language stock market portal for Indian beginners who want to invest
but are afraid of losing money.

**Core promise:** in 30 seconds, a complete beginner should understand what happened
in the market today and why.

### Audience

Housewives, students, first-time investors, early intermediates. They have little
time, limited English, and low confidence. They are on a phone, not a laptop. They
are afraid of losing money and don't know how much they could lose.

### The three questions the site must answer

Every mainstream Indian finance site answers "what should I buy." None of them
answer these, and these are what actually stop beginners:

1. How much can I lose?
2. Am I making a mistake right now?
3. What do I do when the market falls?

---

## PAGES — exactly 5, no more

A beginner shown more than 5 options gets confused and leaves.

### 1. Ghar (Home) — the 30-second page

- Nifty and Sensex closing value + % change
- Sector table: which sectors rose/fell today, sorted by % change
- **"Aaj aisa kyun hua"** — 3 lines of plain-Hindi explanation, written manually each day
- 5 news headlines, each linking to its source
- Button: "Naye ho? Yahan se shuru karo" → Seekhein

This page changes daily. It is the reason people return.

### 2. Seekhein (Learn) — 12 articles in 3 levels

Present as a path, not a flat list, so the reader knows where they are.

**Level 1 — Before you invest money**
1. Share market kya hai? (in 5 minutes)
2. 4 things to do BEFORE investing (emergency fund, clear loans, insurance)
3. How much money should you invest? (an amount whose loss won't cost you sleep)
4. What is risk — profit always comes with the possibility of loss
5. What is a demat account and how to open one

**Level 2 — Understand the market**
6. What are Nifty and Sensex?
7. Why do share prices move up and down?
8. What are sectors — what IT, Bank, Pharma mean
9. Is a company good or not — 4 things to check

**Level 3 — Now start**
10. What is an index fund, and why it suits beginners best
11. What is a SIP, how to start with ₹500
12. **The market is falling — what do I do now?**

Articles #2 and #12 matter most. #2 prevents mistakes. #12 will get the most
traffic, on the days markets crash.

Each article: 3–4 minute read, simple Hindi, short paragraphs.

### 3. Practice (Paper Trading) — virtual portfolio

- ₹1,00,000 in virtual money
- Buy and sell equity only
- **Orders execute at the NEXT trading day's closing price** (EOD, not real-time).
  This is deliberate: real-time paper trading teaches beginners to day-trade, which
  is how they lose money. EOD teaches investing.
- Show holdings and profit/loss
- **Key feature:** always show the comparison —
  *"You made ₹4,200. If you had put the same money in a Nifty index fund, you'd
  have ₹6,800."*
  Most users will underperform the index. Learning that with fake money is the
  single most valuable thing this site can teach.
- Needs login (Firebase Auth) and per-user storage (Firestore)
- **NO** options, F&O, short selling, margin, or leverage — ever

### 4. Scanner — stock filter for intermediate users

- Filters over precomputed EOD indicators: RSI(14), SMA 20/50/200, volume vs
  20-day average, distance from 52-week high/low, daily turnover
- Default minimum turnover ₹1 crore — below that a stock is too illiquid to trade
- Notice at top: *"Ye thoda advance hai. Pehle Seekhein padh lo."*

### 5. Khabrein (News) — aggregated

- Headline + link to the original source + **one line of plain-Hindi "what this means"**
- The headline is available everywhere. The meaning is not. That is the value.
- Never copy full article text or images.

---

## DATA SOURCES — all free, all verified working

### Prices — EOD bhavcopy, ~2,700 stocks, ~195 KB/day

```
https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
```
- Requires a browser `User-Agent` header, else NSE rejects it
- HTTP 403/404 means a market holiday — skip that date, not an error
- Useful columns: `TckrSymb`, `SctySrs` (keep `EQ` and `BE` only), `FinInstrmTp`
  (keep `STK`), `OpnPric`, `HghPric`, `LwPric`, `ClsPric`, `TtlTradgVol`, `TtlTrfVal`

### Sector indices — daily, ~165 rows

```
https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv
```
- **Note the different date format** — `DDMMYYYY` here, `YYYYMMDD` for bhavcopy
- Columns: `Index Name`, `Closing Index Value`, `Points Change`, `Change(%)`
- Contains Nifty IT, Nifty Bank, Nifty Pharma, Nifty Auto, Nifty FMCG,
  Nifty Metal, Nifty Realty, and the broad indices
- This single file answers "which sector is up and which is down" — it is data,
  not news, and needs no scraping

### News — RSS

```
https://www.livemint.com/rss/markets                      (~35 items)
https://www.business-standard.com/rss/markets-106.rss     (~35 items)
https://www.moneycontrol.com/rss/business.xml             (~15 items)
```

---

## HARD CONSTRAINTS

### Content rules — these define the brand

1. Everything in simple Hindi. Explain every English term on first use —
   write "upar-neeche hona (volatility)", never bare "volatility".
2. **Never promise returns.** Never write that a stock will rise.
3. **Show the downside before the upside.** Every other site does the opposite.
   This is what builds trust.
4. Short paragraphs — 2 to 3 lines. This is read on a phone.

### Legal — India / SEBI

- This is a **tool and education** site, **not an advisory**. No stock
  recommendations, no target prices, no tips, no buy/sell calls. Those require
  SEBI Research Analyst (INH) registration, which this project does not have.
- Name scans by their **criteria** ("RSI below 30"), never by **outcome**
  ("today's top picks"). The second one is legally a recommendation.
- Disclaimer on every page.
- News: headline + your own summary + link to source. Never reproduce full text.

### Technical

- **Mobile-first.** Single column, large text, large tap targets. No wide tables.
- **Prefer the simplest thing that works.** No framework unless a page genuinely
  needs one. No database for price data — one daily JSON file is enough. No server
  at all for pages 1, 2, 4, and 5.
- Only paper trading needs auth and a database (Firebase Auth + Firestore).
- The daily update job runs after 18:30 IST on weekdays, when NSE publishes.

---

## EXPLICITLY NOT BUILDING

Do not add these, even if they seem useful:

- Real-time or intraday prices
- Options, F&O, margin, short selling
- Stock recommendations, tips, target prices
- A mobile app (the website works on phones)
- Paid subscriptions
- Comments or a forum

---

## BUILD ORDER

| # | What | Effort | Daily work after |
|---|------|--------|------------------|
| 1 | Home — sector up/down | 1 weekend | automatic |
| 2 | Daily 3-line "kyun hua" | — | 10 min/day |
| 3 | Seekhein — first 5 articles | 2 weekends | none |
| 4 | News via RSS | 1 day | automatic |
| 5 | Scanner | 1 hour | automatic |
| 6 | Remaining 7 articles | 2 weekends | none |
| 7 | Paper trading | 3–4 weekends | automatic |

Paper trading is by far the largest piece — build it **last**, after the site is
live and people are actually visiting.

**Build step 1 only. Ask before starting the next step.**
