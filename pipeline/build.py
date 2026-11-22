"""Build the static site into dist/.

    python3 pipeline/build.py            # full build
    SITE_URL=https://example.org python3 pipeline/build.py

Inputs: data/templates/*.json (the catalog), data/trending.json and data/imgflip.json (weekly Imgflip
snapshots written by pipeline/refresh.py), data/collections.json, data/moderation.json, tests/eval.json.
No network. The same inputs always give the same output apart from the build date.
"""
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog  # noqa: E402

ROOT = catalog.ROOT
SITE = ROOT / "site"
DIST = Path(os.environ.get("BUILD_DIR") or ROOT / "dist")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/") or "https://theguysaccount.github.io/meme-search-engine"
BASE = urlparse(SITE_URL).path.rstrip("/") + "/"
REPO_URL = "https://github.com/theguysaccount/meme-search-engine"
NAME = "Describe a Meme"
TAGLINE = "Describe a meme. Get its name."
EMBED_IMAGES = os.environ.get("EMBED_IMAGES", "1").strip() not in ("0", "false", "no", "off")
GOATCOUNTER_URL = os.environ.get("GOATCOUNTER_URL", "").strip()
SPONSOR_URL = os.environ.get("SPONSOR_URL", "").strip()
SPONSOR_LABEL = os.environ.get("SPONSOR_LABEL", "").strip()
GOOGLE_SITE_VERIFICATION = os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip()
TODAY = datetime.datetime.now(datetime.timezone.utc).date()
STALE_AFTER_DAYS = 21

e = html.escape


def url(path=""):
    """Site-relative link for a page path like 'meme/slug/'."""
    return BASE + path


def absolute(path=""):
    return SITE_URL + "/" + path


def asset(name, _cache={}):
    """Link to a file in site/assets with a content hash, so a deploy never serves a stale script."""
    if name not in _cache:
        digest = hashlib.sha256((SITE / "assets" / name).read_bytes()).hexdigest()[:10]
        _cache[name] = f"{BASE}assets/{name}?v={digest}"
    return _cache[name]


def jsonld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def json_script(data, id_):
    return f'<script type="application/json" id="{id_}">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def thumb_url(code):
    return f"https://i.imgflip.com/4/{code}.jpg"


def imgflip_page(tid):
    return f"https://imgflip.com/meme/{tid}"


def imgflip_generator(tid):
    return f"https://imgflip.com/memegenerator/{tid}"


def show_image(t):
    return EMBED_IMAGES and t.get("embed", True)


def thumb_html(t, href, size=112, external=False):
    """A small picture of the template, loaded from Imgflip, or a text tile when images are off."""
    attrs = ' target="_blank" rel="noopener"' if external else ""
    if show_image(t):
        return (f'<a class="thumb" href="{e(href)}" tabindex="-1" aria-hidden="true"{attrs}>'
                f'<img data-remote src="{thumb_url(t["imgflip"]["code"])}" alt="" loading="lazy" decoding="async" '
                f'width="{size}" height="{size}" referrerpolicy="strict-origin-when-cross-origin"></a>')
    return f'<a class="thumb none" href="{e(href)}" tabindex="-1" aria-hidden="true"{attrs}>Image on Imgflip</a>'


# --- page shell -----------------------------------------------------------------------------------

NAV = [("", "Search"), ("trending/", "Trending"), ("browse/", "Browse"), ("all/", "All templates"), ("api/", "API"), ("about/", "About")]


