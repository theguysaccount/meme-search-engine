"""Weekly health check of the live site: python3 scripts/check_live.py https://theguysaccount.github.io/meme-search-engine

- every sitemap page answers 200 and carries its own canonical URL;
- the JSON API files parse and agree with each other;
- the IndexNow key file is served;
- the trending data is fresh: older than 9 days writes stale=true to $GITHUB_OUTPUT (the workflow then
  dispatches a refresh); older than 21 days is an error;
- a sample of template pictures still loads from Imgflip (a missing one is a warning, not a failure: the
  page falls back to a text link by itself).
Exits 1 on any error.
"""
import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "meme-search-engine-healthcheck/1.0 (+https://github.com/theguysaccount/meme-search-engine)"
STALE_DAYS, DEAD_DAYS = 9, 21


def get(url, method="GET"):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return e.code, b""
            last = e
        except OSError as e:
            last = e
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def main(base):
    base = base.rstrip("/")
    errors, warnings = [], []
    status, body = get(f"{base}/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", body.decode())
    if status != 200 or len(urls) < 10:
        errors.append(f"sitemap: status {status}, {len(urls)} URLs")
    for u in urls:
        try:
            status, page = get(u)
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', page.decode("utf-8", "replace"))
            if status != 200 or not canon or canon.group(1) != u:
                errors.append(f"{u}: status {status}, canonical {canon.group(1) if canon else None}")
        except Exception as e:
            errors.append(str(e))
    meta = json.loads(get(f"{base}/api/v1/meta.json")[1])
    templates = json.loads(get(f"{base}/api/v1/templates.json")[1])
    index = json.loads(get(f"{base}/api/v1/search-index.json")[1])
    trending = json.loads(get(f"{base}/api/v1/trending.json")[1])
    if templates["count"] != len(templates["templates"]) or templates["count"] != meta["templates"]:
        errors.append("templates.json and meta.json disagree on the count")
    if sum(1 for r in index["templates"] if not r.get("x")) != meta["templates"]:
        errors.append("search index and meta.json disagree on the count")
    pages = {u.rstrip("/").rsplit("/", 1)[1] for u in urls if "/meme/" in u}
    missing = [t["slug"] for t in templates["templates"] if t["slug"] not in pages]
    if missing:
        errors.append(f"{len(missing)} templates missing from the sitemap: {missing[:5]}")
    key = (ROOT / "site" / "indexnow-key.txt").read_text().strip()
    if get(f"{base}/{key}.txt")[1].decode().strip() != key:
        errors.append("IndexNow key file not served")
    stale = False
    if trending.get("date"):
        age = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.date.fromisoformat(trending["date"])).days
        print(f"trending data from {trending['date']} ({age} days old)")
        if age > DEAD_DAYS:
            errors.append(f"trending data is {age} days old: the weekly refresh has not succeeded for three weeks")
        stale = age > STALE_DAYS
    else:
        stale = True
        warnings.append("no trending snapshot yet")
    output("stale", "true" if stale else "false")
    sample = random.Random(datetime.date.today().isoformat()).sample(
        [r for r in index["templates"] if r.get("i")], min(20, sum(1 for r in index["templates"] if r.get("i"))))
    for r in sample:
        status, data = get(f"https://i.imgflip.com/4/{r['i']}.jpg")
        if status != 200 or not data.startswith(b"\xff\xd8"):
            warnings.append(f"picture for {r['n']} ({r['id']}) answered {status}; its page shows a text link instead")
        time.sleep(0.3)
    print(f"checked {len(urls)} pages, 4 API files, {len(sample)} pictures; {meta['templates']} templates")
    for w in warnings:
        print(f"::warning::{w}")
    for e in errors:
        print(f"::error::{e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
