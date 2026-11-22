// Describe-a-meme search: tokenizer, Porter stemmer, synonym expansion and a field-weighted BM25 ranker.
// Pure functions with no DOM access, so the same file runs in the browser, in the embed and in node tests.

// Filler words carry no meaning in a meme description. "no", "not" and "yes" stay: they are the whole
// point of some templates. Names made only of filler words ("This Is Fine") still match through the
// exact-name and phrase checks in search(), which keep every word.
const STOP = new Set(("a an and are as at be been being but by can could did do does doing for from had has have having he her " +
  "hers him his i if in into is it its just me my of on or our ours she so some than that the their theirs them then there " +
  "these they this those to too us was we were what when where which while who whom whose will with would you your yours " +
  "meme memes template templates picture pictures pic pics image images thing things like kind sort type " +
  "called name named format something someone somebody really very also about im thats whats").split(" "));

export function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[‘’'`]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

// --- Porter stemmer (M.F. Porter, 1980), the standard algorithm -------------------------------
const C = "[^aeiou]", V = "[aeiouy]", CC = C + "[^aeiouy]*", VV = V + "[aeiou]*";
const MGR0 = new RegExp("^(" + CC + ")?" + VV + CC);
const MEQ1 = new RegExp("^(" + CC + ")?" + VV + CC + "(" + VV + ")?$");
const MGR1 = new RegExp("^(" + CC + ")?" + VV + CC + VV + CC);
const HASV = new RegExp("^(" + CC + ")?" + V);
const CVC = new RegExp("^" + CC + V + "[^aeiouwxy]$");
const STEP2 = { ational: "ate", tional: "tion", enci: "ence", anci: "ance", izer: "ize", bli: "ble", alli: "al", entli: "ent",
  eli: "e", ousli: "ous", ization: "ize", ation: "ate", ator: "ate", alism: "al", iveness: "ive", fulness: "ful",
  ousness: "ous", aliti: "al", iviti: "ive", biliti: "ble", logi: "log" };
const STEP3 = { icate: "ic", ative: "", alize: "al", iciti: "ic", ical: "ic", ful: "", ness: "" };
const stemCache = new Map();

export function stem(word) {
  if (word.length < 3 || /^\d+$/.test(word)) return word;
  const hit = stemCache.get(word);
  if (hit !== undefined) return hit;
  let w = word;
  const firstY = w[0] === "y";
  if (firstY) w = "Y" + w.slice(1);
  let m;
  // 1a
  if ((m = /^(.+?)(ss|i)es$/.exec(w))) w = m[1] + m[2];
  else if ((m = /^(.+?)([^s])s$/.exec(w))) w = m[1] + m[2];
  // 1b
  if ((m = /^(.+?)eed$/.exec(w))) {
    if (MGR0.test(m[1])) w = w.slice(0, -1);
  } else if ((m = /^(.+?)(ed|ing)$/.exec(w)) && HASV.test(m[1])) {
    w = m[1];
    if (/(at|bl|iz)$/.test(w)) w += "e";
    else if (/([^aeiouylsz])\1$/.test(w)) w = w.slice(0, -1);
    else if (CVC.test(w)) w += "e";
  }
  // 1c
  if ((m = /^(.+?)y$/.exec(w)) && HASV.test(m[1])) w = m[1] + "i";
  // 2
  if ((m = /^(.+?)(ational|tional|enci|anci|izer|bli|alli|entli|eli|ousli|ization|ation|ator|alism|iveness|fulness|ousness|aliti|iviti|biliti|logi)$/.exec(w)) && MGR0.test(m[1])) w = m[1] + STEP2[m[2]];
  // 3
  if ((m = /^(.+?)(icate|ative|alize|iciti|ical|ful|ness)$/.exec(w)) && MGR0.test(m[1])) w = m[1] + STEP3[m[2]];
  // 4
  if ((m = /^(.+?)(al|ance|ence|er|ic|able|ible|ant|ement|ment|ent|ou|ism|ate|iti|ous|ive|ize)$/.exec(w))) {
    if (MGR1.test(m[1])) w = m[1];
  } else if ((m = /^(.+?)(s|t)(ion)$/.exec(w)) && MGR1.test(m[1] + m[2])) w = m[1] + m[2];
  // 5
  if ((m = /^(.+?)e$/.exec(w)) && (MGR1.test(m[1]) || (MEQ1.test(m[1]) && !CVC.test(m[1])))) w = m[1];
  if (/ll$/.test(w) && MGR1.test(w)) w = w.slice(0, -1);
  if (firstY) w = "y" + w.slice(1);
  stemCache.set(word, w);
  return w;
}

// --- Tokens -------------------------------------------------------------------------------------
// Irregular forms the stemmer can't fold together, as people use them when describing a picture.
const IRREGULAR = Object.fromEntries(("men:man women:woman children:child people:person feet:foot teeth:tooth mice:mouse " +
  "dies:die died:die dying:die lies:lie lying:lie ran:run sat:sit stood:stand held:hold threw:throw thrown:throw fell:fall " +
  "fallen:fall saw:see seen:see said:say told:tell thought:think took:take taken:take gave:give given:give got:get went:go " +
  "gone:go came:come made:make drew:draw drawn:draw wore:wear worn:wear drove:drive driven:drive ate:eat eaten:eat " +
  "drank:drink wrote:write written:write shook:shake shaken:shake hid:hide hidden:hide burnt:burn caught:catch " +
  "fought:fight slept:sleep wept:weep chose:choose chosen:choose broke:break broken:break spoke:speak spoken:speak " +
  "flew:fly swam:swim sang:sing rode:ride woke:wake stuck:stick struck:strike hung:hang paid:pay built:build " +
  "bought:buy brought:bring taught:teach felt:feel kept:keep met:meet sold:sell sent:send won:win grew:grow knew:know " +
  "known:know became:become began:begin blew:blow shot:shoot lit:light cries:cry cried:cry tries:try tried:try " +
  "flies:fly dries:dry fries:fry skies:sky spies:spy").split(" ").map((pair) => pair.split(":")));
const NUMBER_WORDS = { one: "1", two: "2", three: "3", four: "4", five: "5", six: "6", double: "2", triple: "3", both: "2", pair: "2", couple: "2" };

/** Words of a text, lowercased and stemmed. `keepStop` keeps stopwords (used for phrase matching). */
export function tokens(text, keepStop = false) {
  const out = [];
  for (const raw of normalize(text).split(" ")) {
    if (!raw) continue;
    if (!keepStop && STOP.has(raw)) continue;
    out.push(stem(IRREGULAR[raw] || raw));
  }
  return out;
}

// --- Synonyms -----------------------------------------------------------------------------------
// Groups of words people swap freely when describing a picture. A query word also matches the other
// words of its group at reduced weight. Kept small and literal on purpose: every group was added for a
// real description mismatch, and tests/js/eval.test.mjs measures the effect.
const SYNONYM_GROUPS = [
  "man guy dude bloke fella gentleman male bro",
  "woman lady girl gal female chick",
  "boyfriend husband bf partner",
  "girlfriend wife gf partner",
  "kid child boy girl toddler baby infant youngster",
  "old elderly senior grandpa grandma grandfather grandmother aged",
  "dog doge puppy pup doggo shiba hound canine",
  "cat kitty kitten feline",
  "monkey ape chimp chimpanzee orangutan gorilla",
  "bird pigeon seagull gull parrot puffin",
  "frog toad",
  "bear grizzly",
  "fish shark",
  "angry mad furious upset annoyed pissed rage raging irritated livid",
  "yell scream shout holler screech",
  "sad cry tear sob weep unhappy depressed miserable",
  "happy smile grin joy glad cheerful delighted",
  "laugh lol giggle chuckle crack hilarious",
  "scared afraid terrified frightened fear panic horrified nervous anxious",
  "surprised shocked stunned astonished amazed gasp startled",
  "confused puzzled perplexed baffled lost",
  "smug satisfied pleased proud",
  "tired exhausted sleepy sleep asleep nap doze",
  "sweat nervous stress stressed anxious",
  "look stare glance watch gaze peek peer eye check",
  "turn back around behind",
  "point finger gesture",
  "run sprint flee chase escape jog",
  "walk stroll step",
  "hold carry grip grab clutch",
  "sit seat seated chair",
  "stand standing",
  "think ponder wonder contemplate thought",
  "talk speak say tell explain lecture",
  "hit slap punch smack strike beat",
  "shake handshake clasp grip",
  "drink sip beer wine champagne glass toast cheers",
  "eat food meal dinner lunch",
  "fire flame burn blaze burning",
  "car vehicle automobile truck van",
  "road highway freeway street motorway lane",
  "exit ramp offramp turn swerve drift",
  "house home building room",
  "glasses spectacles shades sunglasses",
  "suit tuxedo tux formal",
  "hat cap helmet",
  "money cash dollar bill rich",
  "phone smartphone cellphone mobile",
  "computer laptop pc keyboard",
  "table desk counter",
  "sign board poster placard banner card",
  "button switch",
  "gun pistol weapon",
  "sword blade knife",
  "book page paper scroll letter note document",
  "brain mind head",
  "picture photo image pic portrait painting",
  "cartoon animated animation anime drawn drawing comic",
  "movie film scene show series",
  "panel frame box square",
  "big large huge giant buff muscular strong",
  "small little tiny weak skinny",
  "robot android machine terminator",
  "alien extraterrestrial ufo",
  "skeleton skull bones dead death",
  "ghost spirit",
  "clown jester makeup",
  "king queen royal crown throne",
  "soldier army military troop",
  "police cop officer",
  "doctor nurse hospital surgeon",
  "teacher professor school class classroom student",
  "office boss manager meeting boardroom work job",
  "space astronaut earth planet moon",
  "water pool sea ocean lake swim drown",
  "window glass blinds",
  "door doorway gate",
  "bus train subway",
  "bike bicycle cycle",
  "ball balloon",
  "wink smirk",
  "hug embrace",
  "kiss love heart",
  "fight battle argue argument quarrel",
  "choose choice pick decide decision option",
  "compare versus vs comparison",
  "ignore neglect",
  "hide hiding conceal behind",
  "throw toss yeet",
  "fall trip crash",
  "dance boogie groove",
];
const SYN = new Map();
for (const line of SYNONYM_GROUPS) {
  const group = [...new Set(line.split(" ").map(stem))];
  for (const w of group) {
    if (!SYN.has(w)) SYN.set(w, new Set());
    for (const o of group) if (o !== w) SYN.get(w).add(o);
  }
}
export const synonyms = (stemmed) => [...(SYN.get(stemmed) || [])];

// --- Index --------------------------------------------------------------------------------------
// Field weights: how much a word counts depending on where it appears in a template's entry.
export const FIELD_WEIGHTS = { name: 6, aka: 5, describe: 3.2, text: 3, franchise: 2.5, look: 2.2, tags: 2, use: 1.2, origin: 1 };
const K1 = 1.2, B = 0.45;

function addField(doc, text, weight, phraseFields) {
  const list = Array.isArray(text) ? text : [text];
  for (const part of list) {
    if (!part) continue;
    const toks = tokens(part);
    for (const t of toks) doc.tf.set(t, (doc.tf.get(t) || 0) + weight);
    doc.len += toks.length * weight;
    if (phraseFields) phraseFields.push(" " + tokens(part, true).join(" ") + " ");
  }
}

/**
 * Build an index from catalog records.
 * record: { slug, name, aka[], describe[], text[], franchise, look, tags[], use, origin, pending }
 */
export function buildIndex(records) {
  const docs = [];
  const df = new Map();
  for (const r of records) {
    const doc = { r, tf: new Map(), len: 0, phrases: [], names: [] };
    addField(doc, r.name, FIELD_WEIGHTS.name, doc.phrases);
    addField(doc, r.aka, FIELD_WEIGHTS.aka, doc.phrases);
    addField(doc, r.describe, FIELD_WEIGHTS.describe, doc.phrases);
    addField(doc, r.text, FIELD_WEIGHTS.text, doc.phrases);
    addField(doc, r.franchise, FIELD_WEIGHTS.franchise, doc.phrases);
    addField(doc, r.look, FIELD_WEIGHTS.look, doc.phrases);
    addField(doc, r.tags, FIELD_WEIGHTS.tags);
    addField(doc, r.use, FIELD_WEIGHTS.use);
    addField(doc, r.origin, FIELD_WEIGHTS.origin);
    doc.names = [r.name, ...(r.aka || [])].map((n) => tokens(n, true).join(" "));
    for (const t of doc.tf.keys()) df.set(t, (df.get(t) || 0) + 1);
    docs.push(doc);
  }
  const avgLen = docs.reduce((s, d) => s + d.len, 0) / Math.max(1, docs.length);
  const vocab = [...df.keys()];
  return { docs, df, avgLen, vocab, n: docs.length };
}

function idf(index, term) {
  const n = index.df.get(term) || 0;
  return Math.log(1 + (index.n - n + 0.5) / (n + 0.5));
}

function termScore(index, doc, term) {
  const tf = doc.tf.get(term);
  if (!tf) return 0;
  return idf(index, term) * ((tf * (K1 + 1)) / (tf + K1 * (1 - B + (B * doc.len) / index.avgLen)));
}

function editDistanceAtMost1(a, b) {
  if (a === b) return true;
  const la = a.length, lb = b.length;
  if (Math.abs(la - lb) > 1) return false;
  let i = 0, j = 0, edits = 0;
  while (i < la && j < lb) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++edits > 1) return false;
    if (la > lb) i++;
    else if (lb > la) j++;
    else {
      // substitution, or a swap of two neighbouring letters
      if (a[i + 1] === b[j] && a[i] === b[j + 1] && a.slice(i + 2) === b.slice(j + 2)) return true;
      i++; j++;
    }
  }
  return edits + (la - i) + (lb - j) <= 1;
}