def shell(*, path, title, description, body, og_image="assets/og/home.png", head="", scripts="", body_class="", index=True, nav=True):
    canonical = absolute(path)
    robots = "" if index else '<meta name="robots" content="noindex,follow">\n'
    verification = f'<meta name="google-site-verification" content="{e(GOOGLE_SITE_VERIFICATION)}">\n' if GOOGLE_SITE_VERIFICATION and path == "" else ""
    analytics = (f'<script data-goatcounter="{e(GOATCOUNTER_URL)}" async src="https://gc.zgo.at/count.js"></script>\n'
                 if GOATCOUNTER_URL else "")
    current = ' aria-current="page"'
    links = "".join(f'<a href="{url(p)}"{current if p == path else ""}>{e(label)}</a>' for p, label in NAV)
    header = (f'<header class="site"><div class="wrap"><a class="brand" href="{url()}">Describe a <b>Meme</b></a>'
              f'<nav class="top" aria-label="Site">{links}</nav></div></header>') if nav else ""
    footer = (f'<footer class="site"><div class="wrap"><nav aria-label="Footer">'
              f'<a href="{url("about/")}">About and image policy</a><a href="{url("about/")}#takedown">Removal requests</a>'
              f'<a href="{REPO_URL}/issues/new/choose">Report a mistake</a><a href="{url("api/")}">Free JSON API</a>'
              f'<a href="{REPO_URL}">Source on GitHub</a></nav>'
              f'<p>Descriptions are written for this site and free to reuse (CC BY 4.0). Template images are not hosted here: '
              f'they load from <a href="https://imgflip.com/">Imgflip</a> and belong to their owners. '
              f'Not affiliated with Imgflip or with anyone pictured.</p></div></footer>') if nav else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
{robots}{verification}<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(absolute(og_image))}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffd60a">
<link rel="icon" href="{url('favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{asset('site.css')}">
<link rel="preconnect" href="https://i.imgflip.com" crossorigin>
{head}{analytics}</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
{header}
<main id="main"><div class="wrap">
{body}
</div></main>
{footer}
<div class="toast" id="toast" role="status" aria-live="polite"></div>
{scripts}
</body>
</html>
"""


def write(path, text):
    out = DIST / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def sponsor_box():
    if not SPONSOR_URL:
        return ""
    label = SPONSOR_LABEL or "Support this site"
    return (f'<aside class="box sponsor" data-sponsor><small>Sponsor</small>'
            f'<a href="{e(SPONSOR_URL)}" rel="sponsored noopener" target="_blank">{e(label)}</a></aside>')


# --- data assembly --------------------------------------------------------------------------------

def assemble():
    templates = catalog.load_templates()
    moderation = catalog.load_moderation()
    trending = catalog.load_trending()
    registry = catalog.load_registry()
    collections = catalog.load_json("collections.json", {"collections": []})["collections"]
    by_id = {}
    for t in templates:
        by_id[str(t["imgflip"]["id"])] = t
        for v in t["variants"]:
            by_id[str(v["id"])] = t
    snaps = trending["snapshots"]
    latest = snaps[-1] if snaps else None
    previous = None
    if latest:
        for s in reversed(snaps[:-1]):
            if (datetime.date.fromisoformat(latest["date"]) - datetime.date.fromisoformat(s["date"])).days >= 5:
                previous = s
                break
    blocked = set(moderation["blocked_ids"])
    rows = []          # this week's list, in Imgflip's order, without blocked templates
    weekly_rank = {}   # slug -> best rank this week
    omitted = 0
    if latest:
        prev_pos = {tid: i + 1 for i, tid in enumerate(previous["ids"])} if previous else {}
        seen_slugs = set()
        for i, tid in enumerate(latest["ids"]):
            tid = str(tid)
            reg = registry.get(tid, {})
            t = by_id.get(tid)
            if tid in blocked or (not t and catalog.blocked_name(reg.get("name", ""), moderation)):
                omitted += 1
                continue
            if t and t["slug"] in seen_slugs:
                continue   # a second version of a template already listed higher up
            if t:
                seen_slugs.add(t["slug"])
                weekly_rank.setdefault(t["slug"], i + 1)
            move = None
            if previous:
                move = "new" if tid not in prev_pos else prev_pos[tid] - (i + 1)
            rows.append({"rank": i + 1, "id": tid, "template": t, "name": t["name"] if t else reg.get("name", "Template " + tid),
                         "captions": latest.get("captions", {}).get(tid), "move": move,
                         "code": t["imgflip"]["code"] if t else _code(tid)})
    pending = [r for r in rows if not r["template"]]
    for t in templates:
        t["_weekly"] = weekly_rank.get(t["slug"])
        t["_popularity"] = catalog.popularity(t.get("rank_all_time"), t["_weekly"])
        reg = registry.get(str(t["imgflip"]["id"]), {})
        t["_captions"] = reg.get("captions")
        t["_boxes"] = t["imgflip"].get("boxes") or reg.get("box_count")
    related(templates)
    hubs = build_hubs(templates, collections)
    return {"templates": templates, "rows": rows, "pending": pending, "latest": latest, "previous": previous,
            "omitted": omitted, "hubs": hubs, "moderation": moderation}


def _code(tid):
    n, digits = int(tid), "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def related(templates):
    """Attach up to four similar templates to each: same source first, then shared tags and shape."""
    tagsets = {t["slug"]: set(t["tags"]) for t in templates}
    for t in templates:
        scored = []
        for o in templates:
            if o is t:
                continue
            score = 0
            if t["franchise"] and o["franchise"] == t["franchise"]:
                score += 4
            score += 1.5 * len(tagsets[t["slug"]] & tagsets[o["slug"]])
            if o["format"] == t["format"]:
                score += 1
            if o["kind"] == t["kind"]:
                score += 0.5
            if score >= 2.5:
                scored.append((-score, -o["_popularity"], o["name"], o))
        scored.sort(key=lambda x: x[:3])
        t["_related"] = [x[3] for x in scored[:4]]


def build_hubs(templates, collections):
    """Browse pages: curated collections, formats, and any source with enough templates to be worth a page."""
    hubs = []

    def tag_match(want, have):
        """A collection tag matches a template tag exactly, or as whole words inside it ("cat" in "angry cat")."""
        w = " " + want.lower() + " "
        return any(w in " " + h.lower() + " " for h in have)

    for c in collections:
        slugs = set(c.get("slugs", []))
        members = [t for t in templates if t["slug"] in slugs or any(tag_match(x, t["tags"]) for x in c.get("tags", []))
                   or (c.get("kinds") and t["kind"] in c["kinds"]) or (c.get("franchises") and t["franchise"] in c["franchises"])]
        if len(members) >= 5:
            hubs.append({"slug": c["slug"], "title": c["title"], "intro": c["intro"], "group": "Collections", "members": members})
    for key, (label, blurb) in catalog.FORMATS.items():
        members = [t for t in templates if t["format"] == key]
        if len(members) >= 5 and key != "other":
            hubs.append({"slug": "format-" + key, "title": f"{label} memes", "intro": blurb, "group": "By shape", "members": members})
    franchises = {}
    for t in templates:
        if t["franchise"]:
            franchises.setdefault(t["franchise"], []).append(t)
    for name, members in sorted(franchises.items()):
        if len(members) >= 4:
            hubs.append({"slug": "from-" + catalog.slugify(name), "title": f"{name} memes",
                         "intro": f"Meme templates that come from {name}, each with what it looks like and how it's used.",
                         "group": "By source", "members": members})
    seen = set()
    for h in hubs:
        if h["slug"] in seen:
            raise ValueError(f"duplicate browse page {h['slug']}")
        seen.add(h["slug"])
        h["members"].sort(key=lambda t: (-t["_popularity"], t["name"]))
    return hubs


# --- pages ----------------------------------------------------------------------------------------

def tile(t, extra=""):
    return (f'<li class="tile">{thumb_html(t, url("meme/" + t["slug"] + "/"), 120)}'
            f'<a class="name" href="{url("meme/" + t["slug"] + "/")}">{e(t["name"])}</a>{extra}</li>')


def move_html(move):
    if move is None:
        return ""
    if move == "new":
        return '<span class="badge new">new</span>'
    if move > 0:
        return f'<span class="up" title="up {move} since the last snapshot">▲ {move}</span>'
    if move < 0:
        return f'<span class="down" title="down {-move} since the last snapshot">▼ {-move}</span>'
    return '<span class="note" title="no change">–</span>'


def page_home(ctx):
    templates = ctx["templates"]
    examples = [q["q"] for q in ctx["selftest"]["queries"]][:5]
    chips = "".join(f'<li><button type="button" data-example="{e(q)}">{e(q)}</button></li>' for q in examples)
    top = [r for r in ctx["rows"] if r["template"]][:12]
    if top:
        tiles = "".join(tile(r["template"], f'<span class="rank">#{r["rank"]} this week</span>') for r in top)
        trending = (f'<h2>Trending templates this week</h2><ul class="grid">{tiles}</ul>'
                    f'<p class="note">From Imgflip\'s public list of the templates people captioned most in the last 30 days, '
                    f'read on {nice_date(ctx["latest"]["date"])}. <a href="{url("trending/")}">See the full list</a>.</p>')
    else:
        tiles = "".join(tile(t) for t in sorted(templates, key=lambda t: -t["_popularity"])[:12])
        trending = f'<h2>Popular templates</h2><ul class="grid">{tiles}</ul>'
    pills = "".join(f'<li><a href="{url("browse/" + h["slug"] + "/")}">{e(h["title"])} <small>{len(h["members"])}</small></a></li>'
                    for h in ctx["hubs"][:18])
    body = f"""<section class="hero">
