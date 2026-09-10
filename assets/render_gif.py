#!/usr/bin/env python3
"""Render the count-up animation into a GIF for the README and the gallery.

    python3 assets/render_gif.py --date 2026-09-07 --out assets/demo.gif

Frames are drawn from real `drain` output, so the GIF cannot drift from what the
tool actually prints. Needs ffmpeg on PATH.
"""
from __future__ import annotations
import argparse, os, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_shot import (W, H, PAD_X, PAD_TOP, FONT, BG, CHROME, BORDER, GREY,
                         ANSI, colour_for)

NUM = re.compile(r"(\$?)(\d[\d,]*)(\.\d+)?")
EASE = lambda t: 1 - (1 - t) ** 3          # same curve as count_up in drain.py


def ramp(line: str, t: float) -> str:
    """Scale the first number on the line to t of its value, keeping the layout."""
    m = NUM.search(line)
    if not m:
        return line
    dollar, whole, frac = m.group(1), m.group(2), m.group(3) or ""
    target = float(whole.replace(",", "") + frac)
    v = target * t
    shown = f"{v:,.2f}" if frac else f"{int(v):,}"
    return line[:m.start()] + dollar + shown + line[m.end():]


def bar_fill(line: str, t: float) -> str:
    """Drain the bar back to t of its length; the block chars are contiguous."""
    m = re.search(r"[█]+", line)
    if not m:
        return line
    n = m.end() - m.start()
    k = max(0, int(round(n * t)))
    return line[:m.start()] + "█" * k + "·" * (n - k) + line[m.end():]


def draw(lines, size, upto, ramp_t, bar_t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    mono = ImageFont.truetype(FONT, size)
    small = ImageFont.truetype(FONT, 13)

    d.rounded_rectangle([16, 16, W - 16, H - 16], radius=14, fill=BG, outline=BORDER, width=1)
    d.rounded_rectangle([16, 16, W - 16, 58], radius=14, fill=CHROME)
    d.rectangle([16, 44, W - 16, 58], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([42 + i * 22, 31, 54 + i * 22, 43], fill=c)
    d.text((W // 2 - 40, 30), "drain", font=small, fill=GREY)

    lh, y = size + 7, PAD_TOP
    for i, ln in enumerate(lines):
        if y > H - 46:
            break
        if i < upto and ln.strip():
            out = ln
            if i in HEAD:
                out = ramp(out, ramp_t)
            elif "█" in ln or "·" in ln:
                out = bar_fill(out, bar_t)
            d.text((PAD_X, y), out, font=mono, fill=colour_for(ln))
        y += lh
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-07")
    ap.add_argument("--out", default="assets/demo.gif")
    ap.add_argument("--size", type=int, default=17)
    ap.add_argument("--fps", type=int, default=14)
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = subprocess.run([sys.executable, os.path.join(root, "drain.py"),
                          "--date", a.date, "--no-anim"],
                         capture_output=True, text=True,
                         env={**os.environ, "NO_COLOR": "1"})
    lines = [ANSI.sub("", l).rstrip() for l in raw.stdout.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)

    global HEAD
    stop = next((i for i, l in enumerate(lines) if "──" in l and "D R A I N" not in l),
                len(lines))
    HEAD = [i for i, l in enumerate(lines[:stop])
            if re.search(r"\S\s{2,}\$?\d", l) and "█" not in l and "·" not in l]
    if not HEAD:
        sys.exit("no headline metrics found — has the output changed?")
    first_bar = next((i for i, l in enumerate(lines) if "█" in l), len(lines))
    tail = len(lines)

    # The first frame doubles as the poster: galleries that do not autoplay show
    # frame zero, and a half-drawn screen reads as a broken image there.
    plan = [(tail, 1.0, 1.0)]                  # (upto, ramp_t, bar_t)
    head_end = max(HEAD) + 1
    for i in range(3):                         # header lands
        plan.append((min(head_end - len(HEAD) + i, head_end), 0.0, 0.0))
    for i in range(20):                        # numbers count up
        plan.append((head_end, EASE((i + 1) / 20), 0.0))
    for i in range(8):                         # bars fill
        plan.append((first_bar + 5, 1.0, EASE((i + 1) / 8)))
    for i in range(6):                         # the rest arrives
        plan.append((first_bar + 5 + int((tail - first_bar - 5) * (i + 1) / 6), 1.0, 1.0))
    plan += [(tail, 1.0, 1.0)] * (a.fps * 3)   # hold three seconds

    tmp = tempfile.mkdtemp(prefix="draingif_")
    for n, (upto, rt, bt) in enumerate(plan):
        draw(lines, a.size, upto, rt, bt).save(os.path.join(tmp, f"{n:04d}.png"))

    out = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    vf = f"fps={a.fps},split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-framerate", str(a.fps), "-i", os.path.join(tmp, "%04d.png"),
                        "-vf", vf, "-loop", "0", out], capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        sys.exit(r.stderr.strip() or "ffmpeg failed")
    print(f"{out}  {W}×{H}  {len(plan)} frames  {os.path.getsize(out)//1024} KB")


if __name__ == "__main__":
    main()