/** For one query word: the index terms it may match, each with a weight. */
function expand(index, term, isLast, typing) {
  const out = new Map([[term, 1]]);
  const put = (t, w) => { if (index.df.has(t) && (out.get(t) || 0) < w) out.set(t, w); };
  for (const s of synonyms(term)) put(s, 0.45);
  if (NUMBER_WORDS[term]) put(NUMBER_WORDS[term], 0.8);
  for (const [word, digit] of Object.entries(NUMBER_WORDS)) if (digit === term) put(stem(word), 0.6);
  if (!index.df.has(term)) {
    // "spiderman" when the catalog says "spider man"
    for (let k = 3; k <= term.length - 3; k++) {
      const a = stem(term.slice(0, k)), b = stem(term.slice(k));
      if (index.df.has(a) && index.df.has(b)) { put(a, 0.8); put(b, 0.8); }
    }
    if (term.length >= 4) {
      for (const v of index.vocab) {
        if (v[0] === term[0] && editDistanceAtMost1(term, v)) put(v, 0.55);
      }
    }
    if (isLast && typing && term.length >= 2) {
      let seen = 0;
      for (const v of index.vocab) {
        if (v.startsWith(term) && seen++ < 30) put(v, 0.6);
      }
    }
  }
  return out;
}

/**
 * Search. Returns [{ record, score, matched: [stems], coverage }] best first.
 * options.typing: the query is still being typed, so the last word may be a prefix.
 */
