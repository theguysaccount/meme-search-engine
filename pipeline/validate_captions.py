"""Validate a captioning batch against pipeline/CAPTIONING.md.

    python3 pipeline/validate_captions.py <output.json> <batch.json>

Prints OK, or one line per problem. Exit code 0 when OK.
"""
import json
import re
import sys

KINDS = {"photo", "screenshot", "cartoon", "comic", "drawing", "game", "render", "graphic", "other"}
FORMATS = {"top-bottom", "labels", "panels", "versus", "ladder", "sign", "reaction", "other"}
PEOPLE = {"none", "fictional", "actor", "public", "private", "models"}
KEYS = ["id", "name", "aka", "look", "text", "use", "slots", "examples", "describe", "tags", "kind", "format",
        "panels", "franchise", "origin", "people", "variant_of", "exclude", "sure"]


def words(s):
    return len(re.findall(r"[A-Za-z0-9']+", s))


def check(entry, want_id):
    errs = [f"missing key {k}" for k in KEYS if k not in entry]
    if errs:
        return errs
    extra = set(entry) - set(KEYS)
    if extra:
        errs.append(f"unknown keys {sorted(extra)}")
    if str(entry["id"]) != str(want_id):
        errs.append(f"id {entry['id']} should be {want_id} (keep batch order)")
    if not isinstance(entry["name"], str) or not entry["name"].strip():
        errs.append("name empty")
    for k in ("aka", "text", "slots", "examples", "describe", "tags"):
        if not isinstance(entry[k], list):
            errs.append(f"{k} must be a list")
            return errs
    if entry["exclude"] is not None:
        if not isinstance(entry["exclude"], str) or len(entry["exclude"]) < 5:
            errs.append("exclude must be null or a reason")
        return errs
    if entry["kind"] not in KINDS:
        errs.append(f"kind {entry['kind']!r} not in {sorted(KINDS)}")
    if entry["format"] not in FORMATS:
        errs.append(f"format {entry['format']!r} not in {sorted(FORMATS)}")
    if entry["people"] not in PEOPLE:
        errs.append(f"people {entry['people']!r} not in {sorted(PEOPLE)}")
    if entry["sure"] not in ("high", "medium", "low"):
        errs.append("sure must be high, medium or low")
    if not isinstance(entry["panels"], int) or not 1 <= entry["panels"] <= 12:
        errs.append("panels must be an integer 1-12")
    if len(entry["aka"]) > 4:
        errs.append("aka: at most 4")
    if not all(isinstance(a, str) and a.strip() for a in entry["aka"] + entry["text"]):
        errs.append("aka and text must be non-empty strings")
    w = words(entry["look"]) if isinstance(entry["look"], str) else 0
    if not 20 <= w <= 60:
        errs.append(f"look has {w} words (20-60)")
    w = words(entry["use"]) if isinstance(entry["use"], str) else 0
    if not 15 <= w <= 60:
        errs.append(f"use has {w} words (15-60)")
    if not 1 <= len(entry["slots"]) <= 6:
        errs.append("slots: 1-6")
    if not 1 <= len(entry["examples"]) <= 2:
        errs.append("examples: 1 or 2")
    for ex in entry["examples"]:
        if not isinstance(ex, list) or len(ex) != len(entry["slots"]) or not all(isinstance(x, str) and x.strip() for x in ex):
            errs.append(f"example {ex!r} must have one non-empty string per slot ({len(entry['slots'])})")
    if not 4 <= len(entry["describe"]) <= 6:
        errs.append("describe: 4-6 phrases")
    for d in entry["describe"]:
        if not isinstance(d, str) or not 4 <= words(d) <= 16:
            errs.append(f"describe phrase {d!r}: 4-16 words")
        elif d != d.lower():
            errs.append(f"describe phrase {d!r}: lowercase")
    if not 5 <= len(entry["tags"]) <= 9:
        errs.append("tags: 5-9")
    for t in entry["tags"]:
        if not isinstance(t, str) or t != t.lower() or not 1 <= words(t) <= 3:
            errs.append(f"tag {t!r}: lowercase, 1-3 words")
    if entry["franchise"] is not None and not (isinstance(entry["franchise"], str) and entry["franchise"].strip()):
        errs.append("franchise: non-empty string or null")
    if not isinstance(entry["origin"], str) or words(entry["origin"]) > 30:
        errs.append("origin: a string of at most 30 words")
    if entry["variant_of"] is not None and not isinstance(entry["variant_of"], str):
        errs.append("variant_of: string or null")
    for k in ("look", "use", "origin"):
        if isinstance(entry[k], str) and re.search(r"https?://|<[a-z/]", entry[k]):
            errs.append(f"{k}: no URLs or markup")
    return errs


def main(out_path, batch_path):
    batch = json.load(open(batch_path, encoding="utf-8"))
    try:
        out = json.load(open(out_path, encoding="utf-8"))
    except Exception as e:
        print(f"not valid JSON: {e}")
        return 1
    if not isinstance(out, list) or len(out) != len(batch):
        print(f"expected a list of {len(batch)} entries, got {len(out) if isinstance(out, list) else type(out).__name__}")
        return 1
    bad = 0
    for item, entry in zip(batch, out):
        errs = check(entry, item["id"]) if isinstance(entry, dict) else ["entry is not an object"]
        for err in errs:
            print(f"{item['id']} {item['name']}: {err}")
        bad += bool(errs)
    if bad:
        print(f"{bad} entries need fixing")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
