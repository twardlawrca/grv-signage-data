#!/usr/bin/env python3
# =====================================================================
#  update-live.py -- regenerate the GRV boards' LIVE feeds:
#      live/headlines.json   world headlines  (Wikipedia "In the news", CC BY-SA 4.0)
#      live/economy.json     the economy at a glance (BLS, Federal Reserve H.15, EIA)
#
#  Every source is free AND cleared for display on a business screen:
#  Wikipedia text is CC BY-SA 4.0 (we show it verbatim with attribution);
#  BLS, the Federal Reserve Board and EIA are U.S. government works
#  (public domain). No market-data vendor, no wire service, no key.
#
#  Runs in GitHub Actions (cron ~6h) and locally. The boards' campaign
#  overlay (v1.7+) renders these files as "live" slides.
#
#  SAFE BY DESIGN: each section that fails to fetch/parse keeps what the
#  existing file already has (the boards keep showing last-good), and the
#  script always exits 0 -- a transient blip never blanks a TV or trips a
#  false-alarm failed cron run.
# =====================================================================
import json, os, re, sys, html, urllib.request
from datetime import datetime, timezone, timedelta

UA   = "GRV-Signage-LiveBot/1.0 (+RCA Greenville IT signage; github.com/twardlawrca/grv-signage-data)"
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT  = os.path.join(ROOT, "live")

# Words that keep a headline off a treatment-centre screen. ONE list for the whole fleet:
# screen.json at the repo root (Marketing / Clinical own it; the GRVTV 2.0 runtime reads the
# same file for On this day, the quote, the ticker and the lobby news). A term matches whole
# words, case-insensitive; a trailing * matches any ending. This hard-coded list is only the
# fallback when screen.json is missing or malformed.
EXCLUDE_FALLBACK = ["overdose", "opioid*", "fentanyl", "heroin", "cocaine", "methamphetamine", "narcotic*",
                    "drug*", "alcohol*", "drunk*", "suicide", "rape*", "sexual assault", "molest*", "child abuse",
                    "massacre*", "behead*", "execut*", "hostage*", "shoot*", "gunman", "gunmen", "stab*",
                    "terror*", "attack*", "dead", "killed", "kill*", "war", "wars", "battle*", "crash*"]
MAX_HEADLINES = 6

def screen_regex():
    """Compile screen.json's exclude list (fallback: EXCLUDE_FALLBACK) into one word-boundary regex."""
    terms, src = None, "screen.json"
    try:
        with open(os.path.join(ROOT, "screen.json"), encoding="utf-8") as f:
            terms = json.load(f).get("exclude")
        if not isinstance(terms, list) or not terms:
            raise ValueError("no exclude list")
    except Exception as e:
        print(f"WARNING: screen.json unusable ({e}); using the built-in fallback list", file=sys.stderr)
        terms, src = EXCLUDE_FALLBACK, "built-in fallback"
    parts = []
    for t in terms:
        t = str(t or "").strip().lower()
        pre, suf = t.startswith("*"), t.endswith("*")
        t = t.strip("*")
        if not t:
            continue
        parts.append(("" if pre else r"\b") + r"\s+".join(re.escape(w) for w in t.split()) + ("" if suf else r"\b"))
    print(f"screen: {len(parts)} terms from {src}", file=sys.stderr)
    return re.compile("(?:" + "|".join(parts) + ")", re.I)

SCREEN = None
def screened(text):
    global SCREEN
    if SCREEN is None:
        SCREEN = screen_regex()
    return bool(SCREEN.search(text or ""))