export function search(index, query, options = {}) {
  const limit = options.limit || 10;
  const qTokens = [...new Set(tokens(query))];
  const qPhrase = tokens(query, true);
  if (!qTokens.length) {
    // The query was only filler words ("what is that one meme"): fall back to the raw words.
    for (const t of qPhrase) if (!qTokens.includes(t)) qTokens.push(t);
  }
  if (!qTokens.length) return [];
  const expansions = qTokens.map((t, i) => expand(index, t, i === qTokens.length - 1, options.typing));
  // "spider man" when the catalog says "spiderman": a joined pair counts for both of its words.
  const raw = normalize(query).split(" ").filter(Boolean);
  for (let i = 0; i + 1 < raw.length; i++) {
    const joined = stem(raw[i] + raw[i + 1]);
    if (!index.df.has(joined)) continue;
    for (const part of [stem(raw[i]), stem(raw[i + 1])]) {
      const at = qTokens.indexOf(part);
      if (at >= 0 && (expansions[at].get(joined) || 0) < 0.9) expansions[at].set(joined, 0.9);
    }
  }
  const qNorm = qPhrase.join(" ");
  const bigrams = [];
  for (let i = 0; i + 1 < qPhrase.length; i++) bigrams.push(" " + qPhrase[i] + " " + qPhrase[i + 1] + " ");
  const results = [];
  for (const doc of index.docs) {
    let score = 0, hit = 0;
    const matched = [];
    for (let i = 0; i < qTokens.length; i++) {
      let best = 0, bestTerm = null;
      for (const [term, weight] of expansions[i]) {
        const s = termScore(index, doc, term) * weight;
        if (s > best) { best = s; bestTerm = term; }
      }
      if (best > 0) { score += best; hit++; matched.push(bestTerm); }
    }
    if (!hit) continue;
    const coverage = hit / qTokens.length;
    score *= 0.35 + 0.65 * coverage * coverage;
    let phraseHits = 0;
    for (const bg of bigrams) if (doc.phrases.some((p) => p.includes(bg))) phraseHits++;
    if (bigrams.length) score *= 1 + 0.35 * (phraseHits / bigrams.length);
    if (doc.names.includes(qNorm)) score *= 3;
    else if (qNorm.length > 3 && doc.names.some((n) => n.startsWith(qNorm + " ") || n.includes(" " + qNorm))) score *= 1.5;
    if (doc.r.popularity) score *= 1 + 0.04 * doc.r.popularity;
    if (doc.r.pending) score *= 0.6;
    results.push({ record: doc.r, score, matched, coverage });
  }
  results.sort((a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name));
  const top = results.slice(0, limit);
  // Drop the long tail of weak partial matches once there is a clearly better answer.
  const floor = top.length ? top[0].score * 0.22 : 0;
  return top.filter((r) => r.score >= floor);
}

/** The describe phrase or sentence that best explains why a record matched, for display. */
export function bestSnippet(record, matched) {
  const want = new Set(matched);
  let best = record.look || "", bestHits = -1;
  for (const cand of [...(record.describe || []), record.look || ""]) {
    const hits = new Set(tokens(cand).filter((t) => want.has(t))).size;
    if (hits > bestHits) { best = cand; bestHits = hits; }
  }
  return best;
}

/** Split text into [{ text, hit }] so the matched words can be highlighted. */
export function highlight(text, matched) {
  const want = new Set(matched);
  return String(text).split(/(\s+)/).map((piece) => {
    const t = tokens(piece);
    return { text: piece, hit: t.length > 0 && t.every((x) => want.has(x)) };
  });
}