<h1>Describe a meme.<br><span>Get its name.</span></h1>
<p class="lead">Type what you remember: who's in it, what they're doing, any words on it. We'll tell you what the meme is called and where to get the blank template.</p>
<form class="search" role="search" action="{url()}" method="get">
<label class="skip" for="q">Describe the meme</label>
<input type="search" id="q" name="q" placeholder="guy looking back at another girl" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" required>
<button type="submit">Find it</button>
</form>
<ul class="chips" aria-label="Example descriptions">{chips}</ul>
</section>
<section aria-label="Results">
<p id="status" role="status" aria-live="polite"></p>
<ol class="results"></ol>
<p><button class="quiet" type="button" data-share-search>Share this search</button></p>
<noscript><p class="empty">Search needs JavaScript. Without it you can still browse <a href="{url('all/')}">every template A to Z</a>.</p></noscript>
</section>
{sponsor_box()}
<section>{trending}</section>
<section><h2>Browse by kind</h2><ul class="pills">{pills}</ul>
<p class="note"><a href="{url('browse/')}">All collections</a> · <a href="{url('all/')}">All {len(templates)} templates A to Z</a></p></section>
<section><h2>How it works</h2>
<ol class="steps">
<li><strong>Describe it your way.</strong> "Dog sitting in a burning room", "two buttons and a sweating guy". No need for the right words: the search knows that a guy is a man and that staring is looking.</li>
<li><strong>Check the match.</strong> Every template has a plain description of what it shows and how people use it, written for this site and checked against the picture.</li>
<li><strong>Use it.</strong> Open the blank template on Imgflip to caption it, or copy a link to send to the friend who asked "what's that meme called?"</li>
</ol>
<p class="note">Nothing you type leaves your browser: the whole catalog is downloaded once and searched on your device. No account, no cookies.</p>
</section>"""
    data = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": absolute(),
            "description": "Find a meme by describing it.",
            "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": absolute("?q={search_term_string}")},
                                "query-input": "required name=search_term_string"}}
    cfg = {"base": BASE, "index": url("api/v1/search-index.json") + "?v=" + ctx["index_hash"], "images": EMBED_IMAGES, "embed": False}
    write("index.html", shell(
        path="", title="Describe a Meme: find any meme's name from a description",
        description=f"Remember a meme but not what it's called? Describe it in your own words and get its name, what it means and the blank template. {len(templates)} templates, free, no signup.",
        body=body, head=jsonld(data) + "\n",
        scripts=json_script(cfg, "cfg") + f'\n<script type="module" src="{asset("app.js")}"></script>'))


def page_template(t, ctx):
    im = t["imgflip"]
    tid = str(im["id"])
    page = imgflip_page(tid)
    full = f"https://i.imgflip.com/{im['image']}" if im.get("image") else thumb_url(im["code"])
    size = f' width="{im["width"]}" height="{im["height"]}"' if im.get("width") and im.get("height") else ""
    if show_image(t):
        frame = (f'<a class="frame" href="{page}" target="_blank" rel="noopener" data-out="imgflip_out">'
                 f'<img data-remote src="{full}" alt="{e(t["name"])} blank meme template: {e(catalog.first_sentence(t["look"]))}"{size} '
                 f'decoding="async" referrerpolicy="strict-origin-when-cross-origin"></a>')
        credit = f'Image served by <a href="{page}" target="_blank" rel="noopener">Imgflip</a>, not hosted on this site. It belongs to its owner.'
    else:
        frame = f'<a class="frame none" href="{page}" target="_blank" rel="noopener" style="padding:18px" data-out="imgflip_out">See the blank template on Imgflip ↗</a>'
        credit = "This site doesn't show the picture. The link opens it on Imgflip."
    facts = [catalog.KINDS[t["kind"]], catalog.FORMATS[t["format"]][0]]
    if t["panels"] > 1:
        facts.append(f'{t["panels"]} panels')
    if t["_boxes"]:
        facts.append(f'{t["_boxes"]} text boxes on Imgflip')
    if t["_weekly"]:
        facts.append(f'#{t["_weekly"]} on Imgflip this week')
    facts_html = "".join(f"<li>{e(f)}</li>" for f in facts)
    aka = f'<p class="aka">Also called: {e(", ".join(t["aka"]))}</p>' if t["aka"] else ""
    slots = "".join(f"<li>{e(s)}</li>" for s in t["slots"])
    examples = ""
    for ex in t["examples"]:
        rows = "".join(f"<dt>{e(_short_slot(s))}</dt><dd>{e(x)}</dd>" for s, x in zip(t["slots"], ex))
        examples += f'<div class="example"><dl>{rows}</dl></div>'
    printed = ""
    if t["text"]:
        printed = "<h2>Words printed on the template</h2><p>" + " · ".join(f"“{e(x)}”" for x in t["text"]) + "</p>"
    origin = f"<h2>Where it comes from</h2><p>{e(t['origin'])}</p>" if t["origin"] else ""
    says = "".join(f'<li><a href="{url()}?q={quote(d)}" rel="nofollow">{e(d)}</a></li>' for d in t["describe"])
    variants = ""
    if t["variants"]:
        items = ", ".join(f'<a href="{imgflip_page(v["id"])}" target="_blank" rel="noopener">{e(v["name"])}</a>' for v in t["variants"])
        variants = f'<p class="note">Other versions of this template on Imgflip: {items}.</p>'
    rel = ""
    if t["_related"]:
        rel = '<section class="related"><h2>Similar templates</h2><ul class="grid">' + "".join(tile(o) for o in t["_related"]) + "</ul></section>"
    hubs = [h for h in ctx["hubs"] if t in h["members"]]
    hub_links = ""
    if hubs:
        hub_links = '<ul class="pills">' + "".join(f'<li><a href="{url("browse/" + h["slug"] + "/")}">{e(h["title"])}</a></li>' for h in hubs[:6]) + "</ul>"
    here = absolute("meme/" + t["slug"] + "/")
    name_q = quote(t["name"] + " meme")
    body = f"""<p class="crumbs"><a href="{url()}">Search</a> › <a href="{url('all/')}">All templates</a> › {e(t["name"])}</p>
