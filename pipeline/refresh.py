"""Weekly pull of Imgflip's public template list: python3 pipeline/refresh.py [--strict]

Writes data/imgflip.json (every template the API has returned, with first and last seen dates) and
appends a snapshot to data/trending.json (this week's order and caption counts). Safe to re-run: a second
run on the same day replaces that day's snapshot instead of adding another.

Fails safe: if the API is down, slow or returns something unexpected, nothing is written and the script
exits 0 with a warning (the site keeps the last good data and shows its date). --strict makes that an error.
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog  # noqa: E402

API = "https://api.imgflip.com/get_memes"
UA = "meme-search-engine/1.0 (+https://github.com/theguysaccount/meme-search-engine)"
KEEP_SNAPSHOTS = 120


def fetch(url=API, attempts=3, timeout=30):
    last = None
    for i in range(attempts):
        if i:
            time.sleep(10 * i)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            print(f"attempt {i + 1}: {e}")
    raise RuntimeError(f"Imgflip API unavailable after {attempts} attempts: {last}")


def validate(payload):
    """The list of memes, or ValueError when the response doesn't look like the documented API."""
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("response is not a successful get_memes payload")
    memes = (payload.get("data") or {}).get("memes")
    if not isinstance(memes, list) or len(memes) < 50:
        raise ValueError(f"expected at least 50 memes, got {len(memes) if isinstance(memes, list) else 'none'}")
    clean, seen = [], set()
    for m in memes:
        tid = str(m.get("id", ""))
        if not tid.isdigit() or tid in seen or not isinstance(m.get("name"), str) or not str(m.get("url", "")).startswith("https://i.imgflip.com/"):
            raise ValueError(f"unexpected entry: {str(m)[:120]}")
        seen.add(tid)
        clean.append({"id": tid, "name": m["name"].strip(), "url": m["url"], "width": m.get("width"), "height": m.get("height"),
                      "box_count": m.get("box_count"), "captions": m.get("captions")})
    return clean


def update(registry, trending, memes, date):
    """Pure: return (registry, trending) with this pull merged in."""
    registry = {k: dict(v) for k, v in registry.items()}
    for m in memes:
        entry = registry.get(m["id"], {"first_seen": date})
        entry.update({k: m[k] for k in ("name", "url", "width", "height", "box_count", "captions")})
        entry["last_seen"] = date
        registry[m["id"]] = entry
    snaps = [s for s in trending.get("snapshots", []) if s["date"] != date]
    snaps.append({"date": date, "ids": [m["id"] for m in memes],
                  "captions": {m["id"]: m["captions"] for m in memes if isinstance(m.get("captions"), int)}})
    snaps.sort(key=lambda s: s["date"])
    return dict(sorted(registry.items(), key=lambda kv: int(kv[0]))), {"snapshots": snaps[-KEEP_SNAPSHOTS:]}


def summary(text):
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    args = ap.parse_args()
    try:
        memes = validate(fetch())
    except Exception as e:
        print(f"::warning::Imgflip refresh skipped, keeping the last good data: {e}")
        return 1 if args.strict else 0
    registry, trending = catalog.load_registry(), catalog.load_trending()
    registry2, trending2 = update(registry, trending, memes, args.date)
    known = set()
    for t in catalog.load_templates(check=False):
        known.add(str(t["imgflip"]["id"]))
        known.update(str(v["id"]) for v in t["variants"])
    blocked = set(catalog.load_moderation()["blocked_ids"])
    new = [m for m in memes if m["id"] not in known and m["id"] not in blocked]
    (catalog.DATA / "imgflip.json").write_text(json.dumps(registry2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (catalog.DATA / "trending.json").write_text(json.dumps(trending2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary(f"Imgflip pull {args.date}: {len(memes)} templates; {len(registry2) - len(registry)} never seen before; "
            f"{len(new)} trending templates not described yet" + (": " + ", ".join(m["name"] for m in new[:15]) if new else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
