import test from "node:test";
import assert from "node:assert/strict";
import { stem, tokens, normalize, synonyms, buildIndex, search, bestSnippet, highlight } from "../../site/assets/core.js";

const rec = (slug, name, extra = {}) => ({ slug, name, aka: [], describe: [], text: [], franchise: null, look: "", tags: [], use: "", origin: "", ...extra });

const CATALOG = [
  rec("distracted-boyfriend", "Distracted Boyfriend", {
    aka: ["Man Looking at Other Woman"],
    describe: ["guy looking back at another girl while his girlfriend looks mad", "man turns around to check out woman in red dress"],
    look: "A man in a plaid shirt walks with his girlfriend but turns to check out a woman in a red dress.",
    tags: ["stock photo", "couple", "jealousy"],
  }),
  rec("this-is-fine", "This Is Fine", {
    describe: ["dog sitting in a burning room drinking coffee", "cartoon dog at a table with fire all around"],
    text: ["THIS IS FINE."], look: "A cartoon dog in a hat sits at a table with a coffee mug while the room burns.",
    tags: ["dog", "fire", "denial"],
  }),
  rec("spider-man-pointing", "Spider-Man Pointing at Spider-Man", {
    describe: ["two identical superheroes pointing at each other"], franchise: "Spider-Man",
    look: "Two cartoon Spider-Men point at each other.", tags: ["cartoon", "pointing", "same"],
  }),
  rec("two-buttons", "Two Buttons", {
    describe: ["guy sweating over which of two red buttons to press"], look: "A man wipes sweat while deciding between two red buttons.",
    tags: ["choice", "decision", "sweat"],
  }),
];
const index = buildIndex(CATALOG);
const top = (q, opts) => search(index, q, opts)[0]?.record.slug;

test("normalize folds case, accents and punctuation", () => {
  assert.equal(normalize("  Café — DON'T  stop!! "), "cafe dont stop");
});

test("the stemmer folds common word forms", () => {
  for (const [a, b] of [["looking", "looks"], ["staring", "stares"], ["buttons", "button"], ["running", "runs"], ["happiness", "happy"]]) {
    assert.equal(stem(a), stem(b), `${a} vs ${b}`);
  }
  assert.notEqual(stem("hoping"), stem("hopping"));
});

test("tokens drop filler words and fold irregular forms", () => {
  assert.deepEqual(tokens("That meme where the men ran"), ["man", "run"]);
  assert.ok(tokens("no yes", false).length === 2, "no and yes carry meaning in meme descriptions");
});

test("synonym groups are symmetric", () => {
  assert.ok(synonyms(stem("guy")).includes(stem("man")));
  assert.ok(synonyms(stem("man")).includes(stem("guy")));
});

test("plain descriptions find the right template", () => {
  assert.equal(top("guy looks back at another girl"), "distracted-boyfriend");
  assert.equal(top("dude staring at a lady in red"), "distracted-boyfriend");
  assert.equal(top("puppy in a room on fire"), "this-is-fine");
  assert.equal(top("sweaty man choosing a button"), "two-buttons");
});

test("names, typos and compound words", () => {
  assert.equal(top("this is fine"), "this-is-fine");
  assert.equal(top("distracted boyfreind"), "distracted-boyfriend");
  assert.equal(top("spiderman pointing"), "spider-man-pointing");
  assert.equal(top("spider man"), "spider-man-pointing");
});

test("a half-typed last word matches while typing", () => {
  assert.equal(top("two butt", { typing: true }), "two-buttons");
});

test("nonsense finds nothing; filler-only queries don't crash", () => {
  assert.deepEqual(search(index, "zzqxj vvkkw"), []);
  assert.ok(Array.isArray(search(index, "what is that one meme")));
  assert.deepEqual(search(index, ""), []);
});

test("snippets and highlighting point at the matched words", () => {
  const hit = search(index, "woman in red dress")[0];
  assert.match(bestSnippet(hit.record, hit.matched), /red dress/);
  const parts = highlight("a woman in a red dress", hit.matched);
  assert.ok(parts.some((p) => p.hit && p.text === "red"));
  assert.ok(parts.some((p) => !p.hit && p.text === "a"));
});

test("pending templates rank below described ones with the same words", () => {
  const idx = buildIndex([rec("x", "Cat Stare", { describe: ["cat staring"] }), { ...rec("", "Cat Stare"), pending: true }]);
  assert.equal(search(idx, "cat stare")[0].record.slug, "x");
});