<article class="meme">
<figure>{frame}<figcaption>{credit}</figcaption></figure>
<div>
<h1>{e(t["name"])}</h1>
{aka}
<ul class="facts">{facts_html}</ul>
<h2>What it looks like</h2>
<p>{e(t["look"])}</p>
{printed}
<h2>How it's used</h2>
<p>{e(t["use"])}</p>
<ol class="slots">{slots}</ol>
<h2>Example</h2>
{examples}
{origin}
<h2>Get the template</h2>
<div class="cta">
<a class="button" href="{imgflip_generator(tid)}" target="_blank" rel="noopener" data-out="imgflip_out">Caption it on Imgflip ↗</a>
<a class="button quiet" href="{page}" target="_blank" rel="noopener" data-out="imgflip_out">Blank template ↗</a>
<button class="quiet" type="button" data-copy="{e(here)}">Copy link to this page</button>
<button class="quiet" type="button" data-share>Share</button>
</div>
<p class="note">More examples: <a href="https://knowyourmeme.com/search?q={quote(t["name"])}" target="_blank" rel="noopener">search Know Your Meme</a> ·
<a href="https://www.google.com/search?tbm=isch&amp;q={name_q}" target="_blank" rel="noopener">Google Images</a></p>
{variants}
<h2>How people describe it</h2>
<ul class="says">{says}</ul>
<p class="note">Not the one you meant? <a href="{url()}">Describe it another way</a>.</p>
{hub_links}
</div>
</article>
{rel}
{sponsor_box()}
<p class="note">Something wrong on this page? <a href="{REPO_URL}/issues/new?template=correction.yml&amp;title={quote('Correction: ' + t['name'])}">Tell us</a>.
Rights holder? See <a href="{url('about/')}#takedown">removal requests</a>.</p>"""
    desc = f"{catalog.first_sentence(t['look'])} What the {t['name']} meme means, how it's used, and a link to the blank template."
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "…"
    data = [{"@context": "https://schema.org", "@type": "WebPage", "name": f"{t['name']} meme", "url": here, "description": desc,
             "isPartOf": {"@type": "WebSite", "name": NAME, "url": absolute()},
             "about": {"@type": "Thing", "name": f"{t['name']} meme", "alternateName": t["aka"], "description": t["look"]},
             "dateModified": t.get("reviewed", t["added"])},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": NAME, "item": absolute()},
                {"@type": "ListItem", "position": 2, "name": "All templates", "item": absolute("all/")},
                {"@type": "ListItem", "position": 3, "name": t["name"], "item": here}]}]
    write(f"meme/{t['slug']}/index.html", shell(
        path=f"meme/{t['slug']}/", title=f"{t['name']} meme: what it's called, what it means, blank template",
        description=desc, body=body, og_image=f"assets/og/{t['slug']}.png" if ctx["og_cards"] else "assets/og/home.png",
        head="".join(jsonld(d) + "\n" for d in data),
        scripts=f'<script type="module" src="{asset("page.js")}"></script>'))


def _short_slot(slot):
    s = re.sub(r"\s*\(.*?\)", "", slot).strip()
    return s[:1].upper() + s[1:]


def page_trending(ctx):
    latest, previous = ctx["latest"], ctx["previous"]
    if not latest:
        body = "<h1>Trending meme templates</h1><p>No snapshot yet. The first weekly pull fills this page.</p>"
    else:
        trs = ""
        for r in ctx["rows"]:
            t = r["template"]
            if t:
                name = f'<a href="{url("meme/" + t["slug"] + "/")}">{e(t["name"])}</a><br><span class="note">{e(catalog.first_sentence(t["look"]))}</span>'
            else:
                name = (f'<a href="{imgflip_page(r["id"])}" target="_blank" rel="noopener">{e(r["name"])} ↗</a> '
                        f'<span class="badge new">not described yet</span>')
            caps = f'{r["captions"]:,}' if isinstance(r["captions"], int) else ""
            trs += f'<tr><td class="num">{r["rank"]}</td><td>{move_html(r["move"])}</td><td>{name}</td><td class="num">{caps}</td></tr>'
        compare = (f"Arrows compare with the snapshot of {nice_date(previous['date'])}." if previous
                   else "Arrows appear once there is an earlier snapshot to compare with.")
        omitted = (f" {ctx['omitted']} template{'s are' if ctx['omitted'] != 1 else ' is'} left out under "
                   f"<a href=\"{url('about/')}#rules\">our content rules</a>." if ctx["omitted"] else "")
        age = (TODAY - datetime.date.fromisoformat(latest["date"])).days
        stale = (f'<p class="box"><strong>This list is {age} days old.</strong> The weekly update has not run; '
                 f'ranks below may be out of date.</p>' if age > STALE_AFTER_DAYS else "")
        body = f"""<h1>Trending meme templates this week</h1>
