#!/usr/bin/env python3
"""Build data/home.json for the Tejii homepage. Stdlib only, no pip install.

Everything here comes from free public sources and needs no key:
  indices + sectors   NSE archive CSV        (reliable from any IP)
  breadth / movers    NSE bhavcopy           (already downloaded by scan.py)
  VIX                 NSE archive CSV        (API used only as a bonus)
  FII / DII           NSE API                (optional - hidden if blocked)
  USD/INR             frankfurter.app        (free, no key)
  news                RSS                    (headline + link only)

Run after scan.py:
    python3 scan.py && python3 build.py
"""
import csv, io, json, os, re, sys, urllib.error, urllib.request, zipfile
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)   # so `python3 -I build.py` can still find scan.py
import scan  # noqa: E402  - reuse UA/RAW/SERIES and its downloader

OUT = os.path.join(HERE, "data")
IST = timezone(timedelta(hours=5, minutes=30))
UA = {"User-Agent": scan.UA}

IDX_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{:%d%m%Y}.csv"
IDX_LIST_URL = "https://nsearchives.nseindia.com/content/indices/ind_{}list.csv"
FII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
FX_URL = "https://api.frankfurter.app/latest?from=USD&to=INR"

# Checked for freshness before being listed here. Moneycontrol was dropped in Aug 2026:
# every one of its RSS feeds had been frozen for ~2.3 years and was filling the
# homepage with 2024 headlines. Run `build.py --feeds` before adding any source.
FEEDS = [
    ("LiveMint", "https://www.livemint.com/rss/markets"),
    ("LiveMint", "https://www.livemint.com/rss/money"),
    ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
    ("Business Standard", "https://www.business-standard.com/rss/finance-103.rss"),
    ("BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
]
FRESH_HOURS = 48   # older than this is not "आज की खबर"

# Sectors shown on the homepage, in the order NSE names them -> short label
SECTORS = [
    ("Nifty IT", "IT"), ("Nifty Bank", "BANK"), ("Nifty Pharma", "PHARMA"),
    ("Nifty FMCG", "FMCG"), ("Nifty Auto", "AUTO"), ("Nifty Realty", "REALTY"),
    ("Nifty Metal", "METAL"), ("Nifty Energy", "ENERGY"),
    ("Nifty Media", "MEDIA"), ("Nifty PSU Bank", "PSU BANK"),
]
HEADLINE = [("Nifty 50", "NIFTY 50"), ("Nifty Bank", "BANK NIFTY"), ("Nifty Next 50", "NIFTY NEXT 50")]


def get(url, timeout=25):
    """Fetch bytes, or None. Nothing here is worth crashing the build over."""
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
    except Exception as e:
        print(f"  ! {url.split('/')[-1][:40]}: {e}", file=sys.stderr)
        return None


def num(s):
    try:
        return float(str(s).strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


# ---------- indices ----------

def indices(d):
    """{index name: {close, chg, pct}} from the daily archive CSV."""
    raw = get(IDX_URL.format(d))
    if not raw:
        return {}
    out = {}
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))):
        name = (r.get("Index Name") or "").strip()
        close, pct = num(r.get("Closing Index Value")), num(r.get("Change(%)"))
        if name and close is not None:
            out[name.lower()] = {"close": close, "chg": num(r.get("Points Change")), "pct": pct}
    return out


def pick(idx, names):
    rows = []
    for full, label in names:
        v = idx.get(full.lower())
        if v:
            rows.append({"name": label, **v})
    return rows


# ---------- bhavcopy-derived ----------

def latest_zip():
    """Newest bhavcopy zip already on disk (scan.py put it there)."""
    zips = sorted(f for f in os.listdir(scan.RAW) if f.endswith(".zip"))
    if not zips:
        sys.exit("no bhavcopy in raw/ - run scan.py first")
    return os.path.join(scan.RAW, zips[-1]), datetime.strptime(zips[-1][:8], "%Y%m%d").date()