def get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_existing(name):
    try:
        with open(os.path.join(OUT, name + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write(name, doc):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

# ---------------------------------------------------------------- headlines
def headlines():
    items, seen = [], set()
    today = datetime.now(timezone.utc)
    for d in (today, today - timedelta(days=1)):
        try:
            feed = json.loads(get("https://api.wikimedia.org/feed/v1/wikipedia/en/featured/" + d.strftime("%Y/%m/%d")))
        except Exception as e:
            print(f"WARNING: wikimedia feed {d:%Y-%m-%d} failed ({e})", file=sys.stderr)
            continue
        for n in feed.get("news") or []:
            text = clean(n.get("story", ""))
            if not text or text in seen:
                continue
            if screened(text):
                print(f"screened: {text[:80]}", file=sys.stderr)
                continue
            url = ""
            for l in n.get("links") or []:
                url = ((l.get("content_urls") or {}).get("desktop") or {}).get("page", "")
                if url:
                    break
            seen.add(text)
            items.append({"text": text, "url": url, "day": d.strftime("%Y-%m-%d")})
        if len(items) >= MAX_HEADLINES:
            break
    if not items:
        raise RuntimeError("no headlines")
    return {
        "source": "Wikipedia · In the news · CC BY-SA 4.0",
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "updated_at": now_iso(),
        "items": items[:MAX_HEADLINES],
    }

# ---------------------------------------------------------------- economy
MONTHS = {"M01": "January", "M02": "February", "M03": "March", "M04": "April", "M05": "May", "M06": "June",
          "M07": "July", "M08": "August", "M09": "September", "M10": "October", "M11": "November", "M12": "December"}

def bls(series):
    d = json.loads(get("https://api.bls.gov/publicAPI/v1/timeseries/data/" + series))
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError("BLS " + str(d.get("message")))
    data = [x for x in d["Results"]["series"][0]["data"] if x["period"].startswith("M") and x["period"] != "M13"]
    data.sort(key=lambda x: (x["year"], x["period"]), reverse=True)     # newest first
    return data

def pts(a, b, unit):
    diff = round(a - b, 2)
    if abs(diff) < 0.005:
        return "flat", "unchanged"
    return ("up" if diff > 0 else "down"), f"{abs(diff):g} {unit}"

def unemployment():
    d = bls("LNS14000000")
    cur, prev = float(d[0]["value"]), float(d[1]["value"])
    dir_, delta = pts(cur, prev, "pt")
    return {"key": "unemployment", "label": "Unemployment", "value": f"{cur:g}%", "raw": cur,
            "asof": MONTHS[d[0]["period"]] + " " + d[0]["year"],
            "delta": (delta if dir_ == "flat" else delta + " from " + MONTHS[d[1]["period"]]), "dir": dir_,
            "note": "U.S. rate · Bureau of Labor Statistics"}

def inflation():
    d = bls("CUUR0000SA0")
    if len(d) < 14:
        raise RuntimeError("CPI history too short")
    yoy  = (float(d[0]["value"]) / float(d[12]["value"]) - 1) * 100
    yoy1 = (float(d[1]["value"]) / float(d[13]["value"]) - 1) * 100
    dir_, delta = pts(round(yoy, 1), round(yoy1, 1), "pt")
    return {"key": "inflation", "label": "Inflation", "value": f"{yoy:.1f}%", "raw": round(yoy, 2),
            "asof": MONTHS[d[0]["period"]] + " " + d[0]["year"],
            "delta": (delta if dir_ == "flat" else delta + " from " + MONTHS[d[1]["period"]]), "dir": dir_,
            "note": "Consumer prices, past 12 months · BLS"}

def h15():
    t = get("https://www.federalreserve.gov/releases/h15/", "text/html")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, flags=re.S)
    table = []
    for r in rows:
        cells = [clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, flags=re.S)]
        if cells:
            table.append(cells)
    dates = next((c[1:] for c in table if c[0] == "Instruments"), None)
    if not dates:
        raise RuntimeError("H.15 header not found")
    def row(pred):
        for c in table:
            if pred(c[0]):
                vals = [(dates[i], v) for i, v in enumerate(c[1:]) if re.match(r"^\d+(\.\d+)?$", v or "")]
                if len(vals) >= 2:
                    return vals
        raise RuntimeError("H.15 row missing")
    def fmt_date(s, short=False):         # "2026Sep14" -> "September 14" / "Sep 14"
        m = re.match(r"(\d{4})([A-Za-z]{3})(\d+)", s)
        if not m:
            return s
        return datetime.strptime(m.group(2), "%b").strftime("%b" if short else "%B") + " " + m.group(3)
    ff = row(lambda s: s.startswith("Federal funds (effective)"))
    ty = row(lambda s: s == "10-year")     # the FIRST 10-year row is the nominal Treasury yield
    out = []
    for key, label, note, vals in (("fedfunds", "Fed funds rate", "Effective rate · Federal Reserve", ff),
                                   ("treasury10", "10-year Treasury", "Yield · Federal Reserve H.15", ty)):
        (d1, v1), (d0, v0) = vals[-2], vals[-1]
        cur, prev = float(v0), float(v1)
        dir_, delta = pts(cur, prev, "pt")
        out.append({"key": key, "label": label, "value": f"{cur:.2f}%", "raw": cur, "asof": fmt_date(d0),
                    "delta": (delta if dir_ == "flat" else delta + " from " + fmt_date(d1, True)), "dir": dir_, "note": note})
    return out

