# Describe a Meme

Find a meme by describing it. Type what you remember ("guy looking back at another girl", "dog in a burning room")
and get the meme's name, what it means, how it's used and a link to the blank template.

**Live:** https://theguysaccount.github.io/meme-search-engine/ · **API:** https://theguysaccount.github.io/meme-search-engine/api/

- 386 popular templates (plus 59 alternate uploads folded into their pages), each described by looking at the template: what it shows, the words on it, how people use
  it, and the ways people describe it when they don't know its name.
- Search runs in your browser (BM25 over the descriptions, plus synonyms, word forms, typos and compound words).
  Nothing you type is sent anywhere.
- A weekly trending list from Imgflip's public API, a page per template, browse pages, a free JSON API and an
  embeddable search box.
- No meme images are hosted here: pictures load from Imgflip with a link back.

## Run, test, deploy

```bash
python3 -m pip install pillow           # optional locally: per-template share cards
python3 pipeline/build.py               # build into dist/
python3 -m http.server -d dist 8000     # then open http://localhost:8000/ (or use scripts/e2e.sh, which serves the production path)
python3 -m unittest discover -s tests   # build, catalog and refresh tests
node --test tests/js/*.test.mjs                   # search tests and the search-quality eval
scripts/e2e.sh                          # drive the built site in headless Chrome
```

Deploys run on GitHub Actions (`.github/workflows/deploy.yml`) on every push to `main` and twice a week with a data
refresh. `OPERATIONS.md` covers every job, how it fails safe, and the switches (domain, sponsor, analytics).
`pipeline/CAPTIONING.md` is the brief for describing new templates.

## Data and licenses

Code: MIT. Template descriptions: CC BY 4.0. Template names and popularity: Imgflip's public API. Meme images belong
to their owners and are not in this repository. Corrections and removal requests: open an issue (there are forms).