<p>The templates people captioned most on Imgflip over the last 30 days, in Imgflip's order, read on <time datetime="{latest['date']}">{nice_date(latest['date'])}</time>. {compare}{omitted}</p>
{stale}
<div class="scroll"><table>
<thead><tr><th class="num">#</th><th>Move</th><th>Template</th><th class="num">All-time captions</th></tr></thead>
<tbody>{trs}</tbody></table></div>
<p class="note">Source: <a href="https://imgflip.com/api" target="_blank" rel="noopener">Imgflip's public API</a>. Rank is Imgflip's; "all-time captions" is its rounded estimate.
This page refreshes itself every week. The same data is in <a href="{url('api/v1/trending.json')}">trending.json</a>.</p>"""
    write("trending/index.html", shell(
        path="trending/", title="Trending meme templates this week, with names and meanings",
        description="The 100 most-used meme templates right now, each with its name, what it looks like and how it's used. Updated weekly from Imgflip's public data.",
        body=body, scripts=f'<script type="module" src="{asset("page.js")}"></script>'))


def page_browse(ctx):
    groups = {}
    for h in ctx["hubs"]:
        groups.setdefault(h["group"], []).append(h)
    sections = ""
    for group in ("Collections", "By shape", "By source"):
        if group not in groups:
            continue
        pills = "".join(f'<li><a href="{url("browse/" + h["slug"] + "/")}">{e(h["title"])} <small>{len(h["members"])}</small></a></li>' for h in groups[group])
        sections += f'<h2>{e(group)}</h2><ul class="pills">{pills}</ul>'
    body = f"""<h1>Browse meme templates</h1>
<p>Don't remember enough to describe it? Narrow it down by what kind of meme it is or where it comes from.</p>
{sections}
<p class="note">Or see <a href="{url('all/')}">every template A to Z</a>.</p>"""
    write("browse/index.html", shell(path="browse/", title="Browse meme templates by kind, shape and source",
                                     description="Meme templates grouped by what they show, how they're laid out and the films, shows and games they come from.",
                                     body=body))
    for h in ctx["hubs"]:
        tiles = "".join(tile(t, f'<span class="rank">{e(_clip(catalog.first_sentence(t["look"]), 90))}</span>') for t in h["members"])
        here = absolute(f"browse/{h['slug']}/")
        data = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h["title"], "url": here, "description": h["intro"],
                "mainEntity": {"@type": "ItemList", "numberOfItems": len(h["members"]), "itemListElement": [
                    {"@type": "ListItem", "position": i + 1, "url": absolute(f"meme/{t['slug']}/"), "name": t["name"]}
                    for i, t in enumerate(h["members"])]}}
        body = f"""<p class="crumbs"><a href="{url()}">Search</a> › <a href="{url('browse/')}">Browse</a> › {e(h["title"])}</p>
<h1>{e(h["title"])}</h1>
<p>{e(h["intro"])}</p>
<ul class="grid">{tiles}</ul>
<p class="note">{len(h["members"])} templates. Still not finding it? <a href="{url()}">Describe it</a>.</p>"""
        write(f"browse/{h['slug']}/index.html", shell(
            path=f"browse/{h['slug']}/", title=f"{h['title']}: names, meanings and blank templates",
            description=_clip(h["intro"] + f" {len(h['members'])} templates with names, descriptions and links to the blanks.", 300),
            body=body, head=jsonld(data) + "\n", scripts=f'<script type="module" src="{asset("page.js")}"></script>'))


def _clip(text, n):
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def page_all(ctx):
    letters = {}
    for t in ctx["templates"]:
        first = t["name"][0].upper()
        letters.setdefault(first if first.isalpha() else "#", []).append(t)
    order = sorted(letters, key=lambda c: (c != "#", c))
    nav = "".join(f'<li><a href="#l-{"num" if c == "#" else c}">{c}</a></li>' for c in order)
    out = ""
    for c in order:
        items = "".join(f'<li><a href="{url("meme/" + t["slug"] + "/")}">{e(t["name"])}</a>'
                        f'<small>{e(_clip(catalog.first_sentence(t["look"]), 130))}</small></li>' for t in letters[c])
        out += f'<h2 id="l-{"num" if c == "#" else c}">{c}</h2><ul class="az">{items}</ul>'
    body = f"""<h1>All meme templates, A to Z</h1>
