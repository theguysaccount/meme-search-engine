# Operations

Describe a Meme is a static site on GitHub Pages. The catalog is JSON in `data/`, the search runs in the
visitor's browser, and GitHub Actions runs everything recurring. There is no server, database or account.

**Live:** https://theguysaccount.github.io/meme-search-engine/
**Repo:** https://github.com/theguysaccount/meme-search-engine

## Automated jobs

| Job | Workflow | When | What it does | How it fails safe |
|---|---|---|---|---|
| Refresh and deploy | `deploy.yml` | Mondays 06:43 UTC, Thursdays 15:17 UTC, every push to `main`, and by hand | On schedule or by hand: pulls Imgflip's public list of the 100 most-captioned templates (`pipeline/refresh.py`). Then: Python and Node tests (including the search-quality eval), build, five end-to-end runs in headless Chrome, saves the refreshed data back to `main`, deploys, runs the same five checks on the live site, pings IndexNow. | Imgflip down, slow or odd: warning only, nothing written, the last good data is used. Any failed test or check stops the run before the data commit and before deploy, so the last good site stays live. Re-running is safe: a second pull on the same day replaces that day's snapshot. |
| Weekly self-test | `selftest.yml` | Saturdays 11:29 UTC, and by hand | Tests; the end-to-end checks on the **live** site; every sitemap page answers 200 with its own canonical; the four API files parse and agree; the IndexNow key is served; trending data is fresh; 20 template pictures still load from Imgflip. | Data older than 9 days: starts `deploy.yml` with a refresh. Older than 21 days, or any broken page: the run fails and opens (or comments on) one `ops-alert` issue, and GitHub emails the repo owner. A missing picture is a warning only: the page falls back to a text link by itself. |
| Keep-alive | `selftest.yml` → `scripts/keepalive.sh` | weekly | Re-enables every scheduled workflow (except one turned off by hand); an empty `[skip ci]` commit after 45 days without commits. | GitHub disables schedules after 60 quiet days; the data commits and this keep them alive. |

GitHub fires scheduled runs on this account hours late and sometimes skips them. Nothing here depends on exact
timing: two refresh slots a week, a stale check that starts a refresh, and every job is safe to re-run.

## What to watch

- **Open `ops-alert` issues.** They name the failing check and link the run.
- **`correction` and `removal` issues.** People file these from the links on every page. Removals come first:
  - *Stop showing the picture:* add `"embed": false` to `data/templates/<slug>.json` and push. The page and the search
    result switch to a text link; nothing else changes.
  - *Remove the page:* delete `data/templates/<slug>.json`, add its Imgflip id with a reason to `blocked_ids` in
    `data/moderation.json`, and push. The template also disappears from the trending list.
  - *Corrections:* edit the JSON file, run the tests, push.
- **The job summary of each refresh** lists trending templates that aren't described yet. They show on the
  trending page and in search with their Imgflip name and link only (no picture) until the content routine
  describes them (key 1).

## Content rules (what the site will not show)

- No meme pictures are hosted here. Where a picture appears, the browser loads it from `i.imgflip.com` with a link
  back to Imgflip, as Imgflip's terms ask. The repository variable `EMBED_IMAGES=0` turns every picture off
  site-wide (text links only).
- Templates whose joke is hate toward a group, slurs or hate symbols, sexual content, self-harm or hard drugs,
  or real tragedies and real violence are left out (`data/moderation.json`, `blocked_ids`, with reasons). They are
  also left off the trending list.
- Ordinary people who became memes are described by the meme's name only; their real names are never written.
- Unreviewed trending templates never get a picture, and their names are checked against `blocked_terms`.

## Keys Jack can turn later

### 1. Content routine (new templates)

AI-written descriptions can't run inside Actions (no API key). Schedule a Claude Code routine (claude.ai/code →
Routines) for the 1st and 15th of each month on this repo:

