#!/usr/bin/env python3
"""burn — what your day with Claude Code actually cost.

Usage:
    python3 burn.py              today
    python3 burn.py --date 2026-09-08
    python3 burn.py --json       machine-readable, no animation
    python3 burn.py --no-anim    static render
"""
from __future__ import annotations

import argparse, json, os, shutil, sys, time
from datetime import date, datetime

from engine import scan_tokens, scan_git

# ─────────────────────────────────────────────────────────── colours

class C:
    R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
    ORANGE = "\033[38;5;208m"; RED = "\033[38;5;203m"; YEL = "\033[38;5;221m"
    GRN = "\033[38;5;114m"; CYA = "\033[38;5;80m"; GRY = "\033[38;5;245m"
    DIM = "\033[38;5;238m"; WHT = "\033[38;5;255m"

    @classmethod
    def off(cls):
        for k in list(vars(cls)):
            if k.isupper():
                setattr(cls, k, "")



# ─────────────────────────────────────────────────────────── legends
# Only numbers that can be defended. "~" marks a widely cited estimate.

def _load_legends():
    """Legends live in legends.json so anyone can add one with a pull request."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legends.json")
    try:
        with open(path, encoding="utf8") as f:
            raw = json.load(f)["legends"]
    except Exception:
        return [(10_239, "Linus Torvalds", "the Linux 0.01 kernel", 1991, True)]
    return sorted(((l["lines"], l["who"], l["what"], l["year"], l.get("exact", False))
                   for l in raw), key=lambda x: x[0])

LEGENDS = _load_legends()

def pick_legend(lines: int, day):
    """Closest legend by scale; rotates day to day among the near matches."""
    if lines <= 0: return None
    scored = sorted(LEGENDS, key=lambda x: abs((lines / x[0]) - 0.6))
    pool = scored[:3]
    return pool[day.toordinal() % len(pool)]

def next_target(lines: int):
    """The next legend you have not passed yet — the thing to beat tomorrow."""
    ahead = [l for l in LEGENDS if l[0] > lines]
    return ahead[0] if ahead else None

# ─────────────────────────────────────────────────────────── i18n

EN = {
 "sub": "what Claude did for you today",
 "tokens": "tokens burned", "cost": "at API rates", "calls": "model calls",
 "commits": "commits", "lines": "lines written",
 "where": "where the tokens went", "cache_r": "cache reads", "cache_w": "cache writes",
 "out": "model output", "inp": "fresh input",
 "think": "of that output, {a} tokens were thinking ({p}%)",
 "saved": "caching saved ${s}", "saved2": " — without it the day would have cost ${t}",
 "means": "what this means",
 "means1": "If you are on a Claude subscription, you did not pay this.",
 "means2": "This is what the day would cost at API rates.",
 "permo": "/mo", "payments": "today = {d} monthly payments",
 "models": "by model", "outp": "output", "where_w": "where it landed", "cmts": "commits",
 "scale": "for scale",
 "aloud_y": "reading this aloud without sleeping — {v} years",
 "aloud_d": "reading this aloud without sleeping — {v} days",
 "aloud_h": "reading this aloud — {v} hours",
 "lk_over": "{v}× the first Linux kernel (0.01, 1991 — 10,239 lines)",
 "lk_under": "{v}% of the first Linux kernel (0.01, 1991)",
 "lk10": "{v}% of Linux 1.0 (1994)",
 "lknow": "{v}% of the modern Linux kernel (40M lines)",
 "day_max": "one day = {v} months of Claude Max 20× at subscription price",
 "day_pro": "one day = {v} months of Claude Pro at subscription price",
 "rate": "{c} model calls — about {r} per minute over an eight-hour day",
 "foot": "burn · reads only ~/.claude on this machine. Nothing is sent anywhere.",
 "doom": "of the Doom 1993 source",
 "leg_over": "today you wrote {v}× {what} — what {who} built{y}",
 "leg_under": "today you wrote {v}% of {what} — what {who} built{y}",
 "leg_year": " in {y}", "approx": "~",
 "next": "{gap} lines to go before you pass {what} — {who}",
}
L = EN


# ─────────────────────────────────────────────────────────── helpers

def w() -> int:
    return min(shutil.get_terminal_size((80, 24)).columns, 76)

def num(n: float) -> str:
    return f"{int(n):,}"

def human(n: float) -> str:
    for lim, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= lim:
            return f"{n/lim:.1f}{suf}".replace(".0", "")
    return str(int(n))

def bar(frac: float, width: int, fill="█", empty="·") -> str:
    frac = max(0.0, min(1.0, frac))
    f = int(round(frac * width))
    return fill * f + empty * (width - f)

def count_up(label: str, target: float, fmt, colour: str, steps=22, delay=0.022, suffix=""):
    """Animate a number counting up in place."""
    if target <= 0:
        sys.stdout.write(f"  {label:<22} {colour}{fmt(0)}{suffix}{C.R}\n"); return
    for i in range(steps + 1):
        # ease-out
        v = target * (1 - (1 - i / steps) ** 3)
        sys.stdout.write(f"\r  {label:<22} {colour}{C.B}{fmt(v)}{suffix}{C.R}   ")
        sys.stdout.flush(); time.sleep(delay)
    sys.stdout.write("\n")

# ─────────────────────────────────────────────────────────── analogies

def analogies(tokens: float, lines: int, cost: float, calls: int, day=None) -> list[str]:
    """One analogy per dimension, chosen to match the order of magnitude."""
    out = []

    # volume: reading aloud lands better than "N books"
    words = tokens * 0.75
    minutes = words / 150            # average reading-aloud pace
    if minutes >= 60 * 24 * 365:
        out.append(L["aloud_y"].format(v=f"{minutes/(60*24*365):.1f}"))
    elif minutes >= 60 * 24:
        out.append(L["aloud_d"].format(v=f"{minutes/(60*24):.1f}"))
    elif minutes >= 60:
        out.append(L["aloud_h"].format(v=f"{minutes/60:.1f}"))

    # code: legend of the day + a Linux anchor
    if lines > 0:
        leg = pick_legend(lines, day)
        if leg:
            n, who, what, year, exact = leg
            label = what
            if not exact: label = L["approx"] + " " + label
            ratio = lines / n
            key = "leg_over" if ratio >= 1 else "leg_under"
            v = f"{ratio:.2f}" if ratio >= 1 else f"{ratio*100:.1f}"
            out.append(L[key].format(v=v, what=label, who=who,
                                     y=L["leg_year"].format(y=year)))
        nxt = next_target(lines)
        if nxt:
            n2, who2, what2, year2, _e2 = nxt
            out.append(L["next"].format(gap=f"{n2 - lines:,}", what=what2, who=who2))
        LNOW = 40_063_856
        out.append(L["lknow"].format(v=f"{lines/LNOW*100:.4f}"))

    # money: what it turns into
    if cost >= 200:
        out.append(L["day_max"].format(v=f"{cost/200:.1f}"))
    elif cost >= 20:
        out.append(L["day_pro"].format(v=f"{cost/20:.1f}"))

    # pace
    if calls > 100:
        out.append(L["rate"].format(c=f"{calls:,}", r=f"{calls/(8*60):.1f}"))

    return out


# ─────────────────────────────────────────────────────────── render

def render(day: date, tok: dict, git: dict, anim=True):
    t = tok["totals"]; W = w()
    if tok.get("missing"):
        print(f"\n  {C.YEL}No Claude Code transcripts found.{C.R}")
        print(f"  {C.GRY}Looked in: {tok['missing']}{C.R}")
        print(f"  {C.GRY}burn reads the logs Claude Code writes locally. Run Claude Code once,{C.R}")
        print(f"  {C.GRY}then try again. Nothing is downloaded and no account is needed.{C.R}\n")
        return
    if not t or t.get("total_tokens", 0) <= 0:
        print(f"\n  {C.GRY}Nothing recorded for {day.isoformat()}.{C.R}")
        print(f"  {C.GRY}Try another day:  burn --date YYYY-MM-DD{C.R}\n")
        return
    cost = t.get("cost", 0.0)
    total = t.get("total_tokens", 0.0)
    lines = git["added"]

    # экономия на кэше: чтение по 0.1× вместо 1×
    saved = 0.0
    for model, m in tok["by_model"].items():
        from engine import price_for
        inp, _out, rmul = price_for(model)
        saved += m.get("cache_r", 0) * inp * (1 - rmul) / 1e6

    print()
    title = "  B U R N  "
    pad = (W - len(title)) // 2
    print(f"{C.DIM}{'─'*pad}{C.R}{C.ORANGE}{C.B}{title}{C.R}{C.DIM}{'─'*(W-pad-len(title))}{C.R}")
    print(f"{C.GRY}  {L['sub']}{C.R}")
    print(f"{C.DIM}  {day.strftime('%d %B %Y')}{C.R}\n")

    if anim:
        count_up(L["tokens"], total, lambda v: num(v), C.ORANGE)
        count_up(L["cost"], cost, lambda v: f"${v:,.2f}", C.RED)
        count_up(L["calls"], t.get("calls", 0), lambda v: num(v), C.YEL)
        count_up(L["commits"], git["commits"], lambda v: num(v), C.GRN)
        count_up(L["lines"], lines, lambda v: num(v), C.GRN)
    else:
        for lbl, val, col in ((L["tokens"], num(total), C.ORANGE),
                              (L["cost"], f"${cost:,.2f}", C.RED),
                              (L["calls"], num(t.get("calls", 0)), C.YEL),
                              (L["commits"], num(git["commits"]), C.GRN),
                              (L["lines"], num(lines), C.GRN)):
            print(f"  {lbl:<22} {col}{C.B}{val}{C.R}")

    # ── из чего складывается объём
    print(f"\n{C.DIM}  ── {L['where']} {'─'*(W-len(L['where'])-6)}{C.R}")
    parts = [(L["cache_r"], t.get("cache_r", 0), C.CYA),
             (L["cache_w"], t.get("cache_w5", 0) + t.get("cache_w1", 0), C.YEL),
             (L["out"], t.get("output", 0), C.ORANGE),
             (L["inp"], t.get("input", 0), C.GRY)]
    for name, v, col in parts:
        if total <= 0: break
        frac = v / total
        print(f"  {name:<14} {col}{bar(frac, W-36)}{C.R} {human(v):>6} {C.DIM}{frac*100:5.1f}%{C.R}")

    if t.get("thinking", 0):
        th = t["thinking"]; ot = max(t.get("output", 1), 1)
        print(f"\n  {C.D}" + L["think"].format(a=human(th), p=f"{th/ot*100:.0f}") + f"{C.R}")

    # ── кэш спас
    if saved > 1:
        print(f"\n{C.GRN}{C.B}  " + L["saved"].format(s=f"{saved:,.2f}") + f"{C.R}{C.GRY}" + L["saved2"].format(t=f"{cost+saved:,.2f}") + f"{C.R}")

    # ── что это значит для подписчика
    api_value = cost + saved
    print(f"\n{C.DIM}  ── {L['means']} {'─'*(W-len(L['means'])-6)}{C.R}")
    print(f"  {C.GRY}{L['means1']}{C.R}")
    print(f"  {C.GRY}{L['means2']}{C.R}")
    for name, price in (("Pro", 20), ("Max 5×", 100), ("Max 20×", 200)):
        if cost <= 0: break
        days = cost / price
        mark = C.GRN + C.B if days >= 1 else C.GRY
        print(f"  {mark}{name:<10}${price:>4}{L['permo']}{C.R}  {C.DIM}"
              + L["payments"].format(d=f"{days:.1f}") + f"{C.R}")

    # ── по моделям
    real = {m: v for m, v in tok["by_model"].items() if not m.startswith("<")}
    if len(real) > 1:
        print(f"\n{C.DIM}  ── {L['models']} {'─'*(W-len(L['models'])-6)}{C.R}")
        for m, v in sorted(real.items(), key=lambda x: -x[1]["cost"]):
            print(f"  {m:<24} {C.RED}${v['cost']:>8,.2f}{C.R} {C.DIM}{human(v.get('output',0)):>6} {L['outp']}{C.R}")

    # ── репозитории
    if git["repos"]:
        print(f"\n{C.DIM}  ── {L['where_w']} {'─'*(W-len(L['where_w'])-6)}{C.R}")
        for r in git["repos"][:6]:
            print(f"  {r['repo']:<24} {C.GRN}+{num(r['added']):<9}{C.R}{C.RED}-{num(r['deleted']):<8}{C.R}"
                  f"{C.DIM}{r['commits']} {L['cmts']}{C.R}")

    # ── аналогии
    an = analogies(total, lines, cost, int(t.get('calls', 0)), day)
    if an:
        print(f"\n{C.DIM}  ── {L['scale']} {'─'*(W-len(L['scale'])-6)}{C.R}")
        for a in an:
            print(f"  {C.WHT}▸{C.R} {a}")

    print(f"\n{C.DIM}{'─'*W}{C.R}")
    print(f"{C.GRY}  {L['foot']}{C.R}\n")

# ─────────────────────────────────────────────────────────── main

def main():
    ap = argparse.ArgumentParser(description="what your day with Claude Code cost")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--no-git", action="store_true", help="skip repository scanning")
    a = ap.parse_args()

    day = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else date.today()
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        C.off()

    tok = scan_tokens(day)
    git = {"commits": 0, "added": 0, "deleted": 0, "repos": []} if a.no_git else scan_git(day)

    if a.json:
        print(json.dumps({"date": day.isoformat(), "tokens": tok, "git": git},
                         ensure_ascii=False, indent=2))
        return
    render(day, tok, git, anim=not a.no_anim and sys.stdout.isatty())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
