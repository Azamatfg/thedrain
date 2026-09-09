#!/usr/bin/env python3
"""Render real `drain` output into a terminal-window PNG for the gallery.

    python3 assets/render_shot.py --date 2026-09-07 --out assets/gallery-1.png

Deliberately not a screenshot: reproducible, exact pixel size, and re-renderable
for every relaunch without hunting for a clean terminal.
"""
from __future__ import annotations
import argparse, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1270, 760
PAD_X, PAD_TOP = 54, 76
FONT = "/System/Library/Fonts/Menlo.ttc"

BG      = (10, 12, 10)
CHROME  = (22, 26, 22)
BORDER  = (46, 54, 44)
FG      = (214, 222, 210)
DIM     = (96, 108, 92)
GREY    = (140, 150, 136)
ACID    = (108, 255, 26)
LIME    = (182, 255, 61)
ORANGE  = (255, 154, 40)
RED     = (255, 106, 96)
CYAN    = (94, 226, 214)
WHITE   = (240, 248, 236)

ANSI = re.compile(r"\033\[[0-9;]*m")


def colour_for(line: str):
    """Pick a colour from the line's semantics — the ANSI is stripped by then."""
    s = line.strip()
    if s.startswith("──") or " ── " in line:            return DIM
    if "caching saved" in s:                             return ACID
    if s.startswith("▸"):                                return WHITE
    if any(s.startswith(x) for x in ("Pro ", "Max 5×", "Max 20×")):  return GREY
    if s.startswith("at API rates"):                     return RED
    if "tokens drained" in s:                            return ORANGE
    if "cache reads" in s or "cache writes" in s:        return CYAN
    if s.startswith("D R A I N") or "D R A I N" in s:    return ACID
    return FG


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-07")
    ap.add_argument("--out", default="assets/gallery-1.png")
    ap.add_argument("--size", type=int, default=17)
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = subprocess.run([sys.executable, os.path.join(root, "drain.py"),
                          "--date", a.date, "--no-anim"],
                         capture_output=True, text=True, env={**os.environ, "NO_COLOR": "1"})
    lines = [ANSI.sub("", l).rstrip() for l in raw.stdout.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    mono = ImageFont.truetype(FONT, a.size)
    small = ImageFont.truetype(FONT, 13)

    # window chrome
    d.rounded_rectangle([16, 16, W - 16, H - 16], radius=14, fill=BG, outline=BORDER, width=1)
    d.rounded_rectangle([16, 16, W - 16, 58], radius=14, fill=CHROME)
    d.rectangle([16, 44, W - 16, 58], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([42 + i * 22, 31, 54 + i * 22, 43], fill=c)
    d.text((W // 2 - 40, 30), "drain", font=small, fill=GREY)

    # body
    lh = a.size + 7
    y = PAD_TOP
    for ln in lines:
        if y > H - 46:
            break
        if ln.strip():
            d.text((PAD_X, y), ln, font=mono, fill=colour_for(ln))
        y += lh

    out = os.path.join(root, a.out) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print(f"{out}  {W}×{H}  ({len(lines)} lines)")


if __name__ == "__main__":
    main()
