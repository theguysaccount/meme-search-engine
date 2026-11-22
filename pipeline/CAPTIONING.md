# Captioning spec: meme template catalog

This is the brief for writing catalog entries, whether by an agent session or by hand. People who remember
what a meme looks like but not what it's called type a description; each entry is what their words are
matched against, and it is also published as that template's page. Accuracy matters more than flair.

## The batch

A batch file is a JSON list. Each item has `id` (Imgflip template id), `name` (the name Imgflip users gave
it; often sloppy), `view` (path of a local JPEG of the blank template), `boxes` (Imgflip's default text-box
count, when known) and sometimes `hint`.

For every item:
1. Open the image and look at it. Describe what is actually in the picture, not what you remember:
   colours, who is where, panel order, any words printed on the blank template.
2. Write one entry (schema below).
3. Write all entries, in batch order, as a JSON list to the output path you were given.
4. Run the validator and fix what it reports until it prints `OK`:
   `python3 pipeline/validate_captions.py <output file> <batch file>`

Don't search the web. If you can't tell what a template is, say so in `exclude` instead of guessing.

## Entry schema (all keys required)

```json
{
  "id": "112126428",
  "name": "Distracted Boyfriend",
  "aka": ["Man Looking at Other Woman", "Guy Checking Out Another Girl"],
  "look": "A stock photo on a city street. A man in a blue plaid shirt walks hand in hand with his girlfriend but turns his head to check out a woman in a red dress walking the other way. The girlfriend, in a light blue top, stares at him in shocked disgust.",
  "text": [],
  "use": "Each of the three people gets a label. The man is someone who should stay committed, the girlfriend is the thing he's neglecting, and the woman in red is the tempting new thing.",
  "slots": ["the tempting new thing (woman in red)", "whoever is tempted (the man)", "what gets neglected (the girlfriend)"],
  "examples": [["Starting a new project", "Me", "The five projects I already started"]],
  "describe": [
    "guy looking back at another girl while his girlfriend looks mad",
    "man turns around to check out woman in red dress",
    "boyfriend staring at another woman and his girlfriend is upset",
    "couple walking and the guy whistles at a girl passing by"
  ],
  "tags": ["stock photo", "couple", "jealousy", "temptation", "street", "red dress"],
  "kind": "photo",
  "format": "labels",
  "panels": 1,
  "franchise": null,
  "origin": "A 2015 stock photo; it took off as a meme in 2017.",
  "people": "models",
  "variant_of": null,
  "exclude": null,
  "sure": "high"
}
```

Field rules:

- `name`: the name most people use for this meme, in Title Case. Fix Imgflip's sloppy names
  ("black guy pointing at head" is "Roll Safe"; "Math lady/Confused lady" is "Confused Math Lady").
  Keep an established name even if it has mild profanity.
- `aka`: 0 to 4 other names people really use, including Imgflip's name if you changed it. Don't invent names.
- `look`: what you see, 20 to 60 words, plain present tense. Mention the panel layout for multi-panel
  templates ("Four panels in a 2x2 grid: ..."). Name the character or actor when that is how people know it
  (see `people`). No opinions.
- `text`: words printed on the blank template itself, as a list of strings in reading order
  (["CHANGE MY MIND"]). Empty list if none. Ignore watermarks and artist signatures.
- `use`: how the joke works and what the labels or captions usually stand for, 15 to 60 words.
- `slots`: one short string per text area, in the order people fill them (top to bottom, left to right).
  Say what goes there and where it sits. 1 to 6 slots.
- `examples`: 1 or 2 original, clean, funny fills. Each example is a list with exactly one string per
  slot. Nothing about real people, politics, religion, sex, race, body shaming or tragedy.
- `describe`: 4 to 6 phrases, each 4 to 16 words, lowercase, written the way someone who forgot the name
  would type it into a search box. Vary the vocabulary between phrases (guy/man/dude, looks at/stares
  at/checks out). Don't use the meme's name or aka in these, unless the name is just the literal
  description. Include one phrase that mentions the text on the image if it has any.
- `tags`: 5 to 9 lowercase tags, 1 to 3 words each: subjects, emotions, setting, colours, structure.
- `kind`: one of `photo`, `screenshot` (still from a film, TV show or video with real people),
  `cartoon` (still from an animated show or film), `comic` (drawn comic or webcomic panels),
  `drawing` (crude or simple drawings: rage faces, wojaks, MS Paint), `game` (video game screenshot or
  render), `render` (3D render or CGI that isn't from a show or game), `graphic` (chart, sign, screen, UI,
  text layout), `other`.
- `format`: one of `top-bottom` (classic caption above and below one image), `labels` (labels placed on
  people or things in one image), `panels` (a sequence of panels telling a tiny story), `versus`
  (two or more options compared: reject/approve, weak/strong), `ladder` (a ranked escalation such as
  Expanding Brain), `sign` (your text goes on a sign, board, screen, paper or button in the image),
  `reaction` (a reaction face or moment with one caption), `other`.
- `panels`: number of panels in the blank template (1 for a single image).
- `franchise`: the film, TV show, game, comic or brand the image comes from, in its common form
  ("SpongeBob SquarePants", "The Simpsons", "Star Wars", "The Office (US)", "Marvel", "Toy Story"),
  or null. Only when you are sure.
- `origin`: one sentence, at most 30 words, with facts you are sure about: the work and scene it comes
  from, the year, who drew it. Use "" when unsure. Never guess a year.
- `people`: who is shown. One of `none` (no people: animals, objects, graphics), `fictional` (cartoon,
  drawn or CGI characters), `actor` (actors in a film or TV role), `public` (a public figure as
  themselves: politicians, athletes, musicians, TV hosts, famous creators), `private` (an ordinary person
  who became a meme, including children), `models` (stock-photo models or unidentified people).
  - `private` and `models`: NEVER write a real name anywhere in the entry. Use the meme's name only.
  - `actor` and `public`: you may name the actor, character or public figure.
- `variant_of`: if this image is just another version (blank, widescreen, cropped, redrawn, recoloured)
  of a meme that appears elsewhere in the full template list you were given, put that other template's
  name here, exactly as it appears in the full list, and still fill in every field. Otherwise null.
- `exclude`: null, or a short reason when the template must not be published. Exclude when the image or
  its usual joke: is sexual or from adult content; uses slurs or hate symbols; mocks a group for race,
  ethnicity, nationality, religion, gender, sexuality or disability as its core joke; shows or jokes
  about a real tragedy, real violence or a real person's death; promotes self-harm or hard drugs; is
  only a blank canvas or utility graphic with no recognisable meme; or you can't tell what it is.
  When you exclude, the other fields may be minimal but must still be present.
- `sure`: `high`, `medium` or `low`: how sure you are that the name and origin are right.

Style: plain words, American English, no hype, no emoji, no semicolons in `describe`. Describe people
respectfully. When skin colour, age or gender is how people commonly describe the meme, you may mention it
neutrally in `look` and `describe` ("a Black man in a suit taps his temple and smiles").

## After a batch

`python3 pipeline/merge_captions.py <output files...>` turns validated entries into `data/templates/<slug>.json`
(new templates only; it never overwrites an existing file) and adds excluded ids to `data/moderation.json`.
Then run the tests and `python3 pipeline/build.py`.