> In theguysaccount/meme-search-engine: run `python3 pipeline/caption_queue.py /tmp/queue --limit 40` to list
> trending Imgflip templates that aren't described yet and download their pictures for viewing. Follow
> `pipeline/CAPTIONING.md` exactly to describe each one, writing `/tmp/queue/out.json`; validate with
> `python3 pipeline/validate_captions.py /tmp/queue/out.json /tmp/queue/batch.json`. Merge with
> `python3 pipeline/merge_captions.py --batch /tmp/queue/batch.json --out /tmp/queue/out.json` (it never overwrites an
> existing template). Add two or three plain descriptions of new templates to `tests/eval.json`, keyed by Imgflip id,
> written before reading your own entries. Run `python3 -m unittest discover -s tests`, `node --test tests/js/*.test.mjs` and
> `python3 pipeline/build.py`, then commit and push. Never commit images.

Also worth giving the routine: open `correction` issues, to apply and close.

### 2. Custom domain

The base URL is one setting: the repository variable `SITE_URL`. Everything else (canonical URLs, sitemap,
robots.txt, share cards, structured data, IndexNow, the self-tests) follows it. To move the site to a domain:

1. DNS at the registrar (not done; the domain rollout owns DNS). For a subdomain such as `memes.example.com`:
   `CNAME memes → theguysaccount.github.io`. For an apex domain: `A @ → 185.199.108.153, 185.199.109.153,
   185.199.110.153, 185.199.111.153`, `AAAA @ → 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153,
   2606:50c0:8003::153`, and `CNAME www → theguysaccount.github.io`.
2. Tell Pages: `gh api -X PUT repos/theguysaccount/meme-search-engine/pages -f cname=<domain>` (Pages deploys by
   workflow here, so no CNAME file is needed). When the certificate is ready:
   `gh api -X PUT repos/theguysaccount/meme-search-engine/pages -F https_enforced=true`.
3. Set the base URL: `gh variable set SITE_URL -b https://<domain> -R theguysaccount/meme-search-engine`.
4. Rebuild: `gh workflow run deploy.yml -R theguysaccount/meme-search-engine -f refresh=false`. The deploy's live
   checks run against the new address.

The old `github.io` address then redirects to the domain (GitHub does this for project sites with a custom domain).
Domain ideas are in `LAUNCH.md`.

### 3. Money

Pages is non-commercial, so there's no checkout. One slot is built in: a sponsor box on the home page, every
template page and the API page, hidden until set. Set `SPONSOR_URL` (and optionally `SPONSOR_LABEL`, e.g.
"Sponsored by …") as repository variables and redeploy. A paid API tier or ads would need other hosting plus an
account with Stripe or an ad network; that's a decision for Jack (see `DECISIONS.md`).

### 4. Analytics

Off by default. Create a GoatCounter site (cookieless), then set `GOATCOUNTER_URL` = `https://<code>.goatcounter.com/count`
and redeploy. Events already in the code: `search` (**activation**: the first search a visitor runs), `example`
(clicked a sample description), `result_open`, `imgflip_out` (opened the template on Imgflip: **the value event**),
`copy_link`, `share_search`, `share_page`, `copy_embed`.

### 5. Search Console

Google no longer takes sitemap pings. Verify the site in Google Search Console (`GOOGLE_SITE_VERIFICATION` repository
variable = the content of Google's meta tag, then redeploy) and submit `/sitemap.xml`. Bing and Yandex get every
deploy through IndexNow. The account's root `robots.txt` (theguysaccount.github.io) lists this site's sitemap
automatically.

## Running it by hand

```bash
python3 -m unittest discover -s tests -v      # Python tests (build, catalog, refresh)
node --test tests/js/*.test.mjs                          # search tests and the quality eval
python3 pipeline/refresh.py                    # pull Imgflip's list now
python3 pipeline/build.py                      # build into dist/
scripts/e2e.sh                                 # drive dist/ in headless Chrome
scripts/e2e.sh https://theguysaccount.github.io/meme-search-engine/   # the same on the live site
python3 scripts/check_live.py https://theguysaccount.github.io/meme-search-engine
gh workflow run deploy.yml -R theguysaccount/meme-search-engine -f refresh=true
```
