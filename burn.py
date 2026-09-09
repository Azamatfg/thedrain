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
# Только числа, которые можно защитить. «≈» — широко цитируемая оценка.

LEGENDS = [
 # (строк, автор, проект, год, точное?)
 (1_244,      "Linus Torvalds",        ("первого коммита git",      "the first commit of git"),      2005, True),
 (10_239,     "Linus Torvalds",        ("ядра Linux 0.01",          "the Linux 0.01 kernel"),        1991, True),
 (39_000,     "John Carmack",          ("движка Doom",              "the Doom engine"),              1993, False),
 (145_000,    "команда Маргарет Хэмилтон", ("бортового компьютера Apollo 11", "the Apollo 11 flight computer"), 1969, True),
 (156_000,    "D. Richard Hipp",       ("SQLite",                   "SQLite"),                       2000, False),
 (176_250,    "Linus Torvalds",        ("ядра Linux 1.0",           "the Linux 1.0 kernel"),         1994, True),
 (200_000,    "Salvatore Sanfilippo",  ("Redis",                    "Redis"),                        2009, False),
 (1_400_000,  "команда PostgreSQL",    ("PostgreSQL",               "PostgreSQL"),                   1996, False),
 (5_000_000,  "команда Kubernetes",    ("Kubernetes",               "Kubernetes"),                   2014, False),
 (40_063_856, "тысячи людей за 34 года", ("современного ядра Linux", "the modern Linux kernel"),      2025, True),
]

def pick_legend(lines: int, day):
    """Легенда, ближайшая по масштабу. Меняется день ото дня среди подходящих."""
    if lines <= 0: return None
    scored = sorted(LEGENDS, key=lambda x: abs((lines / x[0]) - 0.6))
    pool = scored[:3]
    return pool[day.toordinal() % len(pool)]

# ─────────────────────────────────────────────────────────── i18n

RU = {
 "sub": "сколько Claude отработал за вас сегодня",
 "tokens": "токенов сожжено", "cost": "по тарифам API это", "calls": "вызовов к модели",
 "commits": "коммитов", "lines": "строк написано",
 "where": "куда ушли токены", "cache_r": "чтение кэша", "cache_w": "запись в кэш",
 "out": "вывод модели", "inp": "свежий ввод",
 "think": "из вывода {a} токенов — размышления ({p}%)",
 "saved": "кэш сэкономил ${s}", "saved2": " — без него день стоил бы ${t}",
 "means": "что это значит",
 "means1": "Если вы на подписке Claude — вы не платили эти деньги.",
 "means2": "Столько стоил бы этот день, если считать по тарифам API.",
 "permo": "/мес", "payments": "сегодняшний день = {d} месячных платежей",
 "models": "по моделям", "outp": "вывода", "where_w": "где писалось", "cmts": "коммитов",
 "scale": "для масштаба",
 "aloud_y": "читать это вслух без сна — {v} года", "aloud_d": "читать это вслух без сна — {v} суток",
 "aloud_h": "читать это вслух — {v} часа",
 "lk_over": "{v}× первого ядра Linux (0.01, 1991 — 10 239 строк)",
 "lk_under": "{v}% первого ядра Linux (0.01, 1991)",
 "lk10": "{v}% ядра Linux 1.0 (1994)",
 "lknow": "{v}% современного ядра Linux (40 млн строк)",
 "day_max": "один день = {v} месяца Claude Max 20× по цене подписки",
 "day_pro": "один день = {v} месяца Claude Pro по цене подписки",
 "rate": "{c} обращений к модели — примерно {r} в минуту за восьмичасовой день",
 "foot": "burn · читает только ~/.claude на этой машине. Ничего не отправляет.",
 "doom": "исходников Doom 1993",
 "leg_over": "сегодня вы написали {v}× {what} — то, что {who} сделал{y}",
 "leg_under": "сегодня вы написали {v}% {what} — того, что {who} сделал{y}",
 "leg_year": " в {y} году", "approx": "≈",
}
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
 "leg_year": " in {y}", "approx": "≈",
}
L = EN


# ─────────────────────────────────────────────────────────── helpers

def w() -> int:
    return min(shutil.get_terminal_size((80, 24)).columns, 76)

def num(n: float) -> str:
    return f"{int(n):,}".replace(",", " ")

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
    """Одна аналогия на измерение, подобранная под порядок величины."""
    out = []

    # ── объём: чтение вслух ощущается лучше, чем «N книг»
    words = tokens * 0.75
    minutes = words / 150            # средний темп чтения вслух
    if minutes >= 60 * 24 * 365:
        out.append(L["aloud_y"].format(v=f"{minutes/(60*24*365):.1f}"))
    elif minutes >= 60 * 24:
        out.append(L["aloud_d"].format(v=f"{minutes/(60*24):.1f}"))
    elif minutes >= 60:
        out.append(L["aloud_h"].format(v=f"{minutes/60:.1f}"))

    # ── код: легенда дня + якорь на ядре Linux
    if lines > 0:
        leg = pick_legend(lines, day)
        if leg:
            n, who, what, year, exact = leg
            label = what[0] if L is RU else what[1]
            if not exact: label = L["approx"] + " " + label
            ratio = lines / n
            key = "leg_over" if ratio >= 1 else "leg_under"
            v = f"{ratio:.2f}" if ratio >= 1 else f"{ratio*100:.1f}"
            out.append(L[key].format(v=v, what=label, who=who,
                                     y=L["leg_year"].format(y=year)))
        LNOW = 40_063_856
        out.append(L["lknow"].format(v=f"{lines/LNOW*100:.4f}"))

    # ── деньги: во что это превращается
    if cost >= 200:
        out.append(L["day_max"].format(v=f"{cost/200:.1f}"))
    elif cost >= 20:
        out.append(L["day_pro"].format(v=f"{cost/20:.1f}"))

    # ── темп
    if calls > 100:
        out.append(L["rate"].format(c=f"{calls:,}".replace(",", " "), r=f"{calls/(8*60):.1f}"))

    return out


# ─────────────────────────────────────────────────────────── render

def render(day: date, tok: dict, git: dict, anim=True):
    t = tok["totals"]; W = w()
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
    ap.add_argument("--date", help="YYYY-MM-DD (по умолчанию сегодня)")
    ap.add_argument("--json", action="store_true", help="машинный вывод")
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--no-git", action="store_true", help="skip repository scanning")
    ap.add_argument("--ru", action="store_true", help="русский вывод")
    a = ap.parse_args()

    global L
    if a.ru or (not a.json and os.environ.get("LANG","").startswith("ru")): L = RU
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
