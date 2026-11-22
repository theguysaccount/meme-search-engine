"""Prepare a captioning batch of templates that are trending but not described yet (for the Claude routine).

    python3 pipeline/caption_queue.py <work_dir> [--limit 40]

Writes <work_dir>/batch.json and downloads each template's image to <work_dir>/view/ (for looking at only;
never commit images). Then follow pipeline/CAPTIONING.md and merge with pipeline/merge_captions.py.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog  # noqa: E402
from refresh import UA  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work_dir")
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()
    work = Path(args.work_dir)
    (work / "view").mkdir(parents=True, exist_ok=True)
    known = set()
    for t in catalog.load_templates():
        known.add(str(t["imgflip"]["id"]))
        known.update(str(v["id"]) for v in t["variants"])
    moderation = catalog.load_moderation()
    registry = catalog.load_registry()
    snaps = catalog.load_trending()["snapshots"]
    order = []
    for snap in reversed(snaps):
        for tid in snap["ids"]:
            if tid not in order:
                order.append(tid)
    batch = []
    for tid in order:
        reg = registry.get(tid)
        if not reg or tid in known or tid in moderation["blocked_ids"] or catalog.blocked_name(reg["name"], moderation):
            continue
        code = reg["url"].rsplit("/", 1)[1].split(".")[0]
        view = work / "view" / f"{tid}.{reg['url'].rsplit('.', 1)[1]}"
        with urllib.request.urlopen(urllib.request.Request(reg["url"], headers={"User-Agent": UA}), timeout=30) as r:
            view.write_bytes(r.read())
        time.sleep(0.5)
        batch.append({"id": tid, "name": reg["name"], "view": str(view.resolve()), "boxes": reg.get("box_count"), "code": code,
                      "image": reg["url"].rsplit("/", 1)[1], "width": reg.get("width"), "height": reg.get("height"), "rank": None})
        if len(batch) >= args.limit:
            break
    (work / "batch.json").write_text(json.dumps(batch, indent=1), encoding="utf-8")
    names = sorted({t["name"] for t in catalog.load_templates()} | {r["name"] for r in registry.values()})
    (work / "all_names.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"{len(batch)} templates to describe -> {work / 'batch.json'}")


if __name__ == "__main__":
    main()
