#!/usr/bin/env python3
# =====================================================================
#  update-news.py -- regenerate news.json for the GRV signage
#  "In the News" panel from Recovery Centers of America's LIVE
#  WordPress REST API.
#
#  Runs both locally (one-time seed) and in GitHub Actions (cron ~3h).
#  Writes <repo-root>/news.json in the exact shape the TV panel reads:
#      { source, updated_at, items: [ {title, date, excerpt, url}, ... ] }
#
#  SAFE BY DESIGN: on any fetch/parse error or empty result it leaves the
#  existing news.json untouched (the panel keeps showing last-good) and
#  exits 0 -- so a transient API blip never blanks the TVs or trips a
#  false-alarm failed cron run.
# =====================================================================
import json, os, re, sys, html, urllib.request

CATS  = "274,291"          # RCA WP news/press categories (matches the original snapshot)
COUNT = 8                  # store 8; the panel renders only the top 3
API   = ("https://recoverycentersofamerica.com/wp-json/wp/v2/posts"
         f"?categories={CATS}&per_page={COUNT}&orderby=date&order=desc"
         "&_fields=title,date,link,excerpt")
OUT   = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "news.json"))

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")                                  # strip HTML tags
    s = html.unescape(s)                                                  # decode &#8217; -> ' etc.
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*(\[…\]|\[\.\.\.\]|Continue reading.*|Read More.*)$", "", s, flags=re.I).strip()
    return s

def main():
    req = urllib.request.Request(API, headers={
        "User-Agent": "GRV-Signage-NewsBot/1.0 (+RCA Greenville IT signage)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            posts = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"WARNING: fetch failed ({e}); leaving existing news.json untouched", file=sys.stderr)
        return 0
    if not isinstance(posts, list) or not posts:
        print("WARNING: no posts returned; leaving existing news.json untouched", file=sys.stderr)
        return 0

    items = []
    for p in posts:
        title = clean((p.get("title") or {}).get("rendered", ""))
        if not title:
            continue
        items.append({
            "title":   title,
            "date":    p.get("date", ""),
            "excerpt": clean((p.get("excerpt") or {}).get("rendered", ""))[:220],
            "url":     p.get("link", ""),
        })
    if not items:
        print("WARNING: posts had no usable titles; leaving news.json untouched", file=sys.stderr)
        return 0

    from datetime import datetime, timezone
    doc = {
        "source":     f"recoverycentersofamerica.com WP REST (categories {CATS})",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items":      items,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"OK: wrote {len(items)} items -> {OUT} (updated_at {doc['updated_at']})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
