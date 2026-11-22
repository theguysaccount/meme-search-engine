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

    # Imgflip names (and our names) of everything in this run, to resolve variant_of.
    by_name = {}
    for item, entry in pairs:
        by_name.setdefault(norm(item["name"]), item["id"])
        by_name.setdefault(norm(entry["name"]), item["id"])
    entries = {item["id"]: (item, entry) for item, entry in pairs}

    def canonical(tid, seen=()):
        item, entry = entries[tid]
        target = entry.get("variant_of")
        if not target or entry.get("exclude"):
            return tid
        other = by_name.get(norm(target))
        if not other or other == tid or other in seen or other not in entries or entries[other][1].get("exclude"):
            return tid
        return canonical(other, seen + (tid,))

    new_files, variants, skipped, blocked = {}, [], [], []
    for item, entry in pairs:
        tid = str(item["id"])
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
