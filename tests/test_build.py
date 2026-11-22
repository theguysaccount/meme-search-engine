"""Build the whole site into a temporary folder (with temporary trending data) and check what comes out."""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://example.test/memes"
TODAY = datetime.datetime.now(datetime.timezone.utc).date()


def build(data_dir, out_dir, **env):
    e = dict(os.environ, BUILD_DIR=str(out_dir), MEME_DATA_DIR=str(data_dir), SITE_URL=SITE_URL, SKIP_OG="1")
    e.pop("GOATCOUNTER_URL", None)
    e.pop("SPONSOR_URL", None)
    e.update(env)
    r = subprocess.run([sys.executable, str(ROOT / "pipeline" / "build.py")], env=e, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r.stdout


def fixture_data(tmp, snapshot_dates):
    data = Path(tmp) / "data"
    shutil.copytree(ROOT / "data", data)
    templates = [json.loads(p.read_text()) for p in sorted((data / "templates").glob("*.json"))]
    blocked = sorted(json.loads((data / "moderation.json").read_text())["blocked_ids"])
    ids = [str(t["imgflip"]["id"]) for t in templates[:30]] + ["999999991"] + blocked[:1]
    registry = {tid: {"name": f"Template {tid}", "url": f"https://i.imgflip.com/x{tid}.jpg", "width": 500, "height": 500,
                      "box_count": 2, "captions": 1000, "first_seen": snapshot_dates[0] if snapshot_dates else TODAY.isoformat(),
                      "last_seen": TODAY.isoformat()} for tid in ids}
    registry["999999991"]["name"] = "Brand New Format"
    snaps = []
    for i, d in enumerate(snapshot_dates):
        order = ids if i % 2 == 0 else list(reversed(ids))
        snaps.append({"date": d, "ids": order, "captions": {tid: 1000 for tid in order}})
    (data / "imgflip.json").write_text(json.dumps(registry))
    (data / "trending.json").write_text(json.dumps({"snapshots": snaps}))
    return data, templates, blocked


class FreshBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        dates = [(TODAY - datetime.timedelta(days=7)).isoformat(), TODAY.isoformat()]
        cls.data, cls.templates, cls.blocked = fixture_data(cls.tmp, dates)
        # One template switched to text only, as a removal request would.
        cls.text_only = cls.templates[1]
        path = cls.data / "templates" / f"{cls.text_only['slug']}.json"
        t = json.loads(path.read_text())
        t["embed"] = False
        path.write_text(json.dumps(t))
        cls.dist = Path(cls.tmp) / "dist"
        cls.log = build(cls.data, cls.dist)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def read(self, rel):
        return (self.dist / rel).read_text(encoding="utf-8")

    def test_every_template_has_a_page_and_json(self):
        for t in self.templates:
            page = self.read(f"meme/{t['slug']}/index.html")
            self.assertEqual(page.count("<h1"), 1, t["slug"])
            self.assertIn(f'<link rel="canonical" href="{SITE_URL}/meme/{t["slug"]}/">', page)
            self.assertIn(f'https://imgflip.com/meme/{t["imgflip"]["id"]}', page, "every page links back to Imgflip")
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
                json.loads(block)
            json.loads(self.read(f"api/v1/templates/{t['slug']}.json"))

    def test_sitemap_lists_every_page_once_with_matching_canonicals(self):
        urls = re.findall(r"<loc>([^<]+)</loc>", self.read("sitemap.xml"))
        self.assertEqual(len(urls), len(set(urls)))
        for t in self.templates:
            self.assertIn(f"{SITE_URL}/meme/{t['slug']}/", urls)
        for u in urls:
            rel = u[len(SITE_URL) + 1:]
            page = self.read((rel or "") + "index.html")
            self.assertIn(f'<link rel="canonical" href="{u}">', page, u)
        self.assertIn(f"Sitemap: {SITE_URL}/sitemap.xml", self.read("robots.txt"))

    def test_no_meme_images_are_hosted(self):
        for f in self.dist.rglob("*"):
            if f.is_file():
                ext = f.suffix.lower()
                self.assertNotIn(ext, {".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp"}, str(f))
                if ext == ".png":
                    self.assertEqual(f.parent.name, "og", f"only text share cards may be PNGs: {f}")

    def test_text_only_template_shows_no_picture(self):
        page = self.read(f"meme/{self.text_only['slug']}/index.html")
        code = self.text_only["imgflip"]["code"]
        self.assertNotIn(f"i.imgflip.com/{code}.", page)
        self.assertNotIn(f"i.imgflip.com/4/{code}.", page)
        self.assertIn("doesn't show the picture", page)
        index = json.loads(self.read("api/v1/search-index.json"))
        rec = next(r for r in index["templates"] if r.get("s") == self.text_only["slug"])
        self.assertNotIn("i", rec)

    def test_trending_hides_blocked_and_flags_new_templates(self):
        trending = json.loads(self.read("api/v1/trending.json"))
        ids = [r["imgflip_id"] for r in trending["templates"]]
        for b in self.blocked:
            self.assertNotIn(b, ids)
        new = next(r for r in trending["templates"] if r["imgflip_id"] == "999999991")
        self.assertIsNone(new["slug"])
        self.assertEqual(trending["omitted_under_content_rules"], 1 if self.blocked else 0)
        page = self.read("trending/index.html")
        self.assertIn("Brand New Format", page)
        self.assertIn("not described yet", page)
        self.assertNotIn("days old.</strong>", page)
        index = json.loads(self.read("api/v1/search-index.json"))
        pending = [r for r in index["templates"] if r.get("x")]
        self.assertTrue(pending)
        for r in pending:
            self.assertNotIn("i", r, "unreviewed templates never get a picture")

    def test_counts_agree(self):
        meta = json.loads(self.read("api/v1/meta.json"))
        templates = json.loads(self.read("api/v1/templates.json"))
        self.assertEqual(meta["templates"], len(self.templates))
        self.assertEqual(templates["count"], len(self.templates))
        self.assertEqual(meta["trending_date"], TODAY.isoformat())

    def test_home_and_embed(self):
        home = self.read("index.html")
        self.assertIn('"@type": "WebSite"', home)
        self.assertIn("SearchAction", home)
        cfg = json.loads(re.search(r'<script type="application/json" id="cfg">(.*?)</script>', home, re.S).group(1))
        self.assertTrue(cfg["index"].startswith("/memes/api/v1/search-index.json?v="))
        embed = self.read("embed/index.html")
        self.assertIn('name="robots" content="noindex', embed)
        self.assertIn('"embed": true', embed)

    def test_no_money_or_analytics_without_keys(self):
        for rel in ("index.html", f"meme/{self.templates[0]['slug']}/index.html"):
            page = self.read(rel)
            self.assertNotIn("goatcounter", page)
            self.assertNotIn("data-sponsor", page)


class KeysAndStaleData(unittest.TestCase):
    def test_sponsor_and_analytics_appear_when_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, templates, _ = fixture_data(tmp, [TODAY.isoformat()])
            build(data, Path(tmp) / "dist", SPONSOR_URL="https://sponsor.example/", SPONSOR_LABEL="Sponsored by Example",
                  GOATCOUNTER_URL="https://example.goatcounter.com/count")
            page = (Path(tmp) / "dist" / "meme" / templates[0]["slug"] / "index.html").read_text()
            self.assertIn('href="https://sponsor.example/" rel="sponsored noopener"', page)
            self.assertIn('data-goatcounter="https://example.goatcounter.com/count"', page)

    def test_stale_and_missing_trending_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = (TODAY - datetime.timedelta(days=40)).isoformat()
            data, _, _ = fixture_data(tmp, [old])
            build(data, Path(tmp) / "dist")
            page = (Path(tmp) / "dist" / "trending" / "index.html").read_text()
            self.assertIn("40 days old", page)
        with tempfile.TemporaryDirectory() as tmp:
            data, _, _ = fixture_data(tmp, [])
            build(data, Path(tmp) / "dist")
            self.assertIn("No snapshot yet", (Path(tmp) / "dist" / "trending" / "index.html").read_text())
            meta = json.loads((Path(tmp) / "dist" / "api" / "v1" / "meta.json").read_text())
            self.assertIsNone(meta["trending_date"])

    def test_images_can_be_switched_off_site_wide(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, templates, _ = fixture_data(tmp, [TODAY.isoformat()])
            build(data, Path(tmp) / "dist", EMBED_IMAGES="0")
            for f in (Path(tmp) / "dist").rglob("*.html"):
                self.assertNotIn("i.imgflip.com/", f.read_text().replace('rel="preconnect" href="https://i.imgflip.com"', ""), str(f))


if __name__ == "__main__":
    unittest.main()