<p>{len(ctx["templates"])} templates, each with a plain description. Know roughly what it looks like? <a href="{url()}">Describe it</a> instead.</p>
<ul class="letters">{nav}</ul>
{out}"""
    write("all/index.html", shell(path="all/", title="All meme templates A to Z, with what each one looks like",
                                  description=f"An A to Z list of {len(ctx['templates'])} popular meme templates. Each has its name, a one-line description, and a page with its meaning and blank template.",
                                  body=body))


def page_api(ctx):
    sample = ctx["templates"][0]["slug"] if ctx["templates"] else "example"
    base = absolute("api/v1/")
    embed_code = f'<iframe src="{absolute("embed/")}" title="Describe a meme, get its name" width="100%" height="420" style="border:1px solid #ddd;border-radius:12px" loading="lazy"></iframe>'
    body = f"""<h1>Free meme template API and widget</h1>
<p>Everything on this site is also a set of plain JSON files. No key, no signup, no rate limit beyond GitHub Pages' own, and
<code>Access-Control-Allow-Origin: *</code> so you can call it from a browser. The files are rebuilt on every deploy and at least weekly.</p>
<h2>Endpoints</h2>
<div class="scroll"><table>
<thead><tr><th>File</th><th>What's in it</th></tr></thead>
<tbody>
<tr><td><a href="{url('api/v1/templates.json')}"><code>templates.json</code></a></td><td>Every described template: name, other names, what it looks like, how it's used, text slots, examples, tags, source, Imgflip id and links.</td></tr>
<tr><td><a href="{url('api/v1/templates/' + sample + '.json')}"><code>templates/&lt;slug&gt;.json</code></a></td><td>One template.</td></tr>
<tr><td><a href="{url('api/v1/search-index.json')}"><code>search-index.json</code></a></td><td>The compact file this site's own search runs on.</td></tr>
<tr><td><a href="{url('api/v1/trending.json')}"><code>trending.json</code></a></td><td>This week's most-captioned templates on Imgflip, in order, with movement since the previous snapshot.</td></tr>
<tr><td><a href="{url('api/v1/meta.json')}"><code>meta.json</code></a></td><td>Counts and the dates the data was built and last refreshed.</td></tr>
</tbody></table></div>
<h2>Example</h2>
<pre><code>curl {base}templates/{sample}.json

// in a browser
const all = await (await fetch("{base}templates.json")).json();
const withCats = all.templates.filter(t =&gt; t.tags.includes("cat"));</code></pre>
<h2>Search in your own app</h2>
<p>The ranking code is one dependency-free ES module. Load it with the index and search on the device:</p>
<pre><code>import {{ buildIndex, search }} from "{absolute('assets/core.js')}";
const data = await (await fetch("{base}templates.json")).json();
const index = buildIndex(data.templates);
search(index, "guy looking back at another girl")[0].record.name;</code></pre>
<h2>Embed the search box</h2>
<p>Paste this where you want a "what's that meme called?" box. Results open on this site in a new tab.</p>
<pre><code>{e(embed_code)}</code></pre>
<p><button class="quiet" type="button" data-copy="{e(embed_code)}" data-done="Embed code copied" data-event="copy_embed">Copy embed code</button></p>
<h2>Terms</h2>
<ul>
<li>Descriptions, tags and examples are written for this project and licensed <a href="https://creativecommons.org/licenses/by/4.0/" rel="license noopener" target="_blank">CC BY 4.0</a>: use them anywhere, with a link back to this site.</li>
<li>Template names, ids and popularity come from <a href="https://imgflip.com/api" target="_blank" rel="noopener">Imgflip's public API</a>. Images are not part of this API: link to Imgflip for those and follow its terms.</li>
<li>Version 1 files only gain fields; a breaking change would get a new <code>/v2/</code> path.</li>
</ul>
{sponsor_box()}"""
    write("api/index.html", shell(path="api/", title="Free meme template JSON API and embeddable meme finder",
                                  description="A free, keyless JSON API of popular meme templates with plain-language descriptions, tags and weekly trending ranks, plus an embeddable describe-a-meme search box.",
                                  body=body, scripts=f'<script type="module" src="{asset("page.js")}"></script>'))


def page_embed(ctx):
    body = f"""<form class="search" role="search" action="{url()}" method="get" target="_blank">
<label class="skip" for="q">Describe the meme</label>
<input type="search" id="q" name="q" placeholder="Describe a meme: guy looking back at another girl" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" required>
<button type="submit">Find it</button>
</form>
<p id="status" role="status" aria-live="polite"></p>
<ol class="results"></ol>
<p class="by">Meme finder by <a href="{absolute()}" target="_blank" rel="noopener">Describe a Meme</a> · <a href="{absolute('api/')}" target="_blank" rel="noopener">add it to your site</a></p>"""
    cfg = {"base": BASE, "index": url("api/v1/search-index.json") + "?v=" + ctx["index_hash"], "images": EMBED_IMAGES, "embed": True}
    write("embed/index.html", shell(path="embed/", title="Describe a Meme: embeddable meme finder", description="Embeddable describe-a-meme search box.",
                                    body=body, body_class="embed", index=False, nav=False,
                                    scripts=json_script(cfg, "cfg") + f'\n<script type="module" src="{asset("app.js")}"></script>'))


def page_about(ctx):
    n = len(ctx["templates"])
    body = f"""<h1>About Describe a Meme</h1>
