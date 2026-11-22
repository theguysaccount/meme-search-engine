import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import catalog  # noqa: E402


class Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = catalog.load_templates()   # raises with every problem listed
        cls.moderation = catalog.load_moderation()

    def test_catalog_is_not_empty(self):
        self.assertGreaterEqual(len(self.templates), 20, "the catalog looks wiped")

    def test_nothing_blocked_is_published(self):
        blocked = set(self.moderation["blocked_ids"])
        for t in self.templates:
            ids = {str(t["imgflip"]["id"])} | {str(v["id"]) for v in t["variants"]}
            self.assertFalse(ids & blocked, t["slug"])

    def test_examples_fit_their_slots(self):
        for t in self.templates:
            for ex in t["examples"]:
                self.assertEqual(len(ex), len(t["slots"]), t["slug"])

    def test_validator_catches_problems(self):
        good = copy.deepcopy(self.templates[0])
        self.assertEqual(catalog.validate_template(good, self.moderation), [])
        bad = copy.deepcopy(good)
        bad["imgflip"]["code"] = "zzzz"
        self.assertTrue(catalog.validate_template(bad, self.moderation))
        bad = copy.deepcopy(good)
        bad["look"] = "too short"
        self.assertTrue(catalog.validate_template(bad, self.moderation))
        bad = copy.deepcopy(good)
        bad["use"] = bad["use"] + " See https://example.com"
        self.assertTrue(catalog.validate_template(bad, self.moderation))
        bad = copy.deepcopy(good)
        bad["describe"] = bad["describe"] + ["a phrase with " + self.moderation["never_terms"][0]]
        self.assertTrue(catalog.validate_template(bad, self.moderation))

    def test_eval_set_points_at_real_templates(self):
        data = json.loads((catalog.ROOT / "tests" / "eval.json").read_text(encoding="utf-8"))
        ids = set()
        for t in self.templates:
            ids.add(str(t["imgflip"]["id"]))
            ids.update(str(v["id"]) for v in t["variants"])
        known = [q for q in data["queries"] if q["id"] in ids]
        # Most eval targets are popular templates; if most vanish the eval stops meaning anything.
        self.assertGreaterEqual(len(known), len(data["queries"]) * 0.6)


if __name__ == "__main__":
    unittest.main()
