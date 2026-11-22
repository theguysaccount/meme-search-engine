# Launch

**Live (launch URL):** https://theguysaccount.github.io/meme-search-engine/. Nothing here needs DNS to work.

## Domain candidates (checked by RDAP on 2026-11-22; nothing bought, no DNS changed)

| # | Domain | Status | Note |
|---|---|---|---|
| 1 | `memes.gifstudios.com` | gifstudios.com is Jack's | One CNAME; ties the search into Gif Studios, as the note asked. |
| 2 | `describeameme.com` | unregistered (about $11/yr) | Exactly the product name. `describeameme.org` is also free. |
| 3 | `whatmemeisthis.com` | unregistered (about $11/yr) | Matches how people phrase the question. (`whatsthatmeme.com`, `namethatmeme.com`, `findthatmeme.com` and `memefinder.com` are taken.) |

Switching steps are in OPERATIONS.md, key 2 (one repository variable, `SITE_URL`, plus the Pages custom-domain
setting). The "domain rollout" session owns DNS.

## Distribution (machine channels only; nothing is posted as a person)

- **Search pages.** One page per template with name, other names, what it looks like, words on it, how it's used,
  examples and how people describe it; browse pages by collection, shape and source; an A to Z list; a weekly
  trending page. Titles target "<name> meme" and "what's the meme where…" searches.
- **Structured data.** WebSite with SearchAction (sitelinks search box), WebPage + BreadcrumbList per template,
  CollectionPage + ItemList per browse page. Canonical URLs, sitemap, robots.txt, text share cards per template.
- **IndexNow** on every deploy (Bing, Yandex, Seznam, Naver). The account root robots.txt lists the sitemap for Google.
- **Share loop.** Every search updates the address bar (`?q=`) and has a "Share this search" button; every result
  and page has "Copy link". The person who asked "what's that meme called?" gets the answer as a link.
- **Embed and API.** `/embed/` is a search box any site can iframe (credits and links back); `/api/` documents free
  JSON files and the search module. Both are aimed at GitHub discovery (repo topics: meme, memes, meme-templates,
  meme-search, imgflip, search-engine, json-api, github-pages).

## First 1,000 users

There is no outreach in machine mode. Users come from search ("<template name> meme", "meme where…") and shared
links. Watch Search Console impressions (key 5) and the `search` → `imgflip_out` events (key 4) once those keys are
turned.
