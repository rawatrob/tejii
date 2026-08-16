#!/usr/bin/env python3
"""Daily NSE EOD scan. Stdlib only - no pip install, no database, no server.

Downloads NSE's official bhavcopy (one ~195KB zip per trading day), keeps them
in raw/ as the archive, and writes data/scan.json with precomputed indicators.

    python3 scan.py            # catch up to today
    python3 scan.py --back 300 # first run: pull ~300 calendar days of history
    python3 scan.py --selfcheck
"""
import csv, io, json, os, sys, urllib.error, urllib.request, zipfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "data")
URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{}_F_0000.csv.zip"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
WINDOW = 260          # trading days kept per symbol (~1 year, enough for SMA200 + 52w)
SERIES = {"EQ", "BE"}  # plain equity; drops SGBs, ETFs, govt secs, SME


# ---------- fetch ----------

def download(d):
    """Return local zip path for date d, or None if NSE has no file (holiday)."""
    path = os.path.join(RAW, f"{d:%Y%m%d}.zip")
    if os.path.exists(path):
        return path
    req = urllib.request.Request(URL.format(f"{d:%Y%m%d}"), headers={"User-Agent": UA})
    try:
        body = urllib.request.urlopen(req, timeout=60).read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None  # weekend / holiday / not published yet
        raise
    if not body.startswith(b"PK"):
        return None
    os.makedirs(RAW, exist_ok=True)
    with open(path, "wb") as f:
        f.write(body)
    return path


def read_day(path):
    """{symbol: (open, high, low, close, volume, value)} for one bhavcopy zip."""
    with zipfile.ZipFile(path) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    rows = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r["SctySrs"] not in SERIES or r["FinInstrmTp"] != "STK":
            continue
        try:
            rows[r["TckrSymb"]] = (
                float(r["OpnPric"]), float(r["HghPric"]), float(r["LwPric"]),
                float(r["ClsPric"]), float(r["TtlTradgVol"]), float(r["TtlTrfVal"]),
            )
        except ValueError:
            continue
    return rows


# ---------- indicators ----------

def sma(v, n):
    return round(sum(v[-n:]) / n, 2) if len(v) >= n else None


def rsi(closes, n=14):
    """Wilder's RSI - the smoothing everyone's charts actually use."""
    if len(closes) < n + 1:
        return None
    gain = loss = 0.0
    for i in range(1, n + 1):
        ch = closes[i] - closes[i - 1]
        gain += max(ch, 0.0)
        loss += max(-ch, 0.0)
    gain /= n
    loss /= n
    for i in range(n + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gain = (gain * (n - 1) + max(ch, 0.0)) / n
        loss = (loss * (n - 1) + max(-ch, 0.0)) / n
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def pct(a, b):
    return round((a - b) / b * 100, 2) if b else None


def build(sym, bars):
    """bars = [(o,h,l,c,vol,val), ...] oldest first."""
    closes = [b[3] for b in bars]
    vols = [b[4] for b in bars]
    c, prev = closes[-1], closes[-2] if len(closes) > 1 else closes[-1]
    hi52, lo52 = max(b[1] for b in bars), min(b[2] for b in bars)
    av20 = sma(vols, 20)
    row = {
        "sym": sym, "close": c, "chg": pct(c, prev),
        "vol": int(vols[-1]), "val_cr": round(bars[-1][5] / 1e7, 2),
        "rsi14": rsi(closes),
        "sma20": sma(closes, 20), "sma50": sma(closes, 50), "sma200": sma(closes, 200),
        "hi52": round(hi52, 2), "lo52": round(lo52, 2),
        "from_hi": pct(c, hi52), "from_lo": pct(c, lo52),
        "vol_x": round(vols[-1] / av20, 2) if av20 else None,
        "days": len(bars),
    }
    for k in ("sma20", "sma50", "sma200"):
        row["over_" + k] = (c > row[k]) if row[k] else None
    return row


# ---------- main ----------

def run(back):
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    today = date.today()
    days, got = [], 0
    for i in range(back):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        p = download(d)
        if p:
            days.append((d, p))
            got += 1
        if got >= WINDOW:
            break
    if not days:
        sys.exit("no bhavcopy found - NSE may not have published yet (runs ~18:15 IST)")
    days.sort()

    hist = {}
    for _, p in days:
        for sym, bar in read_day(p).items():
            hist.setdefault(sym, []).append(bar)

    latest = read_day(days[-1][1])
    rows = [build(s, hist[s]) for s in latest if len(hist[s]) >= 15]
    rows.sort(key=lambda r: -(r["val_cr"] or 0))

    path = os.path.join(OUT, "scan.json")
    guard(rows, path)
    out = {"date": f"{days[-1][0]}", "count": len(rows), "stocks": rows}
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"{days[-1][0]}: {len(rows)} stocks, {len(days)} sessions -> data/scan.json")


def guard(rows, path):
    """Never replace a good scan.json with a worse one.

    Running without --back pulls only ~8 sessions; the >=15-bar rule then drops
    every stock and the file silently becomes {"count":0}. Failing loudly beats
    a homepage that quietly shows zeros.
    """
    if not rows:
        sys.exit("refusing to write an empty scan.json - "
                 "not enough history, try: scan.py --back 400")
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            had = json.load(f).get("count", 0)
    except (ValueError, OSError):
        return
    if had and len(rows) < had * 0.5:
        sys.exit(f"refusing to shrink scan.json from {had} to {len(rows)} stocks - "
                 "run with a larger --back, or delete the file if this is intended")


def selfcheck():
    up = [float(i) for i in range(1, 40)]
    assert rsi(up) == 100.0, rsi(up)                       # only gains
    assert rsi([float(40 - i) for i in range(39)]) == 0.0   # only losses
    flat = [10.0] * 40
    assert rsi(flat) == 100.0                              # no loss -> guard, not ZeroDivision
    assert rsi([1.0, 2.0]) is None                         # too short
    assert sma([1.0, 2.0, 3.0], 2) == 2.5
    assert sma([1.0], 5) is None
    assert pct(110, 100) == 10.0 and pct(1, 0) is None
    # known-value check: alternating +2/-1 drift should sit above 50
    seq, x = [], 100.0
    for i in range(40):
        x += 2 if i % 2 else -1
        seq.append(x)
    assert 50 < rsi(seq) < 100, rsi(seq)
    bars = [(1, 12.0, 8.0, 10.0 + i % 3, 1000 + i, 5e7) for i in range(30)]
    r = build("TEST", bars)
    assert r["sym"] == "TEST" and r["days"] == 30 and r["hi52"] == 12.0 and r["lo52"] == 8.0
    assert r["vol_x"] is not None and r["sma200"] is None and r["over_sma200"] is None
    # guard: empty result must never overwrite a good file
    tmp = os.path.join(OUT, "_guard_test.json")
    os.makedirs(OUT, exist_ok=True)
    for bad in ([], [{"x": 1}]):                      # empty, and a 90% shrink
        with open(tmp, "w") as f:
            json.dump({"count": 10, "stocks": []}, f)
        try:
            guard(bad, tmp)
            raise AssertionError(f"guard let {len(bad)} rows through")
        except SystemExit:
            pass
    guard([{"x": i} for i in range(9)], tmp)          # 9 vs 10 is fine
    os.remove(tmp)
    print("selfcheck ok")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        n = sys.argv[sys.argv.index("--back") + 1] if "--back" in sys.argv else "12"
        run(int(n))