<p>You remember the picture: a guy looking back at another girl, a dog in a burning room. You don't remember what it's called, so you can't search for it. This site fixes that. Describe the meme in your own words and it gives you the name, what it means, and a link to the blank template.</p>
<h2>How the search works</h2>
<p>Each of the {n} templates has a description written for this site and checked against the picture: what it shows, the words printed on it, how people use it, and the ways someone might describe it without knowing its name. Your words are matched against all of that in your browser, with allowance for synonyms (guy and man, staring and looking), word forms and typos. Nothing you type is sent anywhere.</p>
<p>The list of templates and their popularity comes from <a href="https://imgflip.com/api" target="_blank" rel="noopener">Imgflip's public API</a> and is refreshed every week. A template that is newly popular shows up on the <a href="{url('trending/')}">trending page</a> straight away and gets its full description later.</p>
<h2 id="images">Image policy</h2>
<p>This site hosts no meme images. Where a picture appears, your browser loads it directly from Imgflip's servers, with a link back to the template's page on Imgflip, as Imgflip's terms ask. The pictures belong to their photographers, studios and artists. If Imgflip removes an image, it disappears here too.</p>
<h2 id="takedown">Removal requests</h2>
<p>If you own the rights to an image, or you are pictured in one, and you want this site to stop showing or describing it, <a href="{REPO_URL}/issues/new?template=removal.yml">open a removal request</a>. Say which page and who you are. The page is taken down or switched to text only, no argument needed. To have the image itself removed from where it is hosted, use <a href="https://imgflip.com/image-removal-request" target="_blank" rel="noopener">Imgflip's own removal form</a>.</p>
<h2 id="rules">Content rules</h2>
<ul>
<li>No templates whose joke is hate toward a group, no slurs or hate symbols, nothing sexual, nothing that promotes self-harm or hard drugs, and no real tragedies or real violence played for laughs.</li>
<li>Ordinary people who became memes are described by the meme's name only. Their real names are not published here.</li>
<li>Descriptions say what is in the picture and how the format is used. They don't judge anyone in it.</li>
</ul>
<p>Templates that break these rules are left out, including from the trending list, even when they are popular.</p>
<h2>Mistakes</h2>
<p>Descriptions are written with AI assistance and checked against the pictures, and they can still be wrong. <a href="{REPO_URL}/issues/new?template=correction.yml">Report a mistake</a> and it gets fixed.</p>
<h2>Privacy</h2>
<p>No accounts, no cookies, no ads. The search runs on your device. Images come from Imgflip, so Imgflip sees your browser request them, as with any embedded image. {"Visits are counted with GoatCounter, which stores no personal data." if GOATCOUNTER_URL else "The site does not count visits."}</p>
<h2>Reuse</h2>
<p>The descriptions are free to reuse with a link back (CC BY 4.0), and the whole catalog is a <a href="{url('api/')}">free JSON API</a>. The code is <a href="{REPO_URL}">open source</a>.</p>"""
    write("about/index.html", shell(path="about/", title="About Describe a Meme: how it works, image policy, removal requests",
                                    description="How the describe-a-meme search works, where the data comes from, why no images are hosted here, and how to ask for a page to be removed or corrected.",
                                    body=body))


def page_404(ctx):
    body = f"""<h1>That page isn't here</h1>
