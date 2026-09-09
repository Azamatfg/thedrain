"""Core: считает токены, деньги, коммиты и строки за день."""
from __future__ import annotations
import json, os, subprocess, sys
from collections import defaultdict
from datetime import datetime, timezone, date
from pathlib import Path

# $/1M токенов. Кэш: запись 5м ×1.25, запись 1ч ×2, чтение ×0.1.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0, 0.025), "claude-fable-5": (10.0, 50.0, 0.1),
    "claude-mythos-5-1": (10.0, 50.0, 0.1),
    "claude-opus-5": (5.0, 25.0, 0.1), "claude-opus-4-8": (5.0, 25.0, 0.1),
    "claude-opus-4-7": (5.0, 25.0, 0.1), "claude-opus-4-6": (5.0, 25.0, 0.1),
    "claude-sonnet-5": (2.0, 10.0, 0.1), "claude-sonnet-4-6": (3.0, 15.0, 0.1),
    "claude-haiku-4-5": (1.0, 5.0, 0.1),
}
DEFAULT = (5.0, 25.0, 0.1)

def price_for(model: str):
    if not model: return DEFAULT
    m = model.split("[")[0]
    if m in PRICES: return PRICES[m]
    for k, v in PRICES.items():
        if m.startswith(k): return v
    return DEFAULT

def scan_tokens(day: date, root: Path | None = None) -> dict:
    root = root or Path.home() / ".claude" / "projects"
    if not root.exists():
        return {"totals": {}, "by_model": {}, "missing": str(root)}
    tot = defaultdict(float)
    by_model = defaultdict(lambda: defaultdict(float))
    seen = set()
    for f in root.rglob("*.jsonl"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime).date() < day: continue
        except OSError: continue
        for line in f.open(encoding="utf8", errors="ignore"):
            if '"usage"' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            if d.get("type") != "assistant": continue
            ts = d.get("timestamp")
            if ts:
                try:
                    if datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date() != day: continue
                except Exception: pass
            msg = d.get("message") or {}
            u = msg.get("usage") or {}
            if not u: continue
            key = msg.get("id") or d.get("uuid")
            if key:
                if key in seen: continue
                seen.add(key)
            model = msg.get("model") or "claude-opus-5"
            cc = u.get("cache_creation") or {}
            w5 = cc.get("ephemeral_5m_input_tokens", 0)
            w1 = cc.get("ephemeral_1h_input_tokens", 0)
            if not (w5 or w1): w5 = u.get("cache_creation_input_tokens", 0)
            row = {
                "input": u.get("input_tokens", 0),
                "cache_w5": w5, "cache_w1": w1,
                "cache_r": u.get("cache_read_input_tokens", 0),
                "output": u.get("output_tokens", 0),
                "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0),
                "calls": 1,
            }
            inp, out, rmul = price_for(model)
            row["cost"] = (row["input"]*inp + row["cache_w5"]*inp*1.25 + row["cache_w1"]*inp*2
                           + row["cache_r"]*inp*rmul + row["output"]*out) / 1e6
            for k, v in row.items():
                tot[k] += v; by_model[model][k] += v
    tot["total_tokens"] = sum(tot[k] for k in ("input","cache_w5","cache_w1","cache_r","output"))
    return {"totals": dict(tot), "by_model": {m: dict(v) for m, v in by_model.items()}}

def scan_git(day: date, home: Path | None = None) -> dict:
    home = home or Path.home()
    # git parses a bare date approximately and fills unspecified fields from the
    # current clock, so "--since=2026-09-09" at 16:24 silently means 16:24 that
    # day. Pin both ends of the day explicitly.
    since = f"{day.isoformat()} 00:00:00"
    until = f"{day.isoformat()} 23:59:59"
    out = subprocess.run(["find", str(home), "-maxdepth", "4", "-name", ".git", "-type", "d",
                          "-not", "-path", "*/node_modules/*", "-not", "-path", "*/Library/*"],
                         capture_output=True, text=True, timeout=90)
    commits = 0; add = 0; dele = 0; repos = []
    for g in out.stdout.splitlines():
        repo = str(Path(g).parent)
        try:
            log = subprocess.run(["git","-C",repo,"log","--all","--since",since,
                                  "--until",until,
                                  "--author=azamat","-i","--pretty=tformat:%H","--numstat"],
                                 capture_output=True, text=True, timeout=25)
        except Exception: continue
        c=0; a=0; d_=0
        for ln in log.stdout.splitlines():
            if not ln.strip(): continue
            p = ln.split("\t")
            if len(p)==3:
                if p[0].isdigit(): a+=int(p[0])
                if p[1].isdigit(): d_+=int(p[1])
            elif len(ln)==40: c+=1
        if c or a:
            commits+=c; add+=a; dele+=d_
            repos.append({"repo": Path(repo).name, "commits": c, "added": a, "deleted": d_})
    repos.sort(key=lambda r: -r["added"])
    return {"commits": commits, "added": add, "deleted": dele, "repos": repos}

if __name__ == "__main__":
    day = date.today()
    t = scan_tokens(day); g = scan_git(day)
    print(json.dumps({"date": day.isoformat(), "tokens": t, "git": g}, ensure_ascii=False, indent=1))