def day_rows(path):
    """Full rows incl. previous close, which read_day() drops."""
    with zipfile.ZipFile(path) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        if r["SctySrs"] not in scan.SERIES or r["FinInstrmTp"] != "STK":
            continue
        c, p, v = num(r["ClsPric"]), num(r["PrvsClsgPric"]), num(r["TtlTradgVol"])
        if not (c and p and v is not None):
            continue
        out.append({"sym": r["TckrSymb"], "close": c, "prev": p, "vol": v,
                    "val": num(r["TtlTrfVal"]) or 0, "pct": round((c - p) / p * 100, 2)})
    return out


def breadth(rows):
    up = sum(1 for r in rows if r["close"] > r["prev"])
    dn = sum(1 for r in rows if r["close"] < r["prev"])
    return {"advance": up, "decline": dn, "unchanged": len(rows) - up - dn}


def movers(rows, universe, n=5):
    # Nifty 500 only. A turnover filter does NOT work here: a small-cap spiking 47%
    # generates huge turnover *because* of the spike, so it survives any rupee bar.
    # Showing beginners a list of unknown stocks up 40% teaches exactly the gambling
    # this site exists to steer them away from.
    liquid = [r for r in rows if r["sym"] in universe] if universe else \
             [r for r in rows if r["val"] >= 25e7]
    by = lambda k, rev: [
        {"sym": r["sym"], "close": r["close"], "pct": r["pct"]}
        for r in sorted(liquid, key=k, reverse=rev)[:n]
    ]
    return {
        "gainers": by(lambda r: r["pct"], True),
        "losers": by(lambda r: r["pct"], False),
        "active": by(lambda r: r["val"], True),
        "volume": by(lambda r: r["vol"], True),
    }


def constituents(slug):
    """Symbols of an NSE index, cached on disk. '' if NSE is unreachable."""
    path = os.path.join(OUT, f"{slug}.csv")
    if not os.path.exists(path):
        raw = get(IDX_LIST_URL.format(slug))
        if raw and raw.lstrip().lower().startswith(b"company"):
            with open(path, "wb") as f:
                f.write(raw)
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {r["Symbol"].strip() for r in csv.DictReader(f) if r.get("Symbol")}


def heatmap(rows, universe):
    """Nifty 50 only - 500 tiles is unreadable as a grid."""
    m = {r["sym"]: r for r in rows if r["sym"] in universe}
    return [{"sym": s, "pct": m[s]["pct"]} for s in sorted(m, key=lambda s: -m[s]["pct"])]


