// Search box behaviour for the home page, the 404 page and the embeddable widget.
// Everything runs in the browser: the catalog is one JSON file, the ranking is core.js.
import { buildIndex, search, bestSnippet, highlight } from "./core.js";

const cfg = JSON.parse(document.getElementById("cfg").textContent);
const form = document.querySelector("form.search");
const input = form.querySelector("input[type=search]");
const list = document.querySelector("ol.results");
const status = document.getElementById("status");
const toast = document.getElementById("toast");
const LIMIT = cfg.embed ? 3 : 8;
let index = null;
let counted = false;
let lastQuery = null;

export function track(name) {
  try {
    if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "event/" + name, title: name, event: true });
  } catch (e) { /* analytics must never break the page */ }
}

function el(tag, props = {}, kids = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "text") node.textContent = v;
    else if (k === "class") node.className = v;
    else if (k.startsWith("data-") || k.startsWith("aria-") || k === "role") node.setAttribute(k, v);
    else node[k] = v;
  }
  for (const kid of kids) if (kid) node.append(kid);
  return node;
}

function expandRecord(c) {
  return { slug: c.s, name: c.n, aka: c.a || [], describe: c.d || [], text: c.t || [], franchise: c.f || null, look: c.l || "",
    tags: c.g || [], use: c.u || "", origin: c.o || "", id: c.id, img: c.i || null, popularity: c.p || 0, pending: !!c.x };
}

const ready = fetch(cfg.index)
  .then((r) => { if (!r.ok) throw new Error("catalog " + r.status); return r.json(); })
  .then((data) => { index = buildIndex(data.templates.map(expandRecord)); return index; });

function say(message) {
  toast.textContent = message;
  toast.classList.add("on");
  clearTimeout(say.t);
  say.t = setTimeout(() => toast.classList.remove("on"), 1800);
}

async function copy(text, done) {
  try {
    await navigator.clipboard.writeText(text);
    say(done);
  } catch (e) {
    window.prompt("Copy this link:", text);
  }
}

function thumb(record) {
  const href = record.pending ? `https://imgflip.com/meme/${record.id}` : pageUrl(record);
  const a = el("a", { class: "thumb", href, tabIndex: -1 });
  a.setAttribute("aria-hidden", "true");
  if (cfg.embed || record.pending) { a.target = "_blank"; a.rel = "noopener"; }
  if (cfg.images && record.img) {
    const img = el("img", { alt: "", loading: "lazy", decoding: "async", width: 112, height: 112 });
    img.referrerPolicy = "strict-origin-when-cross-origin";
    img.addEventListener("error", () => { a.classList.add("none"); a.textContent = "Image on Imgflip"; });
    img.src = `https://i.imgflip.com/4/${record.img}.jpg`;
    a.append(img);
  } else {
    a.classList.add("none");
    a.textContent = "Image on Imgflip";
  }
  return a;
}

const pageUrl = (record) => `${cfg.base}meme/${record.slug}/`;

function renderResult(hit, isBest) {
  const r = hit.record;
  const title = r.pending
    ? el("a", { href: `https://imgflip.com/meme/${r.id}`, text: r.name, target: "_blank", rel: "noopener" })
    : el("a", { href: pageUrl(r), text: r.name });
  if (cfg.embed && !r.pending) { title.target = "_blank"; title.rel = "noopener"; }
  title.addEventListener("click", () => track(r.pending ? "imgflip_out" : "result_open"));
  const h3 = el("h3", {}, [title]);
  if (isBest) h3.append(el("span", { class: "badge", text: "Best match" }));
  if (r.pending) h3.append(el("span", { class: "badge new", text: "New, not described yet" }));
  const body = el("div", {}, [h3]);
  if (r.aka.length) body.append(el("p", { class: "aka", text: "Also called: " + r.aka.join(", ") }));
  if (!r.pending) {
    const snippet = el("p", { class: "snippet" });
    for (const piece of highlight(bestSnippet(r, hit.matched), hit.matched)) {
      snippet.append(piece.hit ? el("mark", { text: piece.text }) : document.createTextNode(piece.text));
    }
    body.append(snippet);
  }
  const acts = el("p", { class: "acts" });
  const out = el("a", { href: `https://imgflip.com/meme/${r.id}`, text: "Blank template on Imgflip ↗", target: "_blank", rel: "noopener" });
  out.addEventListener("click", () => track("imgflip_out"));
  acts.append(out);
  if (!r.pending && !cfg.embed) {
    const b = el("button", { class: "quiet", type: "button", text: "Copy link" });
    b.addEventListener("click", () => { copy(new URL(pageUrl(r), location.href).href, "Link copied"); track("copy_link"); });
    acts.append(b);
  }
  body.append(acts);
  const li = el("li", { class: "result" + (isBest ? " best" : "") }, [thumb(r), body]);
  li.dataset.slug = r.slug || "";
  li.dataset.id = r.id;
  return li;
}