def gas(existing):
    x = get("https://www.eia.gov/petroleum/gasdiesel/includes/gas_diesel_rss.xml", "*/*")
    item = re.findall(r"<item>(.*?)</item>", x, flags=re.S)[0]
    title = clean(re.search(r"<title>(.*?)</title>", item, flags=re.S).group(1))
    desc = html.unescape(re.search(r"<description>(.*?)</description>", item, flags=re.S).group(1))
    desc = desc.replace("<![CDATA[", "").replace("]]>", "")
    section = desc.split("On-Highway Diesel")[0]
    prices = {}
    for m in re.finditer(r"(\d+\.\d{3})\s+\.+\s*([A-Za-z][A-Za-z .]*?)\s*<br", section):
        prices.setdefault(m.group(2).strip(), float(m.group(1)))
    us, region = prices.get("U.S."), prices.get("Lower Atlantic")
    if us is None:
        raise RuntimeError("EIA U.S. price not found")
    m = re.search(r"(\d\d)/(\d\d)/(\d\d)", title)
    asof_date = f"20{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""
    asof = datetime.strptime(asof_date, "%Y-%m-%d").strftime("Week of %B %-d") if asof_date else ""
    it = {"key": "gas", "label": "Regular gas", "value": f"${us:.2f}", "raw": us, "asof": asof, "asofDate": asof_date,
          "delta": None, "dir": None, "note": (f"Lower Atlantic ${region:.2f} · " if region else "") + "EIA, U.S. average"}
    # No history in the RSS: carry the previous week's price forward from the last file we wrote.
    old = next((o for o in (existing or {}).get("items", []) if o.get("key") == "gas"), None)
    if old and old.get("asofDate") and old.get("raw") is not None:
        if old["asofDate"] != asof_date:
            it["prev"], it["prevDate"] = old["raw"], old["asofDate"]
        elif old.get("prev") is not None:
            it["prev"], it["prevDate"] = old["prev"], old.get("prevDate")
    if it.get("prev") is not None:
        dir_, _ = pts(us, it["prev"], "")
        diff = abs(round(us - it["prev"], 2))
        it["dir"] = dir_
        it["delta"] = "unchanged" if dir_ == "flat" else f"{diff:.2f} from last week"
    return it

def economy(existing):
    items, order = [], ["unemployment", "inflation", "fedfunds", "treasury10", "gas"]
    got = {}
    for name, fn in (("unemployment", unemployment), ("inflation", inflation)):
        try:
            got[name] = fn()
        except Exception as e:
            print(f"WARNING: {name} failed ({e}); keeping previous", file=sys.stderr)
    try:
        for it in h15():
            got[it["key"]] = it
    except Exception as e:
        print(f"WARNING: H.15 failed ({e}); keeping previous", file=sys.stderr)
    try:
        got["gas"] = gas(existing)
    except Exception as e:
        print(f"WARNING: EIA gas failed ({e}); keeping previous", file=sys.stderr)
    old = {o.get("key"): o for o in (existing or {}).get("items", [])}
    for k in order:
        if k in got:
            items.append(got[k])
        elif k in old:
            items.append(old[k])
    if not items:
        raise RuntimeError("no economy items")
    return {
        "source": "U.S. Bureau of Labor Statistics · Federal Reserve Board · U.S. Energy Information Administration",
        "updated_at": now_iso(),
        "items": items,
    }

def main():
    rc = 0
    for name, fn in (("headlines", lambda: headlines()), ("economy", lambda: economy(load_existing("economy")))):
        try:
            doc = fn()
            old = load_existing(name)
            if old and old.get("items") == doc.get("items"):
                print(f"{name}: unchanged ({len(doc['items'])} items)")
                continue
            write(name, doc)
            print(f"OK: wrote {len(doc['items'])} items -> live/{name}.json")
        except Exception as e:
            print(f"WARNING: {name} not updated ({e}); existing file kept", file=sys.stderr)
    return rc

if __name__ == "__main__":
    sys.exit(main())
