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
    seen = {}
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
            # A streamed reply is written as one line per content block, all sharing
            # message.id. Early lines carry the preliminary usage from message_start;
            # only the last one has the final output_tokens. Keeping the first line
            # would undercount output by more than half on long replies.
            key = msg.get("id") or d.get("uuid")
            if key is None:
                key = (f, len(seen))
            prev = seen.get(key)
            if prev is None or row["output"] > prev[1]["output"]:
                seen[key] = (model, row)

    for model, row in seen.values():
        inp, out, rmul = price_for(model)
        row["cost"] = (row["input"]*inp + row["cache_w5"]*inp*1.25 + row["cache_w1"]*inp*2
                       + row["cache_r"]*inp*rmul + row["output"]*out) / 1e6
        for k, v in row.items():
            tot[k] += v; by_model[model][k] += v
    tot["total_tokens"] = sum(tot[k] for k in ("input","cache_w5","cache_w1","cache_r","output"))
    return {"totals": dict(tot), "by_model": {m: dict(v) for m, v in by_model.items()}}

def repo_roots(home: Path | None = None) -> list[str]:
    """Repositories you actually worked in, taken from the cwd of every transcript.

    Walking the filesystem was the obvious way and the wrong one: macOS refuses to
    let `find` descend into Desktop, Documents and Downloads without Full Disk
    Access, and the refusal arrives on stderr, so a repository kept there simply
    reported zero commits. The transcripts already name the directory of every
    session, which is both cheaper to read and a better answer to the question.
    """
    home = home or Path.home()
    roots = set()
    for f in (home / ".claude" / "projects").rglob("*.jsonl"):
        try:
            with f.open(encoding="utf8", errors="ignore") as fh:
                for line in fh:
                    if '"cwd"' not in line: continue
                    try: cwd = json.loads(line).get("cwd")
                    except Exception: break
                    if not cwd: break
                    # sessions run inside .claude/worktrees/<name> belong to the repo above
                    p = Path(cwd)
                    parts = p.parts
                    if ".claude" in parts:
                        i = parts.index(".claude")
                        if len(parts) > i + 1 and parts[i+1] == "worktrees":
                            p = Path(*parts[:i])
                    while p != p.parent:
                        if (p / ".git").exists():
                            roots.add(str(p)); break
                        p = p.parent
                    break
        except OSError:
            continue
    # A session's cwd is not the only place work lands: a repository edited over a
    # shell from somewhere else never appears as a cwd. So sweep as well, and take
    # the union — the sweep finds shallow repositories, the transcripts find the
    # ones the sweep is not allowed to enter.
    try:
        out = subprocess.run(["find", str(home), "-maxdepth", "4", "-name", ".git",
                              "-not", "-path", "*/node_modules/*", "-not", "-path", "*/Library/*"],
                             capture_output=True, text=True, timeout=90)
        roots |= {str(Path(g).parent) for g in out.stdout.splitlines()}
    except Exception:
        pass
    return sorted(roots)


def _author(repo: str) -> str:
    """Whose commits to count. Hardcoding a name made the tool useless to everyone else."""
    r = subprocess.run(["git", "-C", repo, "config", "user.email"],
                       capture_output=True, text=True, timeout=10)
    return r.stdout.strip()


def scan_git(day: date, home: Path | None = None) -> dict:
    home = home or Path.home()
    # git parses a bare date approximately and fills unspecified fields from the
    # current clock, so "--since=2026-09-09" at 16:24 silently means 16:24 that
    # day. Pin both ends of the day explicitly.
    since = f"{day.isoformat()} 00:00:00"
    until = f"{day.isoformat()} 23:59:59"
    commits = 0; add = 0; dele = 0; repos = []
    seen = set()                        # one clone of a repo is enough
    for repo in repo_roots(home):
        who = _author(repo)
        if not who: continue
        try:
            log = subprocess.run(["git","-C",repo,"log","--branches","--remotes","--no-merges",
                                  "--since",since,"--until",until,
                                  "--author",who,"-i","--pretty=tformat:%H","--numstat"],
                                 capture_output=True, text=True, timeout=25)
        except Exception: continue
        c=0; a=0; d_=0; skip=False
        for ln in log.stdout.splitlines():
            if not ln.strip(): continue
            p = ln.split("\t")
            if len(p)==3:
                if skip: continue
                if p[0].isdigit(): a+=int(p[0])
                if p[1].isdigit(): d_+=int(p[1])
            elif len(ln)==40:
                skip = ln in seen
                if skip: continue
                seen.add(ln); c+=1
        if c or a:
            commits+=c; add+=a; dele+=d_
            repos.append({"repo": Path(repo).name, "commits": c, "added": a, "deleted": d_})
    repos.sort(key=lambda r: -r["added"])
    return {"commits": commits, "added": add, "deleted": dele, "repos": repos}

if __name__ == "__main__":
    day = date.today()
    t = scan_tokens(day); g = scan_git(day)
    print(json.dumps({"date": day.isoformat(), "tokens": t, "git": g}, ensure_ascii=False, indent=1))
