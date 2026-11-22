# Decisions

Defaults picked without blocking on Jack. Each can be reversed.

1. **Search engine first, no social app.** The note's open question ("search engine first, or a meme social app?")
   is settled by the machine-driven brief: a social app needs moderation staff and accounts. A search page has
   strangers arriving with a real need ("what's that meme called?") and no upkeep beyond new templates.
2. **Describe-a-meme, not vision search at query time.** The vision work happens once, ahead of time: an agent
   looked at every template and wrote what it shows, the words on it, how it's used and how people describe it
   without knowing its name (`pipeline/CAPTIONING.md`). Visitors' queries then run against that text with a small
   BM25 ranker plus synonyms, word forms, typos and compound words (`site/assets/core.js`). No model, key or server
   at query time, and nothing a visitor types leaves the browser.
3. **Imgflip as the template list.** Its free API (`get_memes`, no key) gives the 100 most-captioned templates of
   the last 30 days; its public "top all time" pages seeded the catalog with ~480 templates. Both are allowed by its
   robots.txt and fetched slowly with an identifying User-Agent.
4. **Images are hotlinked from Imgflip, never hosted.** Meme pictures belong to photographers and studios. Imgflip's
   terms allow embedding its images with a link back; every picture here links to the template's Imgflip page.
   `EMBED_IMAGES=0` (repository variable) switches the whole site to text links; `"embed": false` does it for one
   template (removal requests). Share cards are text only. Unreviewed trending templates never get a picture.
5. **Content rules over completeness.** 16 popular templates were left out before captioning (slurs, ethnic
   stereotypes, adult origins, real tragedy and violence, hate-symbol associations, utility blanks) and 7 more by the
   captioning pass (real violence or tragedy, a harassment joke, unidentifiable images). All 23 are listed with reasons
   in `data/moderation.json`. 4 entries the captioners weren't sure about (Dancing Monkeys, FINALLY, Rage Table Smash,
   Unicorn Man) are held back for review rather than published with a possibly wrong name.
6. **Private people stay nameless.** Ordinary people who became memes are described by the meme's name only.
   Actors, characters and public figures are named, because that's how people search for them.
7. **Versions fold into one page.** Imgflip has several uploads of some templates (Drake, Spider-Man pointing,
   Woman Yelling at Cat); they become one page whose "other versions" link to each upload, and their names still
   find the page.
8. **Brand "Describe a Meme"** says the job in three words and keeps the repo name for GitHub discovery. The note's
   names (Memegram, MemeNews, Telememe) suit a social app that isn't being built.
9. **MemeNews and the "Always Has Been" bot are cut.** Both need posting as an account, which machine mode rules out.
10. **Money stays a slot.** GitHub Pages is non-commercial; a sponsor box hidden behind `SPONSOR_URL` is the one
    switch. A paid API (the note's "become like Giphy") needs other hosting and Stripe: a decision for Jack.
11. **Quality is measured, not assumed.** `tests/eval.json` holds 123 descriptions written before the catalog text
    existed; the first measurement was 97.5% right first and 100% in the top 3. `tests/js/eval.test.mjs` fails the
    deploy below 85% first or 93% top 3.

## Questions for Jack (none block the site)

- Should this tie into Gif Studios (a "find that meme" box on gifstudios.com, or `memes.gifstudios.com`)?
- Is a paid API worth other hosting, or should the money slot carry a sponsor?
