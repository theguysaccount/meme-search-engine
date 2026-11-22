"""Load and validate the meme template catalog (data/templates/*.json) and the Imgflip snapshots.

The catalog is hand- and agent-written; the Imgflip files are machine-written by pipeline/refresh.py.
Everything here is pure: no network, no writes.
"""
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("MEME_DATA_DIR") or ROOT / "data")

KINDS = {
    "photo": "Photo", "screenshot": "Film or TV still", "cartoon": "Cartoon still", "comic": "Comic", "drawing": "Drawing",
    "game": "Video game", "render": "3D render", "graphic": "Graphic", "other": "Other",
}
FORMATS = {
    "top-bottom": ("Top and bottom caption", "One image with a caption above and below it."),
    "labels": ("Labels on people or things", "One image where each person or object gets a label."),
    "panels": ("Multi-panel story", "A short sequence of panels that tells a tiny story."),
    "versus": ("Comparison", "Two or more options set against each other: one rejected and one approved, or weak against strong."),
    "ladder": ("Escalating ladder", "A ranked ladder where each step is fancier, smarter or more absurd than the last."),
    "sign": ("Text on a sign or screen", "Your text goes on a sign, board, screen, paper or button inside the picture."),
    "reaction": ("Reaction", "A face or moment that reacts to the caption."),
    "other": ("Other", "Formats that don't fit the usual shapes."),
}
PEOPLE = {"none", "fictional", "actor", "public", "private", "models"}
REQUIRED = ["slug", "name", "aka", "look", "text", "use", "slots", "examples", "describe", "tags", "kind", "format",
            "panels", "franchise", "origin", "people", "imgflip", "variants", "added"]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE = re.compile(r"^[a-z0-9]+\.(jpg|png|gif)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def words(text):
    return len(re.findall(r"[A-Za-z0-9']+", text))


def slugify(name):
    s = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load_moderation():
    return json.loads((DATA / "moderation.json").read_text(encoding="utf-8"))


def blocked_name(name, moderation):
    """True when a template name contains a term that keeps it off the site (used for unreviewed names)."""
    low = " " + re.sub(r"[^a-z0-9]+", " ", name.lower()) + " "
    return any(" " + term + " " in low for term in moderation["blocked_terms"])


def validate_template(t, moderation):
    errs = []
    for key in REQUIRED:
        if key not in t:
            errs.append(f"missing {key}")
    if errs:
        return errs
    if not SLUG.match(t["slug"]):
        errs.append("slug must be lowercase words joined by hyphens")
    for key in ("name", "look", "use", "origin"):
        if not isinstance(t[key], str):
            errs.append(f"{key} must be a string")
    for key in ("aka", "text", "slots", "examples", "describe", "tags", "variants"):
        if not isinstance(t[key], list):
            errs.append(f"{key} must be a list")
    if errs:
        return errs
    if not t["name"].strip():
        errs.append("name is empty")
    if not 15 <= words(t["look"]) <= 70:
        errs.append(f"look has {words(t['look'])} words (15-70)")
    if not 10 <= words(t["use"]) <= 70:
        errs.append(f"use has {words(t['use'])} words (10-70)")
    if not 1 <= len(t["slots"]) <= 6:
        errs.append("slots: 1-6")
    if not 1 <= len(t["examples"]) <= 3:
        errs.append("examples: 1-3")
    for ex in t["examples"]:
        if not isinstance(ex, list) or len(ex) != len(t["slots"]) or not all(isinstance(x, str) and x.strip() for x in ex):
            errs.append("each example needs one non-empty string per slot")
    if not 3 <= len(t["describe"]) <= 8:
        errs.append("describe: 3-8 phrases")
    for d in t["describe"]:
        if not isinstance(d, str) or not 3 <= words(d) <= 18:
            errs.append(f"describe phrase {d!r}: 3-18 words")
    if not 3 <= len(t["tags"]) <= 10:
        errs.append("tags: 3-10")
    if t["kind"] not in KINDS:
        errs.append(f"unknown kind {t['kind']!r}")
    if t["format"] not in FORMATS:
        errs.append(f"unknown format {t['format']!r}")
    if t["people"] not in PEOPLE:
        errs.append(f"unknown people {t['people']!r}")
    if not isinstance(t["panels"], int) or not 1 <= t["panels"] <= 12:
        errs.append("panels: integer 1-12")
    if t["franchise"] is not None and not (isinstance(t["franchise"], str) and t["franchise"].strip()):
        errs.append("franchise: non-empty string or null")
    if words(t["origin"]) > 34:
        errs.append("origin: at most 34 words")
    if not DATE.match(str(t["added"])):
        errs.append("added must be YYYY-MM-DD")
    im = t["imgflip"]
    if not isinstance(im, dict) or not re.match(r"^\d+$", str(im.get("id", ""))):
        errs.append("imgflip.id must be a numeric string")
    else:
        if im.get("image") is not None and not IMAGE.match(im["image"]):
            errs.append("imgflip.image must look like 1ur9b0.jpg or be null")
        if not re.match(r"^[a-z0-9]+$", str(im.get("code", ""))):
            errs.append("imgflip.code must be the base-36 image code")
        elif int(im["code"], 36) != int(im["id"]):
            errs.append("imgflip.code must be the template id in base 36")
        for key in ("width", "height"):
            if im.get(key) is not None and not (isinstance(im[key], int) and im[key] > 0):
                errs.append(f"imgflip.{key} must be a positive integer or null")
    for v in t["variants"]:
        if not isinstance(v, dict) or not re.match(r"^\d+$", str(v.get("id", ""))) or not v.get("name"):
            errs.append("each variant needs id and name")
    for field in ("name", "look", "use", "origin"):
        if re.search(r"https?://|<[a-z/]", t[field]):
            errs.append(f"{field}: no URLs or markup")
    text = " ".join([t["name"], t["look"], t["use"], t["origin"], *t["aka"], *t["describe"], *t["tags"], *t["text"],
                     *t["slots"], *[x for ex in t["examples"] if isinstance(ex, list) for x in ex if isinstance(x, str)]])
    low = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
    for term in moderation["never_terms"]:
        if " " + term + " " in low:
            errs.append(f"contains a term that is never published: {term!r}")
    if str(im.get("id")) in moderation["blocked_ids"]:
        errs.append("this Imgflip id is blocked in data/moderation.json")
    return errs


def load_templates(check=True):
    """All catalog entries, sorted by name. Raises ValueError listing every problem when check is on."""
    moderation = load_moderation()
    templates, problems = [], []
    seen_slug, seen_id = {}, {}
    for path in sorted((DATA / "templates").glob("*.json")):
        try:
            t = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{path.name}: not valid JSON ({e})")
            continue
        errs = validate_template(t, moderation)
        if not errs and path.stem != t["slug"]:
            errs.append(f"file name must be {t['slug']}.json")
        if not errs:
            if t["slug"] in seen_slug:
                errs.append(f"duplicate slug (also {seen_slug[t['slug']]})")
            seen_slug[t["slug"]] = path.name
            for tid in [str(t["imgflip"]["id"])] + [str(v["id"]) for v in t["variants"]]:
                if tid in seen_id:
                    errs.append(f"Imgflip id {tid} is also in {seen_id[tid]}")
                seen_id[tid] = path.name
        if errs:
            problems.extend(f"{path.name}: {e}" for e in errs)
        else:
            templates.append(t)
    if check and problems:
        raise ValueError("catalog problems:\n  " + "\n  ".join(problems))
    templates.sort(key=lambda t: (t["name"].lower(), t["slug"]))
    return templates


def load_json(name, default):
    path = DATA / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_trending():
    """{'snapshots': [{'date': 'YYYY-MM-DD', 'ids': [...], 'captions': {id: n}}]} oldest first."""
    return load_json("trending.json", {"snapshots": []})


def load_registry():
    """Every template the Imgflip API has returned: id -> {name, url, width, height, box_count, captions, first_seen, last_seen}."""
    return load_json("imgflip.json", {})


def popularity(all_time_rank, weekly_rank):
    """0-5: a small ranking nudge for well-known templates (log scale, so only the top few get much)."""
    best = 0.0
    for rank in (all_time_rank, weekly_rank):
        if rank:
            best = max(best, 5 * (1 - math.log(rank) / math.log(600)))
    return round(max(0.0, best), 2)


def first_sentence(text):
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return m.group(1) if m else text
