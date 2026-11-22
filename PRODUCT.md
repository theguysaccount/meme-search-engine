# Product: Describe a Meme

**The user.** Anyone who remembers a meme but not its name: the friend who asks "what's the meme where the guy looks
back at another girl?", a social media manager who needs the blank template, someone who saw a reference and wants
to know what it means.

**The painful job.** Meme search on GIPHY, Tenor, Imgflip and Know Your Meme works by name and tags. If you don't
know the name, you scroll, or you ask someone.

**The promise.** Describe it in your own words, get the name, what it means and the blank template in one search.

**The wedge.** Pages people already search for: one page per template ("Distracted Boyfriend meme: what it's called,
what it means, blank template") plus the describe-it box no incumbent has. Every result and page has a link to
copy and send, which answers the friend who asked; a free JSON API and an embeddable search box spread it further.

**Why now.** Vision models can look at a template once and write what people actually remember about it; doing that
for ~450 templates took one batch of agent sessions, and it runs as a static site at no cost.

**The one activation metric.** A visitor runs a search and opens a result's template on Imgflip or copies its link
(`search` → `imgflip_out` / `copy_link` events, once analytics is on; OPERATIONS.md key 4).

**First revenue event.** A sponsor in the slot on template pages (`SPONSOR_URL`), or a paid API tier on other
hosting if Jack wants one.

**What v1 deliberately won't do.** No social app, no uploads, no accounts, no hosting of meme images, no meme
generator (Imgflip does that; we link to it), no MemeNews or auto-posting bots, no NSFW or hateful templates.
