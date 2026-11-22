// End-to-end self-test, loaded only with ?selftest=1. It drives the real search box and checks real
// pages, then writes the verdict to <html data-selftest="pass|fail"> and a <pre id="selftest"> log,
// which scripts/e2e.sh reads from headless Chrome. Expectations come from the catalog the page itself
// loaded (api/v1/meta.json), never from fixed names, so the test keeps passing as the data changes.

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, what, ms = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const v = await fn();
    if (v) return v;
    await wait(25);
  }
  throw new Error("timed out waiting for " + what);
}

function finish(log, error) {
  const pre = document.createElement("pre");
  pre.id = "selftest";
  pre.textContent = (error ? "FAIL: " + (error.stack || error.message || error) + "\n" : "") + log.join("\n");
  document.body.append(pre);
  document.documentElement.dataset.selftest = error ? "fail" : "pass";
}

async function typeQuery(ctx, q) {
  ctx.input.value = q;
  ctx.input.dispatchEvent(new Event("input", { bubbles: true }));
  await until(() => document.body.dataset.query === q, `results for "${q}"`);
}

export async function run(ctx) {
  const log = [];
  try {
    await ctx.ready;
    const meta = await (await fetch(ctx.cfg.base + "api/v1/meta.json")).json();
    if (!meta.selftest || !meta.selftest.queries.length) throw new Error("meta.json has no self-test queries");
    const limit = ctx.cfg.embed ? 3 : 5;
    let found = 0;
    for (const { q, slug } of meta.selftest.queries) {
      await typeQuery(ctx, q);
      const slugs = [...ctx.list.querySelectorAll("li.result")].map((li) => li.dataset.slug);
      const at = slugs.indexOf(slug);
      log.push(`"${q}" -> ${at === -1 ? "MISSING " + slug : "#" + (at + 1) + " " + slug}`);
      if (at !== -1 && at < limit) found++;
    }
    // The self-test queries are chosen at build time from ones the ranker answers; all must come back.
    if (found !== meta.selftest.queries.length) throw new Error(`only ${found} of ${meta.selftest.queries.length} known queries found their template`);
    // The first result links to a page that exists and names the template.
    const first = ctx.list.querySelector("li.result h3 a");
    if (!ctx.cfg.embed) {
      const page = await fetch(first.href);
      const html = await page.text();
      if (!page.ok || !html.includes("<h1")) throw new Error("template page did not load: " + first.href);
      log.push("template page ok: " + new URL(first.href).pathname);
      if (new URL(location.href).searchParams.get("q") !== meta.selftest.queries.at(-1).q) throw new Error("the address bar does not carry the query");
      // Submitting keeps the result and the share button is there.
      ctx.form.requestSubmit();
      await wait(50);
      if (!document.querySelector("[data-share-search]")) throw new Error("no share button");
    } else if (first.target !== "_blank") throw new Error("embed links must open in a new tab");
    // Every result credits Imgflip with a link back, as its terms ask for embedded images.
    for (const li of ctx.list.querySelectorAll("li.result")) {
      if (!li.querySelector('a[href^="https://imgflip.com/meme/"]')) throw new Error("a result has no link back to Imgflip");
    }
    // Nonsense finds nothing and says so.
    await typeQuery(ctx, "zzqxj vvkkw");
    if (ctx.list.querySelectorAll("li.result").length || !ctx.list.querySelector(".empty")) throw new Error("nonsense query should show the empty state");
    log.push("empty state ok");
    // A typo still finds the template.
    const typoCase = meta.selftest.typo;
    if (typoCase) {
      await typeQuery(ctx, typoCase.q);
      const slugs = [...ctx.list.querySelectorAll("li.result")].map((li) => li.dataset.slug);
      if (!slugs.includes(typoCase.slug)) throw new Error(`typo "${typoCase.q}" did not find ${typoCase.slug}`);
      log.push(`typo "${typoCase.q}" ok`);
    }
    log.push(`catalog: ${meta.templates} templates, data ${meta.trending_date || "n/a"}`);
    finish(log);
  } catch (error) {
    finish(log, error);
  }
}

export async function runPage() {
  const log = [];
  try {
    const h1 = document.querySelector("h1");
    if (!h1 || !h1.textContent.trim()) throw new Error("no h1");
    const canonical = document.querySelector('link[rel="canonical"]').href;
    const here = location.origin + location.pathname;
    // Local runs serve the site under the same path as production, so paths always match;
    // on the live host the whole URL must.
    const live = !["localhost", "127.0.0.1"].includes(location.hostname);
    if (new URL(canonical).pathname !== location.pathname) throw new Error(`canonical path ${canonical} does not match ${location.pathname}`);
    if (live && canonical !== here) throw new Error(`canonical ${canonical} != ${here}`);
    for (const node of document.querySelectorAll('script[type="application/ld+json"]')) JSON.parse(node.textContent);
    log.push("h1, canonical and JSON-LD ok: " + h1.textContent.trim());
    const figure = document.querySelector(".meme figure");
    if (figure) {
      if (!figure.querySelector('a[href^="https://imgflip.com/meme/"]')) throw new Error("the image has no link back to Imgflip");
      const img = figure.querySelector("img");
      if (img && new URL(img.src).hostname !== "i.imgflip.com") throw new Error("the image must load from Imgflip, not from this site");
      for (const h of ["What it looks like", "How it's used"]) {
        if (![...document.querySelectorAll("h2")].some((x) => x.textContent.trim() === h)) throw new Error("missing section: " + h);
      }
      const related = [...document.querySelectorAll(".related a.name")].slice(0, 3);
      for (const a of related) {
        const r = await fetch(a.href, { method: "HEAD" });
        if (!r.ok) throw new Error("broken related link " + a.href);
      }
      log.push(`template page ok, ${related.length} related links checked`);
    }
    if (document.querySelector("[data-copy]")) log.push("copy button present");
    finish(log);
  } catch (error) {
    finish(log, error);
  }
}
