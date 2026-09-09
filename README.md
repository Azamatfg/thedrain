# thedrain

**How much did Claude actually do for you today?**

A local, zero-dependency CLI that reads your Claude Code transcripts and tells you what your day
was worth — tokens, API-equivalent cost, commits, lines written, and how that compares to things
you already have a feel for.

```
────────────────────────────────  D R A I N  ─────────────────────────────────
  what Claude did for you today
  07 September 2026

  tokens drained          877 508 082
  at API rates           $630.91
  model calls            5 598
  commits                30
  lines written          10 819

  ── where the tokens went ────────────────────────────────────────────────
  cache reads    ████████████████████████████████████████· 859.7M  98.0%
  cache writes   █······································    16.6M   1.9%
  model output   ·······································     1.2M   0.1%
  fresh input    ·······································    11.3K   0.0%

  caching saved $3,877.28 — without it the day would have cost $4,508.19

  ── what this means ──────────────────────────────────────────────────────
  If you are on a Claude subscription, you did not pay this.
  This is what the day would cost at API rates.
  Pro       $ 20/mo   today = 31.5 monthly payments
  Max 5×    $100/mo   today = 6.3 monthly payments
  Max 20×   $200/mo   today = 3.2 monthly payments

  ── for scale ────────────────────────────────────────────────────────────
  ▸ reading this aloud without sleeping — 8.3 years
  ▸ 1.03× the first Linux kernel (0.01, 1991 — 10,239 lines)
  ▸ 6.0% of Linux 1.0 (1994)
  ▸ 0.0262% of the modern Linux kernel (40M lines)
  ▸ 27% of the Doom 1993 source
────────────────────────────────────────────────────────────────────────────
```

## Why

Claude Code shows you a session cost. It does not show you a **day**, it does not show you what
your subscription actually delivered, and it never connects tokens to the thing you care about —
what got built.

`drain` answers three questions at once:

1. **What did the model do?** Tokens, calls, thinking, and the cache split most people never look at.
2. **What would that have cost?** Priced per model at current API rates, cache writes and reads
   charged correctly — not one flat rate for everything.
3. **What came out of it?** Commits and lines across every git repository you touched that day.

## Install

Python 3.9+. No dependencies.

```bash
git clone https://github.com/YOURNAME/thedrain.git
cd thedrain
python3 drain.py
```

Optional — run it from anywhere:

```bash
echo 'alias drain="python3 ~/burn/drain.py"' >> ~/.zshrc && source ~/.zshrc
```

## Use

```bash
drain                       # today
drain --date 2026-09-07      # any day
drain --json                 # machine-readable
drain --no-git               # skip repository scanning (faster)
drain --no-anim              # no count-up animation
```

## The cache number is the point

Almost everyone reads "877 million tokens" and assumes a catastrophic bill. 98% of that volume is
**cache reads**, billed at 0.1× the input rate. The single most useful line `drain` prints is how
much prompt caching saved you — on the day above, $3,877.

If your cache-read share is low, that is a finding: something in your prompt prefix is changing
between requests and silently invalidating the cache.

## Pricing

Rates are per 1M tokens, current as of September 2026. Cache writes bill at 1.25× input for the
5-minute TTL and 2× for the 1-hour TTL; cache reads at 0.1× input (0.025× on Fable 5.1).

| Model | Input | Output |
|---|---|---|
| Fable 5.1 / Fable 5 | $10 | $50 |
| Opus 5 / 4.8 / 4.7 / 4.6 | $5 | $25 |
| Sonnet 5 | $2 | $10 |
| Sonnet 4.6 | $3 | $15 |
| Haiku 4.5 | $1 | $5 |

Unknown models fall back to Opus-tier pricing and are shown by name, so you can see what was assumed.

## Privacy

`drain` reads `~/.claude/projects/**/*.jsonl` and your local git history. It makes no network
requests of any kind. Nothing leaves the machine. Read `engine.py` — it is about 120 lines.

## Accuracy, honestly

- **Subscription users pay a flat fee.** The dollar figure is API-equivalent value, not what you
  were charged. The tool says so on every run.
- **Line counts come from git** and are attributed by author, so an agent-written commit that you
  authored counts as yours — which is the point.
- **Deduplicated by message id**, so resumed and branched sessions are not double-counted.
- Reference line counts: Linux 0.01 = 10,239; Linux 1.0 = 176,250; Linux 6.14 rc1 = 40,063,856.

## License

MIT
