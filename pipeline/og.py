"""Open Graph share cards (1200x630 PNG), text only: the site never hosts meme images, so a card shows the
template's name and what it looks like, not the picture.

Needs Pillow (`pip install pillow`). build.py skips per-template cards when it's missing.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TITLE_FONT = HERE / "fonts" / "Anton-Regular.ttf"
BODY_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]
BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]
W, H = 1200, 630
INK, PAPER, YELLOW, SOFT = (27, 26, 33), (251, 250, 246), (255, 214, 10), (93, 90, 104)


def _font(candidates, size):
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(str(c), size)
    return ImageFont.load_default(size=size)


def _wrap(draw, text, font, width, max_lines):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = w
        if len(lines) == max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    used = sum(len(x.split()) for x in lines)
    if used < len(words) and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = last.rstrip(",;:") + "…"
    return lines


def card(path, title, body, footer, kicker="DESCRIBE A MEME"):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 28, H], fill=YELLOW)
    d.rectangle([28, H - 92, W, H], fill=INK)
    kick = _font(BOLD_FONTS, 30)
    d.rounded_rectangle([72, 52, 72 + d.textlength(kicker, font=kick) + 28, 102], radius=10, fill=YELLOW)
    d.text((86, 58), kicker, font=kick, fill=INK)
    size, lines = 104, []
    while size >= 56:
        tf = ImageFont.truetype(str(TITLE_FONT), size)
        lines = _wrap(d, title.upper(), tf, W - 150, 2 if size > 80 else 3)
        if " ".join(lines).replace("…", "") == title.upper() or size == 56:
            break
        size -= 8
    y = 130
    for line in lines:
        d.text((72, y), line, font=tf, fill=INK)
        y += int(size * 1.16)
    y += 22
    bf = _font(BODY_FONTS, 32)
    room = max(1, min(4, (H - 112 - y) // 44))
    for line in _wrap(d, body, bf, W - 150, room):
        d.text((72, y), line, font=bf, fill=SOFT)
        y += 44
    ff = _font(BOLD_FONTS, 28)
    d.text((72, H - 64), footer, font=ff, fill=PAPER)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def first_sentence(text):
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return m.group(1) if m else text


def render_all(templates, out_dir, site_url):
    out_dir = Path(out_dir)
    host = re.sub(r"^https?://", "", site_url).rstrip("/")
    card(out_dir / "home.png", "Describe a meme. Get its name.",
         "Type what you remember: who's in it, what they're doing, any words on it.", host)
    for t in templates:
        card(out_dir / f"{t['slug']}.png", t["name"], t["look"], f"What it's called, what it means · {host}")
    return True