<p>The template may have been renamed or removed. Describe the meme and we'll find it:</p>
<form class="search" role="search" action="{url()}" method="get">
<label class="skip" for="q">Describe the meme</label>
<input type="search" id="q" name="q" placeholder="guy looking back at another girl" autocomplete="off" required>
<button type="submit">Find it</button>
</form>
<p id="status" role="status" aria-live="polite"></p>
<ol class="results"></ol>
<p><a href="{url('all/')}">All templates A to Z</a></p>"""
    cfg = {"base": BASE, "index": url("api/v1/search-index.json") + "?v=" + ctx["index_hash"], "images": EMBED_IMAGES, "embed": False}
    write("404.html", shell(path="404.html", title="Page not found | Describe a Meme", description="Page not found.", body=body, index=False,
                            scripts=json_script(cfg, "cfg") + f'\n<script type="module" src="{asset("app.js")}"></script>'))


# --- data files -----------------------------------------------------------------------------------

def public_template(t):
    im = t["imgflip"]
    return {
        "slug": t["slug"], "name": t["name"], "aka": t["aka"], "look": t["look"], "text": t["text"], "use": t["use"],
        "slots": t["slots"], "examples": t["examples"], "describe": t["describe"], "tags": t["tags"], "kind": t["kind"],
        "format": t["format"], "panels": t["panels"], "franchise": t["franchise"], "origin": t["origin"],
        "page": absolute(f"meme/{t['slug']}/"),
        "imgflip": {"id": str(im["id"]), "page": imgflip_page(im["id"]), "caption": imgflip_generator(im["id"]),
                    "boxes": t["_boxes"], "all_time_captions": t["_captions"], "rank_this_week": t["_weekly"],
                    "other_versions": [{"id": str(v["id"]), "name": v["name"]} for v in t["variants"]]},
        "popularity": t["_popularity"], "added": t["added"], "reviewed": t.get("reviewed", t["added"]),
    }


def index_record(t):
    rec = {"s": t["slug"], "n": t["name"], "id": str(t["imgflip"]["id"]), "d": t["describe"], "l": t["look"], "g": t["tags"],
           "u": t["use"], "p": t["_popularity"]}
    aka = t["aka"] + [v["name"] for v in t["variants"] if v["name"].lower() not in {a.lower() for a in t["aka"] + [t["name"]]}]
    if aka:
        rec["a"] = aka
    if t["text"]:
        rec["t"] = t["text"]
    if t["franchise"]:
        rec["f"] = t["franchise"]
    if t["origin"]:
        rec["o"] = t["origin"]
    if show_image(t):
        rec["i"] = t["imgflip"]["code"]
    return rec


def write_data(ctx):
    templates = ctx["templates"]
    licence = {"descriptions": "CC BY 4.0", "attribution": absolute(), "names_and_popularity": "Imgflip public API (https://imgflip.com/api)"}
    write("api/v1/templates.json", json.dumps({"generated": TODAY.isoformat(), "license": licence, "count": len(templates),
                                               "templates": [public_template(t) for t in templates]}, ensure_ascii=False, separators=(",", ":")))
    for t in templates:
        write(f"api/v1/templates/{t['slug']}.json", json.dumps(public_template(t), ensure_ascii=False, indent=1))
    records = [index_record(t) for t in templates]
    for r in ctx["pending"]:
        # Not reviewed yet: name and link only, never a picture.
        records.append({"n": r["name"], "id": r["id"], "x": 1, "p": catalog.popularity(None, r["rank"])})
    index_json = json.dumps({"generated": TODAY.isoformat(), "templates": records}, ensure_ascii=False, separators=(",", ":"))
    ctx["index_hash"] = hashlib.sha256(index_json.encode()).hexdigest()[:10]
    write("api/v1/search-index.json", index_json)
    latest = ctx["latest"]
    rows = [{"rank": r["rank"], "imgflip_id": r["id"], "name": r["name"], "slug": r["template"]["slug"] if r["template"] else None,
             "page": absolute(f"meme/{r['template']['slug']}/") if r["template"] else None,
             "all_time_captions": r["captions"], "move": r["move"]} for r in ctx["rows"]]
    write("api/v1/trending.json", json.dumps({
        "date": latest["date"] if latest else None, "compared_with": ctx["previous"]["date"] if ctx["previous"] else None,
        "source": "https://api.imgflip.com/get_memes", "omitted_under_content_rules": ctx["omitted"], "templates": rows},
        ensure_ascii=False, indent=1))
    write("api/v1/meta.json", json.dumps({
        "name": NAME, "url": absolute(), "built": TODAY.isoformat(), "templates": len(templates), "pending": len(ctx["pending"]),
        "trending_date": latest["date"] if latest else None, "images_embedded": EMBED_IMAGES, "selftest": ctx["selftest"]},
        ensure_ascii=False, indent=1))


def pick_selftest(templates):
    """A few known-good description/template pairs for the in-browser self-test and the example chips.

    Taken from tests/eval.json (queries written without looking at the catalog text, keyed by Imgflip id)
    and kept only when the template is still in the catalog, so removing or renaming a template never
    breaks the self-test.
    """
    path = ROOT / "tests" / "eval.json"
    slug_of = {}
    for t in templates:
        slug_of[str(t["imgflip"]["id"])] = t["slug"]
        for v in t["variants"]:
            slug_of[str(v["id"])] = t["slug"]
    queries, typo = [], None
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("showcase", []):
            if str(item["id"]) in slug_of:
                queries.append({"q": item["q"], "slug": slug_of[str(item["id"])]})
        t = data.get("typo")
        if t and str(t["id"]) in slug_of:
            typo = {"q": t["q"], "slug": slug_of[str(t["id"])]}
    return {"queries": queries[:6], "typo": typo}


def write_static(ctx):
    shutil.copytree(SITE / "assets", DIST / "assets", dirs_exist_ok=True)
    shutil.copy(SITE / "favicon.svg", DIST / "favicon.svg")
    key = (SITE / "indexnow-key.txt").read_text().strip()
    write(f"{key}.txt", key)
    pages = [""] + [f"meme/{t['slug']}/" for t in ctx["templates"]] + ["trending/", "browse/"] + \
            [f"browse/{h['slug']}/" for h in ctx["hubs"]] + ["all/", "api/", "about/"]
    lastmod = {f"meme/{t['slug']}/": t.get("reviewed", t["added"]) for t in ctx["templates"]}
    fresh = ctx["latest"]["date"] if ctx["latest"] else TODAY.isoformat()
    items = "".join(f"<url><loc>{e(absolute(p))}</loc><lastmod>{lastmod.get(p, fresh)}</lastmod></url>\n" for p in pages)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: {BASE}embed/\n\nSitemap: {absolute('sitemap.xml')}\n")
    write("urls.txt", "\n".join(absolute(p) for p in pages) + "\n")
    write(".nojekyll", "")


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    ctx = assemble()
    ctx["selftest"] = pick_selftest(ctx["templates"])
    write_data(ctx)
    write_static(ctx)
    ctx["og_cards"] = False
    try:
        if os.environ.get("SKIP_OG"):
            raise ImportError("SKIP_OG is set")
        import og
        ctx["og_cards"] = og.render_all(ctx["templates"], DIST / "assets" / "og", SITE_URL)
    except ImportError as err:
        if os.environ.get("REQUIRE_OG"):
            raise SystemExit(f"share cards are required but Pillow is missing: {err}")
        print(f"note: per-template share cards skipped ({err}); pages use the default card")
    page_home(ctx)
    for t in ctx["templates"]:
        page_template(t, ctx)
    page_trending(ctx)
    page_browse(ctx)
    page_all(ctx)
    page_api(ctx)
    page_embed(ctx)
    page_about(ctx)
    page_404(ctx)
    n = sum(1 for _ in DIST.rglob("*.html"))
    print(f"built {n} pages: {len(ctx['templates'])} templates, {len(ctx['hubs'])} browse pages, "
          f"{len(ctx['rows'])} trending rows ({len(ctx['pending'])} not described yet), site {SITE_URL}")
    return ctx


if __name__ == "__main__":
    build()
