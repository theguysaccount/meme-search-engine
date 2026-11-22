// Search quality on descriptions written before reading the catalog text (tests/eval.json).
// Thresholds sit a little below the measured rates so a real regression fails, not normal catalog growth.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { buildIndex, search } from "../../site/assets/core.js";

const root = new URL("../../", import.meta.url);
const dir = new URL("data/templates/", root);
const templates = readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => JSON.parse(readFileSync(new URL(f, dir))));
const records = templates.map((t) => ({
  slug: t.slug, name: t.name, aka: [...t.aka, ...t.variants.map((v) => v.name)], describe: t.describe, text: t.text,
  franchise: t.franchise, look: t.look, tags: t.tags, use: t.use, origin: t.origin, popularity: 0,
}));
const slugOf = new Map();
for (const t of templates) {
  slugOf.set(String(t.imgflip.id), t.slug);
  for (const v of t.variants) slugOf.set(String(v.id), t.slug);
}
const evalSet = JSON.parse(readFileSync(new URL("tests/eval.json", root)));
const index = buildIndex(records);

export const MIN_TOP1 = 0.85;
export const MIN_TOP3 = 0.93;

test("described templates are found from plain descriptions", () => {
  const cases = evalSet.queries.filter((q) => slugOf.has(q.id));
  let top1 = 0, top3 = 0;
  const misses = [];
  for (const { id, q } of cases) {
    const want = slugOf.get(id);
    const got = search(index, q, { limit: 10 }).map((r) => r.record.slug);
    const at = got.indexOf(want);
    if (at === 0) top1++;
    if (at !== -1 && at < 3) top3++;
    else misses.push(`"${q}" -> wanted ${want}, got ${got.slice(0, 3).join(", ") || "nothing"}`);
  }
  const n = cases.length;
  console.log(`eval: ${n} queries, top-1 ${(top1 / n * 100).toFixed(1)}%, top-3 ${(top3 / n * 100).toFixed(1)}%`);
  for (const m of misses) console.log("  miss " + m);
  assert.ok(n >= 20, "too few eval queries match the catalog");
  assert.ok(top1 / n >= MIN_TOP1, `top-1 ${top1}/${n} below ${MIN_TOP1}`);
  assert.ok(top3 / n >= MIN_TOP3, `top-3 ${top3}/${n} below ${MIN_TOP3}`);
});

test("the showcase queries used by the live self-test come first", () => {
  for (const { id, q } of evalSet.showcase) {
    if (!slugOf.has(id)) continue;
    const got = search(index, q, { limit: 5 }).map((r) => r.record.slug);
    assert.ok(got.slice(0, 3).includes(slugOf.get(id)), `"${q}" -> ${got.join(", ")}`);
  }
});
