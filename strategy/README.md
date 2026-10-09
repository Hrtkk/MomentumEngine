# Strategy register

One file per strategy. Each file is the single place to read **what the rule is, why a stock gets picked, where it enters, where it exits, where the stop sits, what the evidence says, and what has been observed since**. The "Review log" at the bottom of each file is append-only.

| File | Book | Status | One line |
|---|---|---|---|
| [M11.md](M11.md) | M11 | Forward paper test since 2026-10-08 · **RELIABLE (E2)** on holdout (exploratory: audit FAIL, E2.1 re-run pending) | 52-week-high breakout on ≥ 1.5× volume, among the 6-month-momentum top 100 |
| [M10.md](M10.md) | M10 | Forward paper test since 2026-10-08 · holdout: not reliable (drawdown) | Big-gainer event, bought only after 3–7 sessions of confirmation |
| [M2.md](M2.md) | M2 | Forward paper test since 2026-10-08 · holdout: not reliable (drawdown) | Plain 6-month momentum, top 50 in / top 125 out, weekly |
| [C0.md](C0.md) | C0 | Control (legacy v0.2.1 rules) since 2026-09-17 | Top-gainer scan + MQS score; the rules the project started with |

**Status of the evidence (2026-10-08):** the Codex audit of E2 (`reviews/codex/E2_audit_2026-10-08.md`) reproduced the arithmetic but failed the data and benchmark construction (corporate-action accounting, B2-net, security identity, calendar). Until the E2.1 corrected re-run (ROADMAP R0, scheduled 2026-10-10) the development/holdout numbers on these pages are **exploratory screening**, and the forward books are the real test. Live code is v1.1 (`live/ledgers/registration.json` → `patches`).

Sources for every number: `experiments/results_e2/dev_metrics.csv`, `experiments/results_e2/holdout_metrics.csv`, `experiments/results_e2/selection.json`, the live ledgers under `live/ledgers/`, and `ledgers/` for C0. Development period 2013–2020; holdout 2021 → 2026-10-07 (examined once, after selection); forward test from 2026-10-08.

## Reports

`python strategy/build_reports.py` (from the repo root, with `.venv`) writes `strategy/reports/`:

- `overview.html` — all books on one page: cumulative return, drawdown, daily P&L, scoreboard, trade stats.
- `<ID>.html` — one page per strategy: the same charts for that book, its open positions, its closed trades, and the backtest curve (2013 → today) when `strategy/data/backtest_<ID>.csv` exists.
- `<ID>_equity.csv`, `<ID>_trades.csv`, `<ID>_drawdown.csv` — the numbers behind the charts.

`python strategy/backtest.py M11 M2 M10` regenerates the backtest curves from the point-in-time data with the **current** engine (v1.1), so they can differ slightly from the E2 tables, which were produced before the v1.1 patches (needs `experiments/data/pit/` from 2011; ~10 min).

Reports read ledgers only. They never change a book.

## How to read a strategy file

- **Rule** — the exact frozen rule, in words, with the code reference.
- **Why a stock is picked** — the objective facts the rule looks at, nothing else. The morning report prints these per order ("Why" column).
- **Entry / Exit / Stop** — all pre-registered. Entry is always the next session's open. Nothing is discretionary.
- **Evidence** — the development and holdout numbers, with the number of trials (14) disclosed. B2-net (equal-weight Liquid-500, 0.6% costs) is the hurdle.
- **What it does not do** — the known blind spots.
- **Review log** — append-only observations. Trades → observations → evidence → hypotheses. A hypothesis becomes a shadow version before it can change a rule (ROADMAP §1).

## Rules of the register

1. Report, don't advise. These pages describe what a paper book did and why; they never say buy, sell or hold.
2. Every number carries its source and date. Unverifiable → `—`.
3. Changing a rule = a new version through the promotion gate, logged in `strategy_ledger.md`. The strategy file then gets a new "Version" row, never an edited old one.