function render(query, typing) {
  const q = query.trim();
  if (q === lastQuery && !typing) return;
  lastQuery = q;
  list.replaceChildren();
  document.body.dataset.query = q;
  if (!q) {
    status.textContent = "";
    document.body.dataset.results = "";
    return;
  }
  const hits = search(index, q, { limit: LIMIT, typing });
  document.body.dataset.results = String(hits.length);
  if (!hits.length) {
    status.textContent = `No match for “${q}” yet.`;
    const tips = el("li", { class: "empty" }, [
      el("p", { text: "Try describing what you see instead of what it means: who or what is in the picture, what they are doing, colours, and any words printed on it." }),
    ]);
    if (!cfg.embed) {
      const p = el("p", {});
      p.append("Or browse ", el("a", { href: cfg.base + "all/", text: "every template A to Z" }), ".");
      tips.append(p);
    }
    list.append(tips);
    return;
  }
  const confident = hits.length === 1 || hits[0].score >= hits[1].score * 1.25;
  status.textContent = hits.length === 1 ? `1 match for “${q}”` : `${hits.length} matches for “${q}”, best first`;
  hits.forEach((hit, i) => list.append(renderResult(hit, i === 0 && confident && !hit.record.pending)));
  if (!counted && !typing) { counted = true; track("search"); }
}

function syncUrl(q) {
  const url = new URL(location.href);
  if (q) url.searchParams.set("q", q);
  else url.searchParams.delete("q");
  history.replaceState(null, "", url);
}

let timer = null;
input.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(async () => {
    await ready;
    render(input.value, true);
    if (!cfg.embed) syncUrl(input.value.trim());
  }, 90);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearTimeout(timer);
  await ready;
  lastQuery = null;
  render(input.value, false);
  if (!cfg.embed) syncUrl(input.value.trim());
  if (window.matchMedia("(max-width: 720px)").matches) input.blur();
});

document.querySelectorAll("[data-example]").forEach((b) => b.addEventListener("click", () => {
  input.value = b.dataset.example;
  form.requestSubmit();
  track("example");
}));

const shareButton = document.querySelector("[data-share-search]");
if (shareButton) shareButton.addEventListener("click", () => {
  const url = new URL(location.href);
  if (navigator.share && window.matchMedia("(pointer: coarse)").matches) {
    navigator.share({ title: document.title, url: url.href }).catch(() => {});
  } else copy(url.href, "Search link copied");
  track("share_search");
});

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== input && !event.metaKey && !event.ctrlKey) {
    event.preventDefault();
    input.focus();
  }
});

const params = new URLSearchParams(location.search);
const initial = params.get("q");
ready.then(() => {
  document.body.dataset.ready = "1";
  if (initial) {
    input.value = initial;
    render(initial, false);
  }
}).catch((error) => {
  status.textContent = "The catalog didn't load. Check your connection and reload.";
  console.error(error);
});

if (params.has("selftest")) {
  import("./selftest.js").then((m) => m.run({ ready, cfg, input, form, list }));
}
