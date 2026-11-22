"""Turn validated caption batches into catalog files.

    python3 pipeline/merge_captions.py --batch B1.json --out O1.json [--batch B2.json --out O2.json ...] [--date YYYY-MM-DD]

Batch items carry the Imgflip metadata (id, name, code, image, width, height, boxes, rank); outputs are
lists of entries in the shape pipeline/CAPTIONING.md describes, in batch order.

- New templates become data/templates/<slug>.json. Existing files are never overwritten: a template that
  is already in the catalog is skipped and reported.
- Entries marked as another version of a template (variant_of) are attached to that template's
  `variants` list instead of getting their own page.
- Excluded entries are added to data/moderation.json (blocked_ids), with the reason.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog  # noqa: E402
from validate_captions import check  # noqa: E402

FIELDS = ["name", "aka", "look", "text", "use", "slots", "examples", "describe", "tags", "kind", "format", "panels",
          "franchise", "origin", "people"]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", action="append", required=True)
    ap.add_argument("--out", action="append", required=True)
    ap.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-sure", choices=["low", "medium", "high"], default="medium",
                    help="entries less sure than this are reported and left for a later pass, not published")
    args = ap.parse_args()
    if len(args.batch) != len(args.out):
        raise SystemExit("give one --out per --batch")

    pairs = []
    for b, o in zip(args.batch, args.out):
        batch = json.load(open(b, encoding="utf-8"))
        out = json.load(open(o, encoding="utf-8"))
        if len(batch) != len(out):
            raise SystemExit(f"{o}: {len(out)} entries for {len(batch)} batch items")
        for item, entry in zip(batch, out):
            errs = check(entry, item["id"])
            if errs:
                raise SystemExit(f"{o}: {item['id']} {item['name']}: {errs[0]} (run validate_captions.py)")
            pairs.append((item, entry))

    tdir = catalog.DATA / "templates"
    tdir.mkdir(parents=True, exist_ok=True)
    existing = {}
    for path in tdir.glob("*.json"):
        t = json.loads(path.read_text(encoding="utf-8"))
        existing[str(t["imgflip"]["id"])] = path
        for v in t.get("variants", []):
            existing[str(v["id"])] = path
    moderation = catalog.load_moderation()

    # variant_of names a template as it appears in the Imgflip list; fall back to our cleaned-up names. A name can
    # belong to several uploads, so keep every id (in batch order) and never resolve an entry to itself.
    by_imgflip, by_ours = {}, {}
    for item, entry in pairs:
        by_imgflip.setdefault(norm(item["name"]), []).append(item["id"])
        by_ours.setdefault(norm(entry["name"]), []).append(item["id"])
    entries = {item["id"]: (item, entry) for item, entry in pairs}

    def target_of(tid):
        want = entries[tid][1].get("variant_of")
        if not want:
            return None
        for table in (by_imgflip, by_ours):
            options = [o for o in table.get(norm(want), []) if o != tid and o in entries and not entries[o][1].get("exclude")]
            # Prefer an upload that isn't itself marked as a version of something else.
            options.sort(key=lambda o: bool(entries[o][1].get("variant_of")))
            if options:
                return options[0]
        return None

    def canonical(tid, seen=()):
        if entries[tid][1].get("exclude"):
            return tid
        other = target_of(tid)
        if not other or other in seen:
            return tid
        return canonical(other, seen + (tid,))

    new_files, variants, skipped, blocked = {}, [], [], []
    rank = {"low": 0, "medium": 1, "high": 2}
    for item, entry in pairs:
        tid = str(item["id"])
        if not entry.get("exclude") and rank[entry["sure"]] < rank[args.min_sure]:
            skipped.append(f"{item['name']} (sure: {entry['sure']}; left for review)")
            continue
        if entry.get("exclude"):
            if tid not in moderation["blocked_ids"]:
                moderation["blocked_ids"][tid] = f"{item['name']}: {entry['exclude']}"
                blocked.append(tid)
            continue
        if tid in existing:
            skipped.append(f"{item['name']} (already in {existing[tid].name})")
            continue
        root = canonical(tid)
        if root != tid:
            variants.append((root, {"id": tid, "name": item["name"]}))
            continue
        t = {"slug": None}
        for k in FIELDS:
            t[k] = entry[k]
        t["imgflip"] = {"id": tid, "code": item["code"], "image": item.get("image"), "width": item.get("width"),
                        "height": item.get("height"), "boxes": item.get("boxes")}
        t["variants"] = []
        t["rank_all_time"] = item.get("rank")
        t["sure"] = entry["sure"]
        t["added"] = args.date
        if norm(item["name"]) != norm(entry["name"]) and norm(item["name"]) not in {norm(a) for a in t["aka"]}:
            t["imgflip"]["name"] = item["name"]
        new_files[tid] = t

    # Slugs from names; a clash gets the Imgflip id appended.
    taken = {p.stem for p in tdir.glob("*.json")}
    for tid, t in new_files.items():
        slug = catalog.slugify(t["name"]) or f"template-{tid}"
        if slug in taken:
            slug = f"{slug}-{tid}"
        taken.add(slug)
        t["slug"] = slug
    for root, v in variants:
        if root in new_files:
            new_files[root]["variants"].append(v)
        elif root in existing:
            skipped.append(f"{v['name']} (variant of a template already in the catalog; add it by hand)")

    errors = []
    for t in new_files.values():
        errs = catalog.validate_template({k: v for k, v in t.items()}, moderation)
        errors += [f"{t['slug']}: {e}" for e in errs]
    if errors:
        raise SystemExit("not merged:\n  " + "\n  ".join(errors))
    if not args.dry_run:
        for t in new_files.values():
            (tdir / f"{t['slug']}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (catalog.DATA / "moderation.json").write_text(json.dumps(moderation, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"new templates: {len(new_files)}; variants attached: {sum(1 for r, _ in variants if r in new_files)}; "
          f"newly blocked: {len(blocked)}; skipped: {len(skipped)}{' (dry run)' if args.dry_run else ''}")
    for s in skipped:
        print("  skipped:", s)


if __name__ == "__main__":
    main()