def fresh_extremes():
    """New 52-week highs/lows, from what scan.py already computed."""
    p = os.path.join(OUT, "scan.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        st = json.load(f)["stocks"]
    return {
        "high": sum(1 for r in st if (r.get("from_hi") or -99) >= -0.1),
        "low": sum(1 for r in st if (r.get("from_lo") or 99) <= 0.1),
        "window_days": max((r.get("days") or 0) for r in st) if st else 0,
        "scans": {
            "rsi_low": sum(1 for r in st if (r.get("rsi14") or 99) < 30),
            "rsi_high": sum(1 for r in st if (r.get("rsi14") or 0) > 70),
            "vol_burst": sum(1 for r in st if (r.get("vol_x") or 0) >= 2),
            "near_high": sum(1 for r in st if (r.get("from_hi") or -99) >= -2),
            "near_low": sum(1 for r in st if (r.get("from_lo") or 99) <= 5),
        },
    }


# ---------- outside NSE ----------

def fii_dii():
    raw = get(FII_URL, timeout=15)
    if not raw:
        return None
    try:
        rows = json.loads(raw)
    except Exception:
        return None
    out = {}
    for r in rows:
        key = "fii" if "FII" in r.get("category", "") else "dii"
        out[key] = {"net": num(r.get("netValue")), "date": r.get("date")}
    return out or None


def usdinr():
    raw = get(FX_URL, timeout=15)
    if not raw:
        return None
    try:
        return {"rate": json.loads(raw)["rates"]["INR"]}
    except Exception:
        return None


def epoch(pubdate):
    """RSS pubDate -> unix seconds, so the page can show '2 मिनट पहले'."""
    if not pubdate:
        return None
    try:
        return int(parsedate_to_datetime(pubdate.strip()).timestamp())
    except (TypeError, ValueError):
        return None


def calendar(day_events):
    """Fixed market timings every day, plus whatever was added by hand today."""
    fixed = [
        {"at": "09:15", "what": "बाजार खुलेगा", "kind": "open"},
        {"at": "15:30", "what": "बाजार बंद होगा", "kind": "close"},
        {"at": "शाम", "what": "FII / DII के आंकड़े आएंगे", "kind": "data"},
    ]
    return sorted(fixed + list(day_events or []), key=lambda e: e["at"])


def news(now):
    """Every feed's items, de-duped and sorted newest first.

    Sorting by publish time is the whole point - a round-robin across feeds put a
    two-year-old item third on the homepage. Undated items sort last rather than
    being trusted as fresh.
    """
    items, seen = [], set()
    for src, url in FEEDS:
        raw = get(url, timeout=20)
        if not raw:
            continue
        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            continue
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            key = re.sub(r"\W+", "", t.lower())[:60]
            if not t or not link or key in seen:
                continue
            seen.add(key)
            items.append({"title": t, "link": link, "src": src,
                          "ts": epoch(it.findtext("pubDate"))})
    items.sort(key=lambda i: i["ts"] or 0, reverse=True)
    return items


def top_news(items, now, limit=8, cap=4):
    """Newest first for the homepage, but no single source may take the whole box."""
    fresh = [i for i in items if i["ts"] and now - i["ts"] <= FRESH_HOURS * 3600]
    pool = fresh if len(fresh) >= limit else items      # never leave the box empty
    out, used = [], {}
    for i in pool:
        if used.get(i["src"], 0) < cap:
            out.append(i)
            used[i["src"]] = used.get(i["src"], 0) + 1
            if len(out) == limit:
                return out
    for i in pool:                                      # cap too tight - top up by time
        if i not in out:
            out.append(i)
            if len(out) == limit:
                break
    return out


def feedcheck():
    """`build.py --feeds` — how stale is each source right now?"""
    now = datetime.now(timezone.utc).timestamp()
    for src, url in FEEDS:
        raw = get(url, timeout=20)
        ages = []
        if raw:
            try:
                for it in ElementTree.fromstring(raw).iter("item"):
                    e = epoch(it.findtext("pubDate"))
                    if e:
                        ages.append((now - e) / 3600)
            except ElementTree.ParseError:
                pass
        if ages:
            flag = "  <-- STALE, drop it" if min(ages) > 72 else ""
            print(f"  {src:18} {len(ages):3d} items | newest {min(ages):6.1f}h{flag}")
        else:
            print(f"  {src:18} NO USABLE DATES  {url}")


# ---------- derived, explainable numbers ----------

def health(br, idx_rows, vix):
    """0-100 blend of breadth, index direction and calm. Deliberately simple and
    explainable - the page shows the inputs so nobody has to trust a black box.
    ponytail: fixed weights; only tune if the number ever reads obviously wrong."""
    tot = br["advance"] + br["decline"]
    b = (br["advance"] / tot * 100) if tot else 50
    d = max(0, min(100, 50 + (idx_rows[0]["pct"] if idx_rows else 0) * 15))
    calm = max(0, min(100, (25 - (vix or 15)) / 20 * 100))
    return round(0.5 * b + 0.3 * d + 0.2 * calm)


def mood(score):
    return "POSITIVE" if score >= 60 else "NEGATIVE" if score <= 40 else "NEUTRAL"


def fear(vix):
    if vix is None:
        return None
    return "LOW" if vix < 14 else "MEDIUM" if vix < 20 else "HIGH"


def summary(head, sect, br, fd, vix):
    """The '30 second ka saar' bullets - built from data, not written by hand."""
    out = []
    if head:
        n = head[0]
        move = "बढ़त" if n["pct"] > 0 else "गिरावट" if n["pct"] < 0 else "सपाट"
        size = "मजबूत" if abs(n["pct"]) >= 1 else "हल्की" if abs(n["pct"]) >= 0.3 else "मामूली"
        out.append(f"Nifty {n['close']:,.0f} पर बंद — {size} {move} ({n['pct']:+.2f}%)")
    if sect:
        best, worst = sect[0], sect[-1]
        if best["pct"] > 0:
            out.append(f"{best['name']} सबसे मजबूत ({best['pct']:+.2f}%), {worst['name']} सबसे कमजोर ({worst['pct']:+.2f}%)")
        else:
            out.append(f"सभी सेक्टर दबाव में — {worst['name']} सबसे ज्यादा गिरा ({worst['pct']:+.2f}%)")
    tot = br["advance"] + br["decline"]
    if tot:
        side = "ज्यादा शेयर चढ़े" if br["advance"] > br["decline"] else "ज्यादा शेयर गिरे"
        out.append(f"{br['advance']:,} शेयर चढ़े, {br['decline']:,} गिरे — {side}")
    if fd and fd.get("fii", {}).get("net") is not None:
        v = fd["fii"]["net"]
        out.append(f"FII ने ₹{abs(v):,.0f} करोड़ की {'खरीदारी' if v >= 0 else 'बिकवाली'} की")
    if vix is not None:
        out.append(f"India VIX {vix} — बाजार में घबराहट {'कम' if vix < 14 else 'ज्यादा' if vix > 20 else 'सामान्य'} है")
    return out


def market_open(now):
    if now.weekday() >= 5:
        return False
    return (now.hour, now.minute) >= (9, 15) and (now.hour, now.minute) < (15, 30)


def rotate(bank, d):
    return bank[d.toordinal() % len(bank)] if bank else None


# ---------- main ----------

def main():
    os.makedirs(OUT, exist_ok=True)
    zpath, d = latest_zip()
    print(f"building for {d}")

    rows = day_rows(zpath)
    idx = indices(d)
    head = pick(idx, HEADLINE)
    sect = sorted(pick(idx, SECTORS), key=lambda r: -r["pct"])
    vix_row = idx.get("india vix")
    vix = vix_row["close"] if vix_row else None
    br = breadth(rows)
    fd = fii_dii()
    score = health(br, head, vix)

    content = {}
    cpath = os.path.join(HERE, "content.json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            content = json.load(f)

    # The one thing no data source can produce: why it happened.
    why, events = None, []
    wpath = os.path.join(OUT, "why.json")
    if os.path.exists(wpath):
        with open(wpath) as f:
            w = json.load(f)
        if w.get("date") == f"{d}":      # yesterday's reason is worse than none
            why = w.get("points")
            events = w.get("events") or []

    now = datetime.now(IST)
    nowts = datetime.now(timezone.utc).timestamp()
    allnews = news(nowts)
    with open(os.path.join(OUT, "news.json"), "w") as f:
        json.dump({"date": f"{d}", "items": allnews[:60]}, f, ensure_ascii=False, separators=(",", ":"))

    out = {
        "date": f"{d}",
        "built_at": now.isoformat(timespec="minutes"),
        "market_open": market_open(now),
        "headline": head,
        "sectors": sect,
        "breadth": br,
        "vix": {"value": vix, "pct": vix_row["pct"] if vix_row else None, "level": fear(vix)},
        "fii_dii": fd,
        "usdinr": usdinr(),
        "health": {"score": score, "mood": mood(score)},
        "summary": summary(head, sect, br, fd, vix),
        "why": why,
        "calendar": calendar(events),
        "movers": movers(rows, constituents("nifty500")),
        "heatmap": heatmap(rows, constituents("nifty50")),
        "extremes": fresh_extremes(),
        "news": top_news(allnews, nowts),
        "quiz": rotate(content.get("quiz", []), d),
        "concept": rotate(content.get("concepts", []), d),
        "word": rotate(content.get("words", []), d),
        "tip": rotate(content.get("tips", []), d),
    }
    with open(os.path.join(OUT, "home.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    ok = lambda v: "ok" if v else "MISSING"
    print(f"  indices={len(head)} sectors={len(sect)} movers={len(rows)} news={len(allnews)}")
    print(f"  vix={ok(vix)} fii/dii={ok(fd)} fx={ok(out['usdinr'])} why={ok(why)}")
    print(f"  -> data/home.json")


def selfcheck():
    b = {"advance": 1600, "decline": 900, "unchanged": 20}
    assert 0 <= health(b, [{"pct": 0.8}], 12.0) <= 100
    assert health({"advance": 0, "decline": 0, "unchanged": 0}, [], None) >= 0  # no divide-by-zero
    assert mood(70) == "POSITIVE" and mood(30) == "NEGATIVE" and mood(50) == "NEUTRAL"
    assert fear(11) == "LOW" and fear(25) == "HIGH" and fear(None) is None
    s = summary([{"close": 24366, "pct": -0.12}], [{"name": "IT", "pct": 2.1}, {"name": "METAL", "pct": -1.7}],
                b, {"fii": {"net": 508.12}}, 11.32)
    assert len(s) == 5 and "Nifty" in s[0], s
    assert summary([], [], {"advance": 0, "decline": 0}, None, None) == []  # nothing in, nothing out
    assert num("1,234.5") == 1234.5 and num("") is None and num(None) is None
    r = [{"sym": "A", "close": 10, "prev": 9, "vol": 5, "val": 3e8, "pct": 11.1},
         {"sym": "B", "close": 8, "prev": 9, "vol": 9, "val": 3e8, "pct": -11.1},
         {"sym": "C", "close": 9, "prev": 9, "vol": 1, "val": 1e6, "pct": 0.0}]
    assert breadth(r) == {"advance": 1, "decline": 1, "unchanged": 1}
    m = movers(r, set())
    assert m["gainers"][0]["sym"] == "A" and m["losers"][0]["sym"] == "B"
    assert all(x["sym"] != "C" for x in m["active"])  # illiquid filtered out
    assert market_open(datetime(2026, 8, 14, 10, 0, tzinfo=IST))
    assert not market_open(datetime(2026, 8, 14, 18, 0, tzinfo=IST))
    assert not market_open(datetime(2026, 8, 15, 10, 0, tzinfo=IST))  # Saturday
    assert rotate([1, 2, 3], date(2026, 8, 14)) in (1, 2, 3) and rotate([], date.today()) is None
    NOW = 1_000_000_000
    mk = lambda src, hrs: {"title": src + str(hrs), "link": "x", "src": src, "ts": NOW - hrs * 3600}
    old, new = mk("A", 900), mk("B", 1)
    picked = top_news([old, new], NOW, limit=1)
    assert picked[0] is new, "stale item beat a fresh one"
    # enough other sources -> the cap binds and one feed cannot take the box
    flood = ([mk("A", h) for h in range(1, 12)] +
             [mk("B", h) for h in range(12, 17)] + [mk("C", h) for h in range(17, 22)])
    got = top_news(flood, NOW, limit=8, cap=4)
    assert sum(1 for g in got if g["src"] == "A") == 4, "per-source cap not applied"
    assert len(got) == 8 and got[0]["ts"] >= got[-1]["ts"]
    # only one source available -> cap is relaxed rather than under-filling
    solo = top_news([mk("A", h) for h in range(1, 9)], NOW, limit=8, cap=4)
    assert len(solo) == 8, "box under-filled when only one source had news"
    allstale = [mk("A", 900), mk("A", 901)]
    assert len(top_news(allstale, NOW, limit=2)) == 2, "box must never be empty"
    assert top_news([{"title":"n","link":"x","src":"A","ts":None}], NOW, limit=1)
    assert epoch("Fri, 14 Aug 2026 12:30:00 +0530") > 0
    assert epoch("garbage") is None and epoch(None) is None
    c = calendar([{"at": "11:00", "what": "RBI", "kind": "event"}])
    assert len(c) == 4 and [e["at"] for e in c][:3] == ["09:15", "11:00", "15:30"]
    assert len(calendar(None)) == 3
    print("selfcheck ok")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    elif "--feeds" in sys.argv:
        feedcheck()
    else:
        main()
