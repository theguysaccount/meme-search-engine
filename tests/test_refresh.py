import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import refresh  # noqa: E402


def payload(n=60, start=1000):
    return {"success": True, "data": {"memes": [
        {"id": str(start + i), "name": f"Template {i}", "url": f"https://i.imgflip.com/abc{i}.jpg", "width": 500, "height": 400,
         "box_count": 2, "captions": 1000 - i} for i in range(n)]}}


class Validate(unittest.TestCase):
    def test_accepts_the_documented_shape(self):
        memes = refresh.validate(payload())
        self.assertEqual(len(memes), 60)
        self.assertEqual(memes[0]["id"], "1000")

    def test_rejects_failures_and_odd_payloads(self):
        for bad in ({"success": False}, payload(10), [], {"success": True, "data": {}}):
            with self.assertRaises(ValueError):
                refresh.validate(bad)
        p = payload()
        p["data"]["memes"][3]["url"] = "https://elsewhere.example/x.jpg"
        with self.assertRaises(ValueError):
            refresh.validate(p)
        p = payload()
        p["data"]["memes"][4]["id"] = p["data"]["memes"][5]["id"]
        with self.assertRaises(ValueError):
            refresh.validate(p)


class Update(unittest.TestCase):
    def test_snapshot_and_registry(self):
        memes = refresh.validate(payload())
        reg, tr = refresh.update({}, {"snapshots": []}, memes, "2030-01-05")
        self.assertEqual(len(tr["snapshots"]), 1)
        self.assertEqual(tr["snapshots"][0]["ids"][:2], ["1000", "1001"])
        self.assertEqual(reg["1000"]["first_seen"], "2030-01-05")

    def test_same_day_rerun_replaces_not_appends(self):
        memes = refresh.validate(payload())
        reg, tr = refresh.update({}, {"snapshots": []}, memes, "2030-01-05")
        reg, tr = refresh.update(reg, tr, list(reversed(memes)), "2030-01-05")
        self.assertEqual(len(tr["snapshots"]), 1)
        self.assertEqual(tr["snapshots"][0]["ids"][0], memes[-1]["id"])

    def test_first_seen_kept_last_seen_moves(self):
        memes = refresh.validate(payload())
        reg, tr = refresh.update({}, {"snapshots": []}, memes, "2030-01-05")
        reg, tr = refresh.update(reg, tr, memes[:55], "2030-01-12")
        self.assertEqual(reg["1000"]["first_seen"], "2030-01-05")
        self.assertEqual(reg["1000"]["last_seen"], "2030-01-12")
        self.assertEqual(reg["1059"]["last_seen"], "2030-01-05")
        self.assertEqual([s["date"] for s in tr["snapshots"]], ["2030-01-05", "2030-01-12"])

    def test_keeps_a_bounded_history(self):
        memes = refresh.validate(payload())
        reg, tr = {}, {"snapshots": []}
        start = datetime.date(2030, 1, 5)
        for week in range(refresh.KEEP_SNAPSHOTS + 5):
            reg, tr = refresh.update(reg, tr, memes, (start + datetime.timedelta(weeks=week)).isoformat())
        self.assertEqual(len(tr["snapshots"]), refresh.KEEP_SNAPSHOTS)
        self.assertEqual(tr["snapshots"][-1]["date"], (start + datetime.timedelta(weeks=refresh.KEEP_SNAPSHOTS + 4)).isoformat())


if __name__ == "__main__":
    unittest.main()
