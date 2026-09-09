#!/usr/bin/env python3
"""Build every Product Hunt gallery frame. One idea per frame.

    python3 assets/render_gallery.py
"""
from __future__ import annotations
import os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1270, 760
FONT = "/System/Library/Fonts/Menlo.ttc"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")

BG     = (9, 11, 9)
PANEL  = (13, 16, 13)
CHROME = (22, 26, 22)
BORDER = (44, 52, 42)
FG     = (212, 220, 208)
DIM    = (86, 98, 82)
GREY   = (136, 148, 132)
ACID   = (99, 255, 16)
LIME   = (180, 255, 60)
ORANGE = (255, 154, 40)
RED    = (255, 106, 96)
CYAN   = (94, 226, 214)
WHITE  = (242, 250, 238)

ANSI = re.compile(r"\033\[[0-9;]*m")


def drain(*args) -> list[str]:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "drain.py"), *args],
                       capture_output=True, text=True,
                       env={**os.environ, "NO_COLOR": "1"})
    return [ANSI.sub("", l).rstrip() for l in r.stdout.split("\n")]


def section(lines, start_marker, stop_marker=None):
    """Pull one '── heading ──' block out of the output."""
    out, on = [], False
    for l in lines:
        if start_marker in l:
            on = True
            out.append(l)
            continue
        if on:
            if stop_marker and stop_marker in l:
                break
            if l.strip().startswith("──") and start_marker not in l:
                break
            out.append(l)
    return [l for l in out]


LOGO = os.path.join(OUT, "wordmark.png")

def canvas(headline: str, sub: str = "", logo=True):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    top = 58
    if logo and os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGB")
        bb = lg.point(lambda v: 0 if v < 14 else 255).convert("L").getbbox()
        if bb:
            lg = lg.crop(bb)
        h = 54
        lg = lg.resize((int(lg.width * h / lg.height), h), Image.LANCZOS)
        img.paste(lg, (62, 44))
        top = 128
    head = ImageFont.truetype(FONT, 38)
    subf = ImageFont.truetype(FONT, 18)
    d.text((64, top), headline, font=head, fill=WHITE)
    if sub:
        d.text((64, top + 52), sub, font=subf, fill=GREY)
    return img, d


def terminal(d: ImageDraw.ImageDraw, lines, x, y, w, h, size=17, colour=None):
    d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=PANEL, outline=BORDER, width=1)
    d.rounded_rectangle([x, y, x + w, y + 34], radius=12, fill=CHROME)
    d.rectangle([x, y + 22, x + w, y + 34], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x + 16 + i * 18, y + 12, x + 26 + i * 18, y + 22], fill=c)
    mono = ImageFont.truetype(FONT, size)
    ly = y + 54
    for l in lines:
        if ly > y + h - 24:
            break
        if l.strip():
            d.text((x + 26, ly), l, font=mono, fill=(colour(l) if colour else FG))
        ly += size + 7
    return ly


def main():
    full = drain("--date", "2026-09-07", "--no-anim")
    while full and not full[0].strip():
        full.pop(0)

    # ── frame 2: the cache revelation
    def c2(l):
        s = l.strip()
        if "caching saved" in s: return ACID
        if "cache reads" in s or "cache writes" in s: return CYAN
        if s.startswith("──") or " ── " in l: return DIM
        return FG
    img, d = canvas("98% of it was cache.",
                    "The bill everyone fears is mostly reads at a tenth of the input rate.")
    body = section(full, "where the tokens went")
    terminal(d, body, 64, 246, W - 128, 330, colour=c2)
    big = ImageFont.truetype(FONT, 54)
    d.text((64, 612), "$3,877.28 saved in one day", font=big, fill=ACID)
    d.text((64, 678), "If your cache-read share is low, something in your prompt prefix is changing.",
           font=ImageFont.truetype(FONT, 17), fill=GREY)
    img.save(f"{OUT}/gallery-2.png")

    # ── frame 3: the competition
    def c3(l):
        s = l.strip()
        if s.startswith("▸"): return LIME
        if s.startswith("──") or " ── " in l: return DIM
        return FG
    img, d = canvas("Race the people who built the tools.",
                    "Your day, measured against code you already have a feel for.")
    body = section(full, "for scale")
    terminal(d, body, 64, 246, W - 128, 264, size=17, colour=c3)
    d.text((64, 546), "The first Linux kernel was 10,239 lines.",
           font=ImageFont.truetype(FONT, 34), fill=WHITE)
    d.text((64, 596), "A normal day with an agent now passes what Torvalds released in 1991.",
           font=ImageFont.truetype(FONT, 20), fill=GREY)
    d.text((64, 664), "legends.json — send a pull request with the one you want to race.",
           font=ImageFont.truetype(FONT, 17), fill=ACID)
    img.save(f"{OUT}/gallery-3.png")

    # ── frame 4: install + privacy
    img, d = canvas("Two commands. Nothing leaves the machine.",
                    "No account, no API key, no network calls, no tokens spent.")
    install = [
        "$ brew install Azamatfg/tap/thedrain",
        "",
        "  or, without Homebrew:",
        "",
        "$ curl -fsSL https://raw.githubusercontent.com/\\",
        "         Azamatfg/thedrain/main/install.sh | bash",
        "",
        "$ drain",
    ]
    def c4(l):
        if l.strip().startswith("$"): return ACID
        return GREY
    terminal(d, install, 64, 246, W - 128, 262, size=18, colour=c4)
    facts = [
        ("reads", "~/.claude transcripts Claude Code already writes, and your git log"),
        ("sends", "nothing — there is not a single network call in the source"),
        ("costs", "zero tokens; asking a model would be like calling the bank to"),
        ("", "read your own statement"),
        ("needs", "Python 3.9+, no third-party dependencies"),
    ]
    y = 546
    kf = ImageFont.truetype(FONT, 19)
    vf = ImageFont.truetype(FONT, 19)
    for k, v in facts:
        if k:
            d.text((64, y), f"{k:<7}", font=kf, fill=ACID)
        d.text((64 + 100, y), v, font=vf, fill=FG if k else GREY)
        y += 34
    img.save(f"{OUT}/gallery-4.png")

    for n in (1, 2, 3, 4):
        p = f"{OUT}/gallery-{n}.png"
        if os.path.exists(p):
            print(f"  gallery-{n}.png  {Image.open(p).size}")


if __name__ == "__main__":
    main()
